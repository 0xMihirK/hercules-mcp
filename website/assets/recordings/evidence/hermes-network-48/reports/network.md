# Network inventory

Real Hercules tools in a disposable local lab. Model decisions and this report are scripted.

## Verified observations

### 3. recon_dns
I will query the lab DNS server directly. The result will establish the local address before service discovery.

Actual response excerpt:
```text
tool: recon_dns
selected_tool: dig
target: 172.30.82.10
command: dig @172.30.82.10 172.30.82.10 A
exit_code: 0
stdout: 
; <<>> DiG 9.20.27-2-Debian <<>> @172.30.82.10 172.30.82.10 A
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 21695
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;172.30.82.10.			IN	A

;; ANSWER SECTION:
172.30.82.10.		60	IN	A	172.30.82.10

;; Query time: 0 msec
;; SERVER: 172.30.82.10#53(172.30.82.10) (UDP)
;; WHEN: Wed Oct 07 10:24:19 UTC 2026
;; MSG SIZE  rcvd: 46


stderr: 
duration_seconds: 0.2
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 479
stderr_chars: 0
stdout_bytes: 479
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 479
inline_stderr_chars: 0
estimated_inline_tokens: 120
```

### 4. nmap_scan
DNS is confirmed. I will map only the three scoped service ports; an open port alone will not establish a vulnerability.

Actual response excerpt:
```text
tool: nmap_scan
mode: port
target: 172.30.82.10
ports: 8000,8080,8443
exit_code: 0
stderr: 
duration_seconds: 0.23
command: nmap -p 8000,8080,8443 -Pn -sT -oX - 172.30.82.10
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 1626
stderr_chars: 0
stdout_bytes: 1626
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 407
raw_artifact: /opt/workspace/logs/exec_raw_20261007_102427_592577.txt
raw_artifacts: combined: /opt/workspace/logs/exec_raw_20261007_102427_592577.txt
filter_notes: raw output preserved in artifact
parsed: scanner: nmap
start_time: 1791368667
host_count: 1
hosts: status: up
addresses: addr: 172.30.82.10
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

### 5. shell_exec
The ports are reachable. I will verify service behavior with version detection and retain both text and XML output.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: Starting Nmap 7.99 ( https://nmap.org ) at 2026-10-07 10:24 +0000
Nmap scan report for hercules-capture-374b1467e0f5-fixture.hercules-capture-374b1467e0f5-net (172.30.82.10)
Host is up (0.00016s latency).

PORT     STATE SERVICE        VERSION
8000/tcp open  http-alt?
8080/tcp open  http-proxy?
8443/tcp open  ssl/https-alt?
2 services unrecognized despite returning data. If you know the service/version, please submit the following fingerprints at https://nmap.org/cgi-bin/submit.cgi?new-service :
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port8000-TCP:V=7.99%I=2%D=10/7%Time=6AC61DF3%P=x86_64-pc-linux-gnu%r(Ge
SF:tRequest,2DD,"HTTP/1\.0\x20200\x20OK\r\nServer:\x20AtlasLab/1\.0\x20\r\
SF:nDate:\x20Wed,\x2007\x20Oct\x202026\x2010:24:51\x20GMT\r\nContent-Type:
SF:\x20text/html;\x20charset=utf-8\r\nContent-Length:\x20565\r\nX-Hercules
SF:-Lab:\x20disposable\r\n\r\n<!doctype\x20html><html\x20lang=\"en\"><titl
SF:e>Atlas\x20lab\x20\xe2\x80\x94\x20sign\x20in</title>\n<style>body{font:
SF:18px\x20system-ui;max-width:540px
```

### 6. network_curl
I will confirm that the discovered HTTP service responds, retaining the response as a file.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.82.10:8000/health
redirects_followed: False
redirect_note: Redirect following is disabled while target scopes are configured.
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.17
command: curl -s -X GET --proto =http,https -i --max-time 5 -o /opt/workspace/artifacts/health.txt http://172.30.82.10:8000/health
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

