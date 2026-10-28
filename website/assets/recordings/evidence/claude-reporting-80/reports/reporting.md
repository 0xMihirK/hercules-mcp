# Credential controls and evidence

Hercules tool results from a disposable local lab.

## Verified observations

### 3. nmap_scan
DNS is confirmed. I will map only the three scoped service ports; an open port alone will not establish a vulnerability.

Actual response excerpt:
```text
tool: nmap_scan
mode: port
target: 172.30.96.10
ports: 8000,8080,8443
exit_code: 0
stderr: 
duration_seconds: 0.23
command: nmap -p 8000,8080,8443 -Pn -sT -oX - 172.30.96.10
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
raw_artifact: /opt/workspace/logs/exec_raw_20261026_233303_311208.txt
raw_artifacts: combined: /opt/workspace/logs/exec_raw_20261026_233303_311208.txt
filter_notes: raw output preserved in artifact
parsed: scanner: nmap
start_time: 1793057583
host_count: 1
hosts: status: up
addresses: addr: 172.30.96.10
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

### 4. network_curl
I will confirm that the discovered HTTP service responds, retaining the response as a file.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/health
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.21
command: curl -s -X GET --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/health.txt http://172.30.96.10:8000/health
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

### 5. workspace_read_file
The review log is larger than a concise inline answer. I will read its first bounded page and note that these are supplied inputs, not current scanner results.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/review-log.ndjson
encoding: text
bytes: 2048
total_bytes: 11882
offset: 0
truncated: True
next_offset: 2048
content: {"sequence": 0, "source": "lab-input", "path": "/debug", "status": 200}
{"sequence": 1, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 2, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 3, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 4, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 5, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 6, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 7, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 8, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 9, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 10, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 11, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 12, "source": "lab-input", "path": "/health", 
```

### 6. workspace_read_file
I will page the next bytes without silently assuming that the first chunk was the whole artifact.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/review-log.ndjson
encoding: text
bytes: 2048
total_bytes: 11882
offset: 2048
truncated: True
next_offset: 4096
content: atus": 200}
{"sequence": 28, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 29, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 30, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 31, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 32, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 33, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 34, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 35, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 36, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 37, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 38, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 39, "source": "lab-input", "path": "/health", "status": 200}
{"sequence": 40, "source": "lab-i
```

### 7. shell_exec
I will reconcile every log record with a full-file computation, not extrapolate from the two inline pages.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: {
  "records": 160,
  "debug_records": 8,
  "source": "authored lab input",
  "fresh_evidence": "artifacts/health.txt"
}

stderr: 
duration_seconds: 0.22
command: bash /opt/workspace/tmp/shell_096a303298554fc58cf8d415fcc937c1.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 121
stderr_chars: 0
stdout_bytes: 121
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 121
inline_stderr_chars: 0
estimated_inline_tokens: 31
requested_timeout_seconds: 45
effective_timeout_seconds: 45
```

### 8. network_curl
I will check the debug route now. The report must distinguish current evidence from the supplied historical log.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/debug
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.23
command: curl -s -X GET --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/current-debug.txt http://172.30.96.10:8000/debug
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

### 9. workspace_read_file
I will verify the reconciliation artifact and explicitly state what these inputs cannot establish.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/reconciled.json
encoding: text
bytes: 120
total_bytes: 120
offset: 0
truncated: False
next_offset: None
content: {
  "records": 160,
  "debug_records": 8,
  "source": "authored lab input",
  "fresh_evidence": "artifacts/health.txt"
}
```

### 10. network_curl
A wrong fixture password is the negative control. A generic HTTP response or noisy scanner output must not be read as credential success.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/login
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.17
command: curl -s -X POST --proto =http,https -i -L -d 'email=reviewer%40lab.test&password=*** --max-time 5 -o /opt/workspace/artifacts/credential-rejected.txt http://172.30.96.10:8000/login
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

### 11. workspace_read_file
I will verify the rejected response before testing the one supplied disposable account.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/credential-rejected.txt
encoding: text
bytes: 197
total_bytes: 197
offset: 0
truncated: False
next_offset: None
content: HTTP/1.0 401 Unauthorized
Server: AtlasLab/1.0 
Date: Mon, 26 Oct 2026 23:34:12 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 20
X-Hercules-Lab: disposable

Credentials rejected
```

### 12. network_curl
I will test only the fixture credential supplied for this lab; this is not password spraying or a general credential audit.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/login
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.2
command: curl -s -X POST --proto =http,https -i -L -d 'email=reviewer%40lab.test&password=*** --max-time 5 -D /opt/workspace/artifacts/credential-headers.txt -o /opt/workspace/artifacts/credential-accepted.txt http://172.30.96.10:8000/login
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

### 13. workspace_read_file
I will require the actual redirect and session header before marking the fixture account accepted.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/credential-headers.txt
encoding: text
bytes: 441
total_bytes: 441
offset: 0
truncated: False
next_offset: None
content: HTTP/1.0 303 See Other
Server: AtlasLab/1.0 
Date: Mon, 26 Oct 2026 23:34:28 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 30
X-Hercules-Lab: disposable
Location: /dashboard
Set-Cookie: atlas-session=lab-reviewer; HttpOnly; SameSite=Lax; Path=/

HTTP/1.0 404 Not Found
Server: AtlasLab/1.0 
Date: Mon, 26 Oct 2026 23:34:28 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 9
X-Hercules-Lab: disposable


```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
