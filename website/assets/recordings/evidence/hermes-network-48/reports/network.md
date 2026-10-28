# Service boundary map

Hercules tool results from a disposable local lab.

## Verified observations

### 3. recon_dns
I will query the lab DNS server directly. The result will establish the local address before service discovery.

Actual response excerpt:
```text
tool: recon_dns
selected_tool: dig
target: 172.30.95.10
command: dig @172.30.95.10 172.30.95.10 A
exit_code: 0
stdout: 
; <<>> DiG 9.20.27-2-Debian <<>> @172.30.95.10 172.30.95.10 A
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 53130
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;172.30.95.10.			IN	A

;; ANSWER SECTION:
172.30.95.10.		60	IN	A	172.30.95.10

;; Query time: 0 msec
;; SERVER: 172.30.95.10#53(172.30.95.10) (UDP)
;; WHEN: Tue Oct 27 07:30:27 UTC 2026
;; MSG SIZE  rcvd: 46


stderr: 
duration_seconds: 0.13
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
requested_timeout_seconds: 60
effective_timeout_seconds: 60
```

### 4. nmap_scan
DNS is confirmed. I will map only the three scoped service ports; an open port alone will not establish a vulnerability.

Actual response excerpt:
```text
tool: nmap_scan
mode: port
target: 172.30.95.10
ports: 8000,8080,8443
exit_code: 0
stderr: 
duration_seconds: 0.18
command: nmap -p 8000,8080,8443 -Pn -sT -oX - 172.30.95.10
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
requested_timeout_seconds: 300
effective_timeout_seconds: 300
raw_artifact: /opt/workspace/logs/exec_raw_20261027_073036_194036.txt
raw_artifacts: combined: /opt/workspace/logs/exec_raw_20261027_073036_194036.txt
filter_notes: raw output preserved in artifact
parsed: scanner: nmap
start_time: 1793086236
host_count: 1
hosts: status: up
addresses: addr: 172.30.95.10
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
se
```

