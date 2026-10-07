# Service assessment

Real Hercules tools in a disposable local lab. Model decisions and this report are scripted.

## Verified observations

### 3. nmap_scan
DNS is confirmed. I will map only the three scoped service ports; an open port alone will not establish a vulnerability.

Actual response excerpt:
```text
tool: nmap_scan
mode: port
target: 172.30.80.10
ports: 8000,8080,8443
exit_code: 0
stderr: 
duration_seconds: 0.16
command: nmap -p 8000,8080,8443 -Pn -sT -oX - 172.30.80.10
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 1625
stderr_chars: 0
stdout_bytes: 1625
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 407
raw_artifact: /opt/workspace/logs/exec_raw_20261007_102207_316948.txt
raw_artifacts: combined: /opt/workspace/logs/exec_raw_20261007_102207_316948.txt
filter_notes: raw output preserved in artifact
parsed: scanner: nmap
start_time: 1791368527
host_count: 1
hosts: status: up
addresses: addr: 172.30.80.10
addrtype: ipv4
ports: portid: 8000
protocol: tcp
state: open
service: name: http-alt
product: None
version: None
portid: 8080
protocol: tcp
state: open
service: name: http-proxy
product: None
version: None
portid: 8443
protocol: tcp
state: open
service: name: https-alt
product: None
version: None
structured_
```

### 4. shell_exec
I will obtain service-detection evidence before consulting vulnerability references.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: Starting Nmap 7.99 ( https://nmap.org ) at 2026-10-07 10:22 +0000
Nmap scan report for hercules-capture-939b6807bd7e-fixture.hercules-capture-939b6807bd7e-net (172.30.80.10)
Host is up (0.0000080s latency).

PORT     STATE SERVICE   VERSION
8000/tcp open  http-alt?
1 service unrecognized despite returning data. If you know the service/version, please submit the following fingerprint at https://nmap.org/cgi-bin/submit.cgi?new-service :
SF-Port8000-TCP:V=7.99%I=2%D=10/7%Time=6AC61D66%P=x86_64-pc-linux-gnu%r(Ge
SF:tRequest,2DD,"HTTP/1\.0\x20200\x20OK\r\nServer:\x20AtlasLab/1\.0\x20\r\
SF:nDate:\x20Wed,\x2007\x20Oct\x202026\x2010:22:30\x20GMT\r\nContent-Type:
SF:\x20text/html;\x20charset=utf-8\r\nContent-Length:\x20565\r\nX-Hercules
SF:-Lab:\x20disposable\r\n\r\n<!doctype\x20html><html\x20lang=\"en\"><titl
SF:e>Atlas\x20lab\x20\xe2\x80\x94\x20sign\x20in</title>\n<style>body{font:
SF:18px\x20system-ui;max-width:540px;margin:80px\x20auto;background:#e9e9e
SF:6;color:#242424}label,input,button{display:block;margin:12px\x200}input
SF:,button{padding:12px
```

### 5. network_curl
I will retain the actual headers and page, then compare them with the scanner's service classification.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.80.10:8000
redirects_followed: False
redirect_note: Redirect following is disabled while target scopes are configured.
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.19
command: curl -s -X GET --proto =http,https -i --max-time 5 -D /opt/workspace/artifacts/headers.txt -o /opt/workspace/artifacts/home.html http://172.30.80.10:8000
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 0
stderr_chars: 0
stdout_bytes: 0
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 0
```

### 6. searchsploit
I will search the local Exploit-DB catalog for HTTP-server leads. This is reference gathering, not exploitation.

Actual response excerpt:
```text
tool: searchsploit
action: search
query: http
degraded_from: http server
message: Returned output from the broadest attempted query; try a broader service, product, or CVE term if no useful entries are present.
exit_code: 0
stdout: {
	"SEARCH": "http",
	"DB_PATH_EXPLOIT": "/usr/share/exploitdb",
	"RESULTS_EXPLOIT": [
		{"Title":"(Gabriel's FTP Server) Open & Compact FTP Server 1.2 - 'PORT' Remote Denial of Service","EDB-ID":"12698","Date_Published":"2010-05-22","Date_Added":"2010-05-21","Date_Updated":"","Author":"Ma3sTr0-Dz","Type":"dos","Platform":"windows","Port":"","Verified":"1","Codes":"","Tags":"","Aliases":"","Screenshot":"","Application":"http://www.exploit-db.comopen-ftpd.1.2.tar.gz","Source":"","Path":"/usr/share/exploitdb/exploits/windows/dos/12698.py"},
		{"Title":"(Gabriel's FTP Server) Open & Compact FTP Server 1.2 - Authentication Bypass / Directory Traversal SAM Retrieval","EDB-ID":"27401","Date_Published":"2013-08-07","Date_Added":"2013-08-07","Date_Updated":"2013-08-07","Author":"Wireghoul","Type":"remote","Platform":"windows","Port":"","Verified":"1","Codes":"CVE-
```

### 7. searchsploit
A reference exists. I will read it and compare its product and prerequisites with the Atlas lab evidence.

Actual response excerpt:
```text
tool: searchsploit
action: get
id: 12698
exploit_content: 
exploit_path: 
exploit_size: 0
exploit_bytes: 0
exploit_content_truncated: False
truncated: False
next_offset: None
artifact_path: 
mirror_output: [!] Could not find EDB-ID #



exit_code: 0
```

### 8. workspace_read_file
The lab identifies itself as AtlasLab. I will reject a generic catalog hit whose affected product or deployment prerequisites are not established.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/headers.txt
encoding: text
bytes: 168
total_bytes: 168
offset: 0
truncated: False
next_offset: None
content: HTTP/1.0 200 OK
Server: AtlasLab/1.0 
Date: Wed, 07 Oct 2026 10:22:51 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 565
X-Hercules-Lab: disposable


```

### 9. network_curl
I will verify the administrative route's actual response. A 403 is an access-control observation, not evidence of compromise.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.80.10:8000/admin
redirects_followed: False
redirect_note: Redirect following is disabled while target scopes are configured.
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.17
command: curl -s -X GET --proto =http,https -i --max-time 5 -o /opt/workspace/artifacts/admin-denied.html http://172.30.80.10:8000/admin
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 0
stderr_chars: 0
stdout_bytes: 0
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 0
```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
