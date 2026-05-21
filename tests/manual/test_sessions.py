"""Test session isolation: start, create file, restart, verify isolation, list sessions."""
import asyncio
import os
import subprocess
from pathlib import Path

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from hercules.core.config import HerculesConfig
from hercules.core.docker_manager import DockerManager


class MockContext:
    def __init__(self, docker, config):
        self.lifespan_context = {"docker": docker, "config": config, "msf_client": None}


async def test_session_isolation():
    config = HerculesConfig(project_root=Path.cwd(), skip_metasploit=True)
    docker = DockerManager(config)

    # ── Test 1: Start container, verify session workspace ──
    print("=== Test 1: Start container ===")
    await docker.start_container()
    session1 = docker.session_id
    ws1 = Path.cwd() / "workspace" / session1
    assert ws1.exists(), f"Workspace {ws1} should exist"
    print(f"  PASS: Session '{session1}' started, workspace exists at {ws1}")

    # ── Test 2: Create a file inside container, verify on host ──
    print("\n=== Test 2: File isolation ===")
    result = await docker.exec_command("echo 'target_A_data' > /opt/workspace/scan_results.txt")
    host_file = ws1 / "scan_results.txt"
    assert host_file.exists(), "File should appear on host in session folder"
    assert "target_A_data" in host_file.read_text()
    print(f"  PASS: File created in container appears at {host_file}")

    # ── Test 3: Atomic restart ──
    print("\n=== Test 3: Atomic restart ===")
    new_session = await docker.restart_container()
    session2 = docker.session_id
    ws2 = Path.cwd() / "workspace" / session2
    assert session2 == new_session
    assert session1 != session2, "New session should have different ID"
    assert ws2.exists(), f"New workspace {ws2} should exist"
    assert ws1.exists(), f"Old workspace {ws1} should still exist"
    print(f"  PASS: Restarted from '{session1}' to '{session2}'")

    # ── Test 4: Old files NOT visible in new container ──
    print("\n=== Test 4: Workspace isolation ===")
    result = await docker.exec_command("cat /opt/workspace/scan_results.txt 2>&1")
    assert result.exit_code != 0 or "No such file" in result.stdout or "No such file" in result.stderr, \
        "Old session file should NOT be visible in new container"
    print(f"  PASS: Old file not visible in new session (exit_code={result.exit_code})")

    # ── Test 5: New file in new session stays isolated ──
    print("\n=== Test 5: New session file ===")
    await docker.exec_command("echo 'target_B_data' > /opt/workspace/new_scan.txt")
    new_host_file = ws2 / "new_scan.txt"
    old_check = ws1 / "new_scan.txt"
    assert new_host_file.exists(), "New file should appear in new session workspace"
    assert not old_check.exists(), "New file should NOT appear in old session workspace"
    print(f"  PASS: New file isolated to session '{session2}'")

    # ── Test 6: list_sessions ──
    print("\n=== Test 6: List sessions ===")
    sessions = docker.list_sessions()
    ids = [s["session_id"] for s in sessions]
    assert session1 in ids, f"Session '{session1}' should be in list"
    assert session2 in ids, f"Session '{session2}' should be in list"
    active = [s for s in sessions if s["is_active"]]
    assert len(active) == 1 and active[0]["session_id"] == session2
    print(f"  PASS: {len(sessions)} sessions listed, active={session2}")
    for s in sessions:
        print(f"    {s['session_id']} | active={s['is_active']} | files={s['file_count']} | size={s['total_size_mb']}MB")

    # ── Test 7: session_id reads live (not stale) ──
    print("\n=== Test 7: Live session_id ===")
    ctx = MockContext(docker, config)
    live_id = ctx.lifespan_context["docker"].session_id
    assert live_id == session2, "Live read should match current session"
    print(f"  PASS: Live read returns '{live_id}' (current session)")

    # ── Test 8: Stop container ──
    print("\n=== Test 8: Stop container ===")
    await docker.stop_container()
    ps = subprocess.run(["docker", "ps", "-q", "-f", f"name=hercules-{session2}"],
                        capture_output=True, text=True)
    assert not ps.stdout.strip(), "Container should be removed"
    assert ws2.exists(), "Workspace should survive container removal"
    print("  PASS: Container removed, workspace preserved")

    # ── Cleanup ──
    import shutil
    shutil.rmtree(ws1, ignore_errors=True)
    shutil.rmtree(ws2, ignore_errors=True)

    print("\n" + "=" * 50)
    print("ALL 8 TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(test_session_isolation())
