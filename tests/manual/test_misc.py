import asyncio
import docker

async def test_misc():
    client = docker.from_env()
    print("[*] Starting fast container...")
    kali = client.containers.run(
        "kalilinux/kali-rolling",
        command="sleep infinity",
        detach=True,
        remove=True,
        network_mode="host",
        privileged=True
    )
    
    print("[*] Installing tools...")
    kali.exec_run("apt-get update -qq")
    # Note: Amass, dnsx, httpx are installed via github releases in our docker_manager, but we can test nmap and ncat and wpscan here easily
    kali.exec_run("apt-get install -y -qq nmap wpscan ncat curl unzip")
    
    # Let's install dnsx and httpx really quickly
    kali.exec_run(["bash", "-c", "curl -sSL https://github.com/projectdiscovery/dnsx/releases/download/v1.2.1/dnsx_1.2.1_linux_amd64.zip -o dnsx.zip && unzip -o dnsx.zip -d /usr/local/bin/ && chmod +x /usr/local/bin/dnsx"])
    kali.exec_run(["bash", "-c", "curl -sSL https://github.com/projectdiscovery/httpx/releases/download/v1.6.8/httpx_1.6.8_linux_amd64.zip -o httpx.zip && unzip -o httpx.zip -d /usr/local/bin/ && chmod +x /usr/local/bin/httpx"])
    
    print("\n--- Testing recon_dnsx ---")
    res = kali.exec_run(["bash", "-c", "echo 'scanme.nmap.org' | dnsx -silent"])
    print(res.output.decode('utf-8'))
    
    print("\n--- Testing web_httpx ---")
    res = kali.exec_run("httpx -u http://scanme.nmap.org -title -tech-detect -silent")
    print(res.output.decode('utf-8'))
    
    print("\n--- Testing web_wpscan ---")
    res = kali.exec_run("wpscan --url http://scanme.nmap.org --no-update")
    out = res.output.decode('utf-8')
    print("[wpscan output truncated]" if "Scan Aborted" in out else out[:500])
    
    target_ip = "172.17.0.2"
    
    print("\n--- Testing nmap_aggressive_scan ---")
    res = kali.exec_run(f"nmap -A -T4 -p 21 {target_ip}")
    print(res.output.decode('utf-8')[-500:])
    
    print("\n--- Testing nmap_port_scan ---")
    res = kali.exec_run(f"nmap -p 21,22 {target_ip}")
    print(res.output.decode('utf-8')[-300:])
    
    print("\n--- Testing nmap_script_scan ---")
    res = kali.exec_run(f"nmap --script vuln -p 21 {target_ip}")
    print(res.output.decode('utf-8')[-500:])
    
    print("\n--- Testing nmap_custom_scan ---")
    res = kali.exec_run(f"nmap -sU -p 161 {target_ip}")
    print(res.output.decode('utf-8')[-300:])
    
    print("\n--- Testing network_ncat ---")
    kali.exec_run("ncat -l -p 4444 -e /bin/bash", detach=True)
    res = kali.exec_run("ncat 127.0.0.1 4444 -c 'echo Hello from ncat'")
    print(res.output.decode('utf-8'))
    
    print("[*] Tearing down container...")
    kali.stop()

if __name__ == "__main__":
    asyncio.run(test_misc())
