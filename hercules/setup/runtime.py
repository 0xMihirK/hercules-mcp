"""Local-only verification. Host checks never invoke an execution tool."""

from __future__ import annotations

import asyncio
import json
import os
import socket
from contextlib import closing
from pathlib import Path

from hercules.setup.transaction import SetupError


def cleanup_verification(directory: Path, metadata: dict):
    """Reclaim only a journaled, uniquely allocated verification workspace."""
    import shutil

    workspace = Path(metadata["workspace"]).absolute()
    if (
        workspace != directory.absolute() / "verification"
        or workspace.resolve() != workspace
    ):
        raise SetupError(
            "unsafe_cleanup", "Verification workspace is outside its transaction"
        )
    if metadata.get("cleaned"):
        return
    if not workspace.exists():
        metadata["cleaned"] = True
        return
    if metadata.get("runtime"):
        import docker
        from hercules.core.docker_manager import (
            _project_hash,
            _is_process_running,
            _process_start_token,
        )

        expected = {
            "hercules.managed": "true",
            "hercules.project_root_hash": _project_hash(Path(metadata["checkout"])),
            "hercules.workspace_root_hash": _project_hash(workspace),
        }
        try:
            with closing(docker.from_env(timeout=10)) as client:
                containers = client.containers.list(
                    all=True,
                    filters={"label": [f"{k}={v}" for k, v in expected.items()]},
                )
                for container in containers:
                    container.reload()
                    labels = container.attrs.get("Config", {}).get("Labels") or {}
                    if any(labels.get(k) != v for k, v in expected.items()):
                        raise SetupError(
                            "cleanup_ownership_changed",
                            "Verification container labels changed",
                        )
                    pid = int(labels.get("hercules.owner_pid", "0"))
                    token = labels.get("hercules.owner_start_token", "")
                    if not pid or not token:
                        raise SetupError(
                            "cleanup_ownership_unknown",
                            "Verification container has incomplete ownership labels",
                        )
                    if _is_process_running(pid) and _process_start_token(pid) in (
                        "",
                        token,
                    ):
                        raise SetupError(
                            "verification_still_running",
                            f"The disposable verification server is still running (PID {pid})",
                            "Wait for that exact server to exit, then resume; do not stop other MCP clients.",
                        )
                    identity = {
                        k: v for k, v in labels.items() if k.startswith("hercules.")
                    }
                    exact = client.containers.get(container.id)
                    exact.reload()
                    if any(
                        (exact.attrs.get("Config", {}).get("Labels") or {}).get(k) != v
                        for k, v in identity.items()
                    ):
                        raise SetupError(
                            "cleanup_ownership_changed",
                            "Container ownership changed before removal",
                        )
                    exact.remove(force=True)
        except docker.errors.DockerException as exc:
            raise SetupError(
                "cleanup_docker_unavailable",
                "Docker is unavailable; verification cleanup is not confirmed",
                "Restore Docker access and resume cleanup.",
            ) from exc
        # Runtime evidence is useful on failure and never silently discarded.
        metadata["retained_evidence"] = str(workspace)
    else:
        # Host-only verification writes only its transaction-owned session logs.
        shutil.rmtree(workspace)
    metadata["cleaned"] = True


def image_status(facts: dict) -> str:
    import docker

    try:
        with closing(docker.from_env(timeout=10)) as client:
            image = client.images.get(facts["image"]["tag"])
            labels = image.attrs.get("Config", {}).get("Labels") or {}
            expected = facts["image"]
            actual_platform = (
                f"{image.attrs.get('Os')}/{image.attrs.get('Architecture')}"
            )
            if actual_platform != expected["target_platform"]:
                return "mismatch"
            return (
                "ready"
                if all(
                    labels.get(key) == value
                    for key, value in expected["labels"].items()
                )
                else "mismatch"
            )
    except docker.errors.ImageNotFound:
        return "missing"
    except docker.errors.DockerException:
        return "docker_unavailable"