### 7. network_curl
The HTTP service is healthy. I will inspect its declared routes before interpreting what the application exposes.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.82.10:8000/robots.txt
redirects_followed: False
redirect_note: Redirect following is disabled while target scopes are configured.
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.22
command: curl -s -X GET --proto =http,https -i --max-time 5 -o /opt/workspace/artifacts/robots.txt http://172.30.82.10:8000/robots.txt
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

### 8. shell_exec
I will verify the lab certificate with its supplied CA; I will not disable certificate validation.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: Connecting to 172.30.82.10
Can't use SSL_get_servername
depth=0 CN=lab
verify return:1
CONNECTED(00000003)
---
Certificate chain
 0 s:CN=lab
   i:CN=lab
   a:PKEY: RSA, 2048 (bit); sigalg: sha256WithRSAEncryption
   v:NotBefore: Oct  7 10:21:16 2026 GMT; NotAfter: Nov  6 10:21:16 2026 GMT
---
Server certificate
-----BEGIN CERTIFICATE-----
MIIDEzCCAfugAwIBAgIUdqP9luYl4pXvQRjq0Aq6D0VYAW0wDQYJKoZIhvcNAQEL
BQAwDjEMMAoGA1UEAwwDbGFiMB4XDTI2MTAwNzEwMjExNloXDTI2MTEwNjEwMjEx
NlowDjEMMAoGA1UEAwwDbGFiMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKC
AQEAx1D/xysvD9zg8i30DpyAcDcj9gRr6PR1D8SXHzB5VybMChmtCDRqC8NHh+BZ
65oGn0jSUjXC3ho5tm30h142zez/Wc3KrIjBsmbeHF+v4n2v2QIch6ZqKFR0EyXM
V3JOhv9f8UBj0kb/2GV8dlYu4jmwi2uwq8QWKoiV4ojPU40V/oAaqtpaVloFSW7f
CS001auh2xttTlgnv11DBEIEF3I7ESdAan/p0O5I+u8uyktw+rsWNi0PdeobLn5q
mOx/si3fshAIMjWgvMqzFx0WH6mLh0QlM48k8XoLU8XnHldBe9nr7jb7SG9tvCeo
NsbBHgBf49VFuc/d+wAm5xff0wIDAQABo2kwZzAdBgNVHQ4EFgQUnz/nuyuQ28eX
3BV3CuvEYCIfRnUwHwYDVR0jBBgwFoAUnz/nuyuQ28eX3BV3CuvEYCIfRnUwDwYD
VR0TAQH/BAUwAwEB/zAUBgNVHREEDTALggNsYWKHBKweUgowDQYJKoZIhvcNAQEL
BQADgg
```

### 9. workspace_read_file
I will inspect the structured scan artifact before writing the inventory. The report should distinguish discovery from verified application behavior.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/services.xml
encoding: text
bytes: 4096
total_bytes: 8110
offset: 0
truncated: True
next_offset: 4096
content: <?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<?xml-stylesheet href="file:///usr/share/nmap/nmap.xsl" type="text/xsl"?>
<!-- Nmap 7.99 scan initiated Wed Oct  7 10:24:44 2026 as: /usr/lib/nmap/nmap -Pn -sT -sV -&#45;version-light -p 8000,8080,8443 -oA /opt/workspace/artifacts/services 172.30.82.10 -->
<nmaprun scanner="nmap" args="/usr/lib/nmap/nmap -Pn -sT -sV -&#45;version-light -p 8000,8080,8443 -oA /opt/workspace/artifacts/services 172.30.82.10" start="1791368684" startstr="Wed Oct  7 10:24:44 2026" version="7.99" xmloutputversion="1.05">
<scaninfo type="connect" protocol="tcp" numservices="3" services="8000,8080,8443"/>
<verbose level="0"/>
<debugging level="0"/>
<host starttime="1791368684" endtime="1791368701"><status state="up" reason="user-set" reason_ttl="0"/>
<address addr="172.30.82.10" addrtype="ipv4"/>
<hostnames>
<hostname name="hercules-capture-374b1467e0f5-fixture.hercules-capture-374b1467e
```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
