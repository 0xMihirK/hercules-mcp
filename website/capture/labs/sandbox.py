"""Isolate the real host-side Hercules process without modifying its APIs.

Only source and runtime build inputs are copied. No .env, agent configuration,
Docker credentials or personal workspace enters the capture containers.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
CAPABILITIES = "shell,session,workspace,dns,nmap,curl,ncat,whatweb,fuzz,nuclei,searchsploit,binwalk,steghide,browser"


def fresh_source(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    for directory in ("hercules", "docker"):
        shutil.copytree(ROOT / directory, destination / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                        dirs_exist_ok=True)
    for name in ("Dockerfile", ".dockerignore", "pyproject.toml", "install.md"):
        if (ROOT / name).is_file():
            shutil.copyfile(ROOT / name, destination / name)
    assert not (destination / ".env").exists()
    return destination


def host_environment(source: Path, workspace: Path, network: str) -> dict[str, str]:
    inherited = {key: os.environ[key] for key in
                 ("PATH", "SystemRoot", "WINDIR", "TEMP", "TMP", "LOCALAPPDATA", "APPDATA", "USERPROFILE", "PROCESSOR_ARCHITECTURE", "PROCESSOR_ARCHITEW6432", "COMSPEC")
                 if key in os.environ}
    return {**inherited, "PYTHONUTF8": "1", "HERCULES_INSTALLED_CAPABILITIES": CAPABILITIES,
            "HERCULES_DISABLED_TOOLS": "", "HERCULES_IMAGE_PLATFORM": "linux/amd64", "SKIP_METASPLOIT": "true",
            "MSF_PASSWORD": "capture-local-unused", "USE_PRIVILEGED": "false",
            "HERCULES_WORKSPACE_ROOT": str(workspace.resolve()),
            "HERCULES_WORDLIST_ROOT": str((ROOT / "wordlists").resolve()),
            "HERCULES_DOCKER_NETWORK": network,
            "HERCULES_LISTENER_BIND_HOST": "127.0.0.1",
            "HERCULES_LISTENER_PORTS": "24444-24447", "MSF_RPC_PORT": "25553",
            "BROWSER_STREAM_PORT": "0", "HERCULES_AUTO_ALLOCATE_PORTS": "true",
            "HERCULES_WORKSPACE_AUTO_PRUNE": "false", "PRESERVE_CONTAINER": "false",
            "ALLOWED_TARGETS": "172.30.0.0/16,lab,*.lab.test",
            "HERCULES_MAX_INLINE_RESPONSE_CHARS": "6000", "WATCHDOG_INTERVAL": "0"}


def server_command(source: Path) -> list[str]:
    return [sys.executable, "-I", "-c",
            "import sys; sys.path.insert(0, " + repr(str(source.resolve())) +
            "); from hercules.main import main; main()"]


def build_runtime(source: Path, environment: dict[str, str]) -> None:
    code = """import json
from pathlib import Path
from hercules.core.config import HerculesConfig
from hercules.core.build_info import image_identity, capability_manifest_sha256
from hercules.core.tool_catalog import format_capabilities
c=HerculesConfig.from_env()
tag,fingerprint=image_identity(c.project_root,c.installed_capabilities,target_platform=c.image_platform)
print(json.dumps({'tag':tag,'fingerprint':fingerprint,'capabilities':format_capabilities(c.installed_capabilities),'manifest':capability_manifest_sha256(c.installed_capabilities),'platform':c.image_platform}))
"""
    command = [sys.executable, "-I", "-c", "import sys; sys.path.insert(0, " + repr(str(source.resolve())) + ");\n" + code]
    metadata = json.loads(subprocess.check_output(command, env=environment, text=True))
    args = ["docker", "build", "--platform", metadata["platform"], "-t", metadata["tag"],
            "--build-arg", "HERCULES_CAPABILITIES=" + metadata["capabilities"],
            "--build-arg", "HERCULES_BUILD_FINGERPRINT=" + metadata["fingerprint"],
            "--build-arg", "HERCULES_CAPABILITY_MANIFEST_SHA256=" + metadata["manifest"],
            "--build-arg", "HERCULES_TARGET_PLATFORM=" + metadata["platform"], str(source)]
    # BuildKit's plugin lives in the system installation. A fresh Docker CLI
    # config supplies that path without copying registry credentials/contexts.
    docker_config = source / "capture-docker-config"
    docker_config.mkdir(exist_ok=True)
    plugins = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Docker/cli-plugins"
    (docker_config / "config.json").write_text(json.dumps({"cliPluginsExtraDirs": [str(plugins)]}), encoding="utf-8")
    build_environment = {**environment, "DOCKER_CONFIG": str(docker_config), "DOCKER_BUILDKIT": "1"}
    if os.name == "nt":
        build_environment["DOCKER_HOST"] = "npipe:////./pipe/dockerDesktopLinuxEngine"
    subprocess.run(args, env=build_environment, check=True)
    (source / "capture-runtime.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    source = fresh_source(ROOT / "website/test-results/labs/source")
    environment = host_environment(source, ROOT / "website/test-results/labs/workspace", "hercules-capture-lab")
    if args.build:
        build_runtime(source, environment)
