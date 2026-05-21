import asyncio
import docker

async def test_remaining():
    client = docker.from_env()
    
    print("[*] Starting temporary container for fast testing...")
    test_container = client.containers.run(
        "kalilinux/kali-rolling",
        command="sleep infinity",
        detach=True,
        remove=True
    )
    
    print("[*] Installing exploitdb and python3...")
    test_container.exec_run("apt-get update -qq")
    test_container.exec_run("apt-get install -y -qq exploitdb python3 python3-pip")
    
    # 1. Searchsploit
    print("\n--- Testing searchsploit ---")
    res = test_container.exec_run("searchsploit UnrealIRCd 3.2.8.1")
    out = res.output.decode('utf-8', errors='replace')
    print(out[:500] + "...\n")
    if "unrealircd" in out.lower() or "backdoor" in out.lower():
        print("[+] searchsploit (search) passed!")
        
    res = test_container.exec_run("searchsploit -m linux/remote/13853.pl -d /tmp 2>/dev/null; cat /tmp/13853.pl 2>/dev/null || echo 'mirror failed'")
    out = res.output.decode('utf-8', errors='replace')
    if "perl" in out.lower() or "socket" in out.lower() or "unrealircd" in out.lower():
        print("[+] searchsploit (get) passed!")
        
    # 2. System & Workspace
    print("\n--- Testing System & Workspace ---")
    res = test_container.exec_run("cat /etc/os-release")
    out = res.output.decode('utf-8', errors='replace')
    if "kali" in out.lower():
        print("[+] shell_exec passed!")
        
    test_container.exec_run("mkdir -p /opt/workspace/py /opt/workspace/sh")
    test_container.exec_run(["bash", "-c", "echo 'import sys; print(\"Hercules Working\")' > /opt/workspace/py/test.py"])
    res = test_container.exec_run("python3 /opt/workspace/py/test.py")
    out = res.output.decode('utf-8', errors='replace')
    if "Hercules Working" in out:
        print("[+] workspace_scripts (python write/run) passed!")
        
    test_container.exec_run(["bash", "-c", "echo '#!/bin/bash\\necho $USER' > /opt/workspace/sh/test.sh && chmod +x /opt/workspace/sh/test.sh"])
    res = test_container.exec_run("bash /opt/workspace/sh/test.sh")
    out = res.output.decode('utf-8', errors='replace').strip()
    if "root" in out:
        print("[+] workspace_scripts (shell write/run) passed!")
        
    print("[*] Tearing down temporary container...")
    test_container.stop()
    
    # 3. Post-Exploitation Resources
    print("\n--- Testing Resources ---")
    with open('hercules/resources/post_exploitation.py', 'r') as f:
        content = f.read()
        if "gtfobins" in content.lower():
            print("[+] Post-Exploitation Resource check passed!")

if __name__ == "__main__":
    asyncio.run(test_remaining())
