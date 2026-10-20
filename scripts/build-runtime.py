"""Local full-image build with an isolated builder, disk guard and owned cleanup."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hercules.core.setup_info import setup_information


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", default="linux/amd64", choices=("linux/amd64", "linux/arm64"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    facts = setup_information(root, capabilities="all", target_platform=args.platform)
    builder = "hercules-build-" + uuid.uuid4().hex[:12]
    report = {"builder": builder, "image": facts["image"]["tag"], "platform": args.platform,
              "status": "building", "cleanup": "pending", "started": time.time(), "minimum_free_bytes": shutil.disk_usage(output).free}
    flags = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}

    def run(argv, **kwargs):
        return subprocess.run(argv, check=True, stdin=subprocess.DEVNULL, **flags, **kwargs)

    def save():
        (output / "build.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    process = None
    created = False
    try:
        if shutil.disk_usage(output).free < 8 * 1024**3:
            raise RuntimeError("Less than 8 GiB free; build not started")
        (output / "facts.json").write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
        run(["docker", "buildx", "create", "--name", builder, "--driver", "docker-container"], stdout=subprocess.DEVNULL)
        created = True
        save()
        command = ["docker", "buildx", "build", "--builder", builder, "--platform", args.platform, "--load", "--progress", "plain", "-t", facts["image"]["tag"]]
        for key, value in facts["image"]["build_arguments"].items():
            command.extend(["--build-arg", f"{key}={value}"])
        for key, value in facts["image"]["labels"].items():
            command.extend(["--label", f"{key}={value}"])
        if facts["image"]["custom_ca"]["configured"]:
            raise RuntimeError("Use hercules-setup runtime prepare --image-source build with the explicit CA secret")
        with (output / "build.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([*command, str(root)], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, shell=False, **flags)
            from hercules.core.docker_manager import _process_start_token
            report["build_process"] = {"pid": process.pid, "start_token": _process_start_token(process.pid)}
            while process.poll() is None:
                free = shutil.disk_usage(output).free
                report["minimum_free_bytes"] = min(report["minimum_free_bytes"], free)
                save()
                if free < 8 * 1024**3:
                    raise RuntimeError("8 GiB disk reserve reached; cancelling only this build")
                if time.time() - report["started"] > 7200:
                    raise RuntimeError("Two-hour build deadline reached; candidate retained for diagnosis")
                time.sleep(2)
        if process.returncode:
            raise RuntimeError(f"Build failed ({process.returncode}); inspect build.log")
        result = run(["docker", "image", "inspect", facts["image"]["tag"]], capture_output=True, text=True)
        report["image_inspect"] = json.loads(result.stdout)
        from hercules.core.build_info import image_identity, record_local_image

        if image_identity(root)[1] != facts["image"]["fingerprint"]:
            raise RuntimeError("Build inputs changed while building; retained candidate is not the current runtime")
        record_local_image(facts["image"]["fingerprint"], report["image_inspect"][0]["Id"])
        report["status"] = "built_pending_verification"
    except BaseException as exc:
        report.update(status="failed", error=str(exc))
        raise
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        if created:
            cleanup = subprocess.run(["docker", "buildx", "rm", "--force", builder], check=False, stdin=subprocess.DEVNULL, capture_output=True, text=True, **flags)
            report["cleanup"] = "complete" if cleanup.returncode == 0 else "failed"
            if cleanup.returncode:
                report["cleanup_error"] = cleanup.stderr
        else:
            report["cleanup"] = "not_created"
        report["duration_seconds"] = time.time() - report["started"]
        save()
        if report["cleanup"] == "failed" and report["status"] != "failed":
            raise RuntimeError("Image built but builder cleanup was not confirmed; inspect build.json before using it")


if __name__ == "__main__":
    main()
