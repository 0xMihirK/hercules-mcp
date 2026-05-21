import asyncio
import docker

async def test_scanme_tools():
    print("[*] Initializing Docker Manager...")
    client = docker.from_env()
    
    print("[*] Starting temporary container for quick testing...")
    test_container = client.containers.run(
        "kalilinux/kali-rolling",
        command="sleep infinity",
        detach=True,
        remove=True
    )
    print(f"[+] Started temporary container: {test_container.id}")
    
    print("[*] Installing testing tools...")
    test_container.exec_run("apt-get update -qq")
    test_container.exec_run("apt-get install -y -qq curl hping3 dnsutils whois")
    
    # 1. network_curl
    print("\n--- Testing network_curl ---")
    result = test_container.exec_run("curl -I http://scanme.nmap.org")
    print(result.output.decode('utf-8', errors='replace'))
    
    # 2. network_hping3
    print("\n--- Testing network_hping3 ---")
    result = test_container.exec_run("hping3 -c 5 -S -p 80 scanme.nmap.org")
    print(result.output.decode('utf-8', errors='replace'))
    
    # 3. recon_whois
    print("\n--- Testing recon_whois ---")
    result = test_container.exec_run("whois scanme.nmap.org")
    print(result.output.decode('utf-8', errors='replace')[:500] + "...\n[Output truncated]")
    
    # 4. recon_dig
    print("\n--- Testing recon_dig ---")
    result = test_container.exec_run("dig ANY scanme.nmap.org")
    print(result.output.decode('utf-8', errors='replace'))
    
    print("[*] Tearing down temporary container...")
    test_container.stop()

if __name__ == "__main__":
    asyncio.run(test_scanme_tools())