def assets_ready(root: Path, capabilities: list[str]) -> bool:
    from hercules.core.tool_catalog import required_wordlists
    from hercules.core.wordlists import (
        WORDLIST_FILES,
        validate_wordlist_archive,
        _seclists_ready,
        _rockyou_ready,
    )

    for name in required_wordlists(capabilities):
        archive = root / WORDLIST_FILES[name]
        if not validate_wordlist_archive(archive.name, archive):
            return False
        if name == "seclists" and not _seclists_ready(
            root / "SecLists", root / "SecLists/.hercules-ready", archive
        ):
            return False
        if name == "rockyou" and not _rockyou_ready(
            root / "rockyou.txt", root / ".rockyou.hercules-ready.json", archive
        ):
            return False
    return True


async def verify(
    launcher: Path,
    environment: dict[str, str],
    facts: dict,
    workspace: Path,
    *,
    runtime: bool = False,
) -> dict:
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    env = {
        **os.environ,
        **environment,
        "HERCULES_WORKSPACE_ROOT": str(workspace),
        "PRESERVE_CONTAINER": "false",
        "HERCULES_WORKSPACE_AUTO_PRUNE": "false",
    }
    if runtime:
        env.update(
            ALLOWED_TARGETS="127.0.0.1",
            BLOCKED_TARGETS="",
            HERCULES_DOCKER_NETWORK="",
            USE_PRIVILEGED="false",
            BROWSER_PROXY_URL="",
            BROWSER_PROXY="",
        )

    def transport():
        return StdioTransport(str(launcher), [], env=env, cwd=str(launcher.parent))

    checks = []
    network = None
    started = False
    try:
        async with Client(transport(), timeout=180) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            if sorted(t.name for t in tools) != sorted(
                facts["mcp_surface"]["tool_names"]
            ):
                raise SetupError(
                    "surface_mismatch", "Cold MCP tools differ from setup facts"
                )
            if sorted(str(r.uri) for r in resources) != sorted(
                facts["mcp_surface"]["resource_uris"]
            ):
                raise SetupError(
                    "surface_mismatch", "Cold MCP resources differ from setup facts"
                )
            # Remote catalog resources are deliberately not fetched during setup.
            for resource in resources:
                if str(resource.uri).startswith("resource://agent_skills/"):
                    await client.read_resource(resource.uri)
            checks.append("cold_stdio_surface")
            if not runtime:
                return {"host": "passed", "runtime": "not_run", "checks": checks}
            try:
                cold = (
                    await client.call_tool(
                        "shell_exec", {"command": "true"}, raise_on_error=False
                    )
                ).structured_content
                if cold.get("error_type") != "runtime_not_started":
                    raise SetupError(
                        "cold_start_failed",
                        "Pre-start tool did not report runtime_not_started",
                    )
                first = (
                    await client.call_tool("system_start_container")
                ).structured_content
                if first.get("status") != "success":
                    raise SetupError(
                        "runtime_start_failed",
                        "Explicit start failed; inspect the disposable verification evidence",
                    )
                started = True
                second = (
                    await client.call_tool("system_start_container")
                ).structured_content
                if (
                    second.get("session_id") != first["session_id"]
                    or second.get("start_mode") != "already_running"
                ):
                    raise SetupError(
                        "idempotency_failed",
                        "Repeated start did not reuse the container",
                    )
                command = (
                    await client.call_tool(
                        "shell_exec", {"command": "printf hercules-local-ok"}
                    )
                ).structured_content
                if (
                    command.get("exit_code") != 0
                    or command.get("stdout") != "hercules-local-ok"
                ):
                    raise SetupError("command_failed", "Harmless local command failed")
                checks.extend(
                    [
                        "pre_start_guard",
                        "explicit_start",
                        "idempotent_start",
                        "local_command",
                    ]
                )
                if "browser" in facts["selection"]["capabilities"]:
                    job = (
                        await client.call_tool(
                            "shell_exec_background",
                            {
                                "command": "python3 -m http.server 18080 --bind 127.0.0.1 --directory /tmp",
                                "job_id": "setup-browser-fixture",
                            },
                        )
                    ).structured_content
                    if job.get("status") == "error":
                        raise SetupError(
                            "browser_fixture_failed", "Local browser fixture failed"
                        )
                    for _ in range(20):
                        ready = (
                            await client.call_tool(
                                "shell_exec",
                                {
                                    "command": (
                                        "python3 -c 'import urllib.request; "
                                        "client = urllib.request.build_opener(urllib.request.ProxyHandler({})); "
                                        "client.open(\"http://127.0.0.1:18080/\", timeout=2).close()'"
                                    )
                                },
                            )
                        ).structured_content
                        if ready.get("exit_code") == 0:
                            break
                        await asyncio.sleep(0.25)
                    else:
                        raise SetupError(
                            "browser_fixture_failed",
                            "Local browser fixture did not become ready",
                        )
                    opened = (
                        await client.call_tool(
                            "browser_open",
                            {
                                "url": "http://127.0.0.1:18080",
                                "session": "setup-verification",
                            },
                        )
                    ).structured_content
                    if opened.get("exit_code") != 0:
                        raise SetupError(
                            "browser_check_failed", "Local-only browser check failed"
                        )
                    checks.append("local_browser")
                network = (
                    await client.call_tool("system_network_info")
                ).structured_content
                async with Client(transport(), timeout=60) as other:
                    await other.list_tools()
                    cold = (
                        await other.call_tool(
                            "shell_exec", {"command": "true"}, raise_on_error=False
                        )
                    ).structured_content
                    if cold.get("error_type") != "runtime_not_started":
                        raise SetupError(
                            "cold_isolation_failed", "Second client started a runtime"
                        )
                command = (
                    await client.call_tool("shell_exec", {"command": "true"})
                ).structured_content
                if command.get("exit_code") != 0:
                    raise SetupError(
                        "cold_isolation_failed",
                        "Second client disturbed the running runtime",
                    )
                checks.append("second_cold_connection")
            finally:
                if started:
                    stopped = (
                        await client.call_tool("system_stop_container")
                    ).structured_content
                    if stopped.get("status") != "success":
                        raise SetupError(
                            "cleanup_failed", "Verification container did not stop"
                        )
        if network:
            effective = network["port_allocation"]["effective"]
            for port in [
                effective["metasploit_rpc"],
                effective["browser_stream"],
                *effective["listeners"],
            ]:
                if not port:
                    continue
                with socket.socket() as probe:
                    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                        probe.setsockopt(
                            socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1
                        )
                    probe.bind(("127.0.0.1", int(port)))
            checks.append("stop_and_ports_released")
        return {"host": "passed", "runtime": "passed", "checks": checks}
    finally:
        # Graceful STDIO shutdown is allowed to settle before the owner check.
        from hercules.core.workspace import WorkspaceManager

        manager = WorkspaceManager(workspace)
        manager.cleanup_empty_owned(active_session="")


def main():
    """Worker mode uses the candidate release's dependencies and implementation."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("assets", "assets-ready", "verify"))
    parser.add_argument("--facts", required=True, type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--runtime", action="store_true")
    args = parser.parse_args()
    facts = json.loads(args.facts.read_text(encoding="utf-8"))
    if args.action == "assets":
        from hercules.core.wordlists import provision_wordlists

        result = provision_wordlists(
            Path(os.environ["HERCULES_WORDLIST_ROOT"]),
            facts["selection"]["capabilities"],
        )
    elif args.action == "assets-ready":
        result = {"ready": assets_ready(Path(os.environ["HERCULES_WORDLIST_ROOT"]), facts["selection"]["capabilities"])}
    else:
        root = Path(facts["source"]["checkout"])
        launcher = (
            root
            / ".venv"
            / ("Scripts/hercules.exe" if os.name == "nt" else "bin/hercules")
        )
        result = asyncio.run(
            verify(launcher, {}, facts, args.workspace, runtime=args.runtime)
        )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