### 5. shell_exec
The ports are reachable. I will verify service behavior with version detection and retain both text and XML output.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: Starting Nmap 7.99 ( https://nmap.org ) at 2026-10-27 07:30 +0000
Nmap scan report for hercules-capture-9d9bd4e9990a-fixture.hercules-capture-9d9bd4e9990a-net (172.30.95.10)
Host is up (0.00011s latency).

PORT     STATE SERVICE        VERSION
8000/tcp open  http-alt?
8080/tcp open  http-proxy?
8443/tcp open  ssl/https-alt?
2 services unrecognized despite returning data. If you know the service/version, please submit the following fingerprints at https://nmap.org/cgi-bin/submit.cgi?new-service :
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port8000-TCP:V=7.99%I=2%D=10/27%Time=6AE05333%P=x86_64-pc-linux-gnu%r(G
SF:etRequest,2DD,"HTTP/1\.0\x20200\x20OK\r\nServer:\x20AtlasLab/1\.0\x20\r
SF:\nDate:\x20Tue,\x2027\x20Oct\x202026\x2007:30:59\x20GMT\r\nContent-Type
SF::\x20text/html;\x20charset=utf-8\r\nContent-Length:\x20565\r\nX-Hercule
SF:s-Lab:\x20disposable\r\n\r\n<!doctype\x20html><html\x20lang=\"en\"><tit
SF:le>Atlas\x20lab\x20\xe2\x80\x94\x20sign\x20in</title>\n<style>body{font
SF::18px\x20system-ui;max-width:540p
```

### 6. network_curl
I will confirm that the discovered HTTP service responds, retaining the response as a file.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.95.10:8000/health
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.17
command: curl -s -X GET --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/health.txt http://172.30.95.10:8000/health
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
requested_timeout_seconds: 60
effective_timeout_seconds: 60
```

### 7. network_curl
The HTTP service is healthy. I will inspect its declared routes before interpreting what the application exposes.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.95.10:8000/robots.txt
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.14
command: curl -s -X GET --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/robots.txt http://172.30.95.10:8000/robots.txt
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
requested_timeout_seconds: 60
effective_timeout_seconds: 60
```

### 8. shell_exec
I will verify the lab certificate with its supplied CA; I will not disable certificate validation.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: Connecting to 172.30.95.10
Can't use SSL_get_servername
depth=0 CN=lab
verify return:1
CONNECTED(00000003)
---
Certificate chain
 0 s:CN=lab
   i:CN=lab
   a:PKEY: RSA, 2048 (bit); sigalg: sha256WithRSAEncryption
   v:NotBefore: Oct 27 07:27:32 2026 GMT; NotAfter: Nov 26 07:27:32 2026 GMT
---
Server certificate
-----BEGIN CERTIFICATE-----
MIIDEzCCAfugAwIBAgIUfNsi5JHyKahcFVHq+PlmRXOAM6EwDQYJKoZIhvcNAQEL
BQAwDjEMMAoGA1UEAwwDbGFiMB4XDTI2MTAyNzA3MjczMloXDTI2MTEyNjA3Mjcz
MlowDjEMMAoGA1UEAwwDbGFiMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKC
AQEAnfoFk4y+TBcZLBf9jvnRIl8U2anD6U7hj/Qjw9NA8I1USVDtGHZJQmeAAnPc
4z36ehzqNIgVcqw8t8os6iDHyXz0y7cAuEDv/4+Oc19UwvHFTY4yi0QGwTGWlnE/
vOYNq5PiktpndM99yUNq6vJHSD5IQaqwfYyPo45nZdkoQPtuTveWoaipyGxvZnuN
8deKRtZB0J4Yl33TZnGLEEAZcdw5AWTshLfbN2OcHyMrpgeu9u34G9KBaYYFWN/v
i7zLw/us756+G/HUa7KkNHKni7NGXAg8DqxTicrQddy52IpJNfEJJQ2Achfm2jas
iYy1NfeXaf+pJx8kDh7XYSENQQIDAQABo2kwZzAdBgNVHQ4EFgQURaUpB+tEP9Cw
p+0jPJ52WG3L1C4wHwYDVR0jBBgwFoAURaUpB+tEP9Cwp+0jPJ52WG3L1C4wDwYD
VR0TAQH/BAUwAwEB/zAUBgNVHREEDTALggNsYWKHBKweXwowDQYJKoZIhvcNAQEL
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
total_bytes: 8112
offset: 0
truncated: True
next_offset: 4096
content: <?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<?xml-stylesheet href="file:///usr/share/nmap/nmap.xsl" type="text/xsl"?>
<!-- Nmap 7.99 scan initiated Tue Oct 27 07:30:53 2026 as: /usr/lib/nmap/nmap -Pn -sT -sV -&#45;version-light -p 8000,8080,8443 -oA /opt/workspace/artifacts/services 172.30.95.10 -->
<nmaprun scanner="nmap" args="/usr/lib/nmap/nmap -Pn -sT -sV -&#45;version-light -p 8000,8080,8443 -oA /opt/workspace/artifacts/services 172.30.95.10" start="1793086253" startstr="Tue Oct 27 07:30:53 2026" version="7.99" xmloutputversion="1.05">
<scaninfo type="connect" protocol="tcp" numservices="3" services="8000,8080,8443"/>
<verbose level="0"/>
<debugging level="0"/>
<host starttime="1793086253" endtime="1793086269"><status state="up" reason="user-set" reason_ttl="0"/>
<address addr="172.30.95.10" addrtype="ipv4"/>
<hostnames>
<hostname name="hercules-capture-9d9bd4e9990a-fixture.hercules-capture-9d9bd4e99
```

### 10. shell_exec
The negative-control port should not look like an exposed service. I will save its actual result before drawing a network boundary.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: Starting Nmap 7.99 ( https://nmap.org ) at 2026-10-27 07:32 +0000
Nmap scan report for hercules-capture-9d9bd4e9990a-fixture.hercules-capture-9d9bd4e9990a-net (172.30.95.10)
Host is up (0.0000070s latency).

PORT     STATE  SERVICE
9999/tcp closed abyss

Nmap done: 1 IP address (1 host up) scanned in 0.03 seconds
# Nmap 7.99 scan initiated Tue Oct 27 07:32:16 2026 as: /usr/lib/nmap/nmap -Pn -sT -p 9999 -oN /opt/workspace/artifacts/closed-port.txt 172.30.95.10
Nmap scan report for hercules-capture-9d9bd4e9990a-fixture.hercules-capture-9d9bd4e9990a-net (172.30.95.10)
Host is up (0.0000070s latency).

PORT     STATE  SERVICE
9999/tcp closed abyss

# Nmap done at Tue Oct 27 07:32:16 2026 -- 1 IP address (1 host up) scanned in 0.03 seconds

stderr: 
duration_seconds: 0.22
command: bash /opt/workspace/tmp/shell_f1a39e58f38a470c90325dabf55eb336.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 745
stderr_chars: 0
stdout_bytes: 745
stderr_bytes: 0
stdout_chars_exact: True
```

### 11. workspace_read_file
I will include the negative control in the report so coverage is explicit.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/closed-port.txt
encoding: text
bytes: 430
total_bytes: 430
offset: 0
truncated: False
next_offset: None
content: # Nmap 7.99 scan initiated Tue Oct 27 07:32:16 2026 as: /usr/lib/nmap/nmap -Pn -sT -p 9999 -oN /opt/workspace/artifacts/closed-port.txt 172.30.95.10
Nmap scan report for hercules-capture-9d9bd4e9990a-fixture.hercules-capture-9d9bd4e9990a-net (172.30.95.10)
Host is up (0.0000070s latency).

PORT     STATE  SERVICE
9999/tcp closed abyss

# Nmap done at Tue Oct 27 07:32:16 2026 -- 1 IP address (1 host up) scanned in 0.03 seconds

```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
