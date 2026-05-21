import asyncio
import docker

async def test_web_tools():
    target_ip = "172.17.0.2"
    print(f"[*] Target IP: {target_ip}")
    print("[*] Initializing Docker Manager...")
    client = docker.from_env()
    
    print("[*] Starting temporary container for web testing...")
    test_container = client.containers.run(
        "kalilinux/kali-rolling",
        command="sleep infinity",
        detach=True,
        remove=True
    )
    print(f"[+] Started temporary container: {test_container.id}")
    
    print("[*] Installing testing tools (whatweb, wafw00f, nikto, arjun, gobuster, python3-pip)...")
    test_container.exec_run("apt-get update -qq")
    test_container.exec_run("apt-get install -y -qq whatweb wafw00f nikto gobuster python3 python3-pip wget")
    test_container.exec_run("python3 -m pip install arjun --break-system-packages -q")
    
    # 1. web_whatweb
    print("\n--- Testing web_whatweb ---")
    result = test_container.exec_run(f"whatweb http://{target_ip}")
    print(result.output.decode('utf-8', errors='replace'))
    
    # 2. web_wafw00f
    print("\n--- Testing web_wafw00f ---")
    result = test_container.exec_run(f"wafw00f http://{target_ip}")
    print(result.output.decode('utf-8', errors='replace')[:500] + "\n[Output truncated]")
    
    # 3. fuzz_dirs (gobuster)
    print("\n--- Testing fuzz_dirs (gobuster) ---")
    # Quick wordlist
    test_container.exec_run("wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt -O /tmp/common.txt")
    result = test_container.exec_run(f"gobuster dir -u http://{target_ip}/ -w /tmp/common.txt -t 10 -q")
    print(result.output.decode('utf-8', errors='replace')[:500] + "\n[Output truncated]")
    
    print("[*] Tearing down temporary container...")
    test_container.stop()

if __name__ == "__main__":
    asyncio.run(test_web_tools())
