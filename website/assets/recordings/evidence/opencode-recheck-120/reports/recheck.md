# Remediation proof

Hercules tool results from a disposable local lab.

## Verified observations

### 3. network_curl
I will capture the baseline response before changing the disposable configuration.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/debug
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.36
command: curl -s -X GET --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/before.txt http://172.30.96.10:8000/debug
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

### 4. workspace_read_file
The baseline confirms the fixture debug endpoint. I will retain it for a direct before/after comparison.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/before.txt
encoding: text
bytes: 250
total_bytes: 250
offset: 0
truncated: False
next_offset: None
content: HTTP/1.0 200 OK
Server: AtlasLab/1.0 
Date: Tue, 27 Oct 2026 06:22:01 GMT
Content-Type: application/json
Content-Length: 91
X-Hercules-Lab: disposable

{"build": "lab-2026.10", "debug": true, "environment": "disposable", "credentials": "none"}
```

### 5. network_curl
I will apply only the explicitly scoped fixture remediation. This changes no production or external service.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/lab-control/remediate
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 1.71
command: curl -s -X POST --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/change.txt http://172.30.96.10:8000/lab-control/remediate
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

### 6. network_curl
I will repeat the same debug request after the change, keeping its response separate from the baseline.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/debug
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 1.66
command: curl -s -X GET --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/after.txt http://172.30.96.10:8000/debug
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

### 7. workspace_read_file
The endpoint now returns 404. I will verify the new headers and compare the two saved responses.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/after.txt
encoding: text
bytes: 276
total_bytes: 276
offset: 0
truncated: False
next_offset: None
content: HTTP/1.0 404 Not Found
Server: AtlasLab/1.0 
Date: Tue, 27 Oct 2026 06:22:30 GMT
Content-Type: application/json
Content-Length: 9
X-Hercules-Lab: disposable
Content-Security-Policy: default-src 'self'; frame-ancestors 'none'
X-Content-Type-Options: nosniff

Not found
```

### 8. network_curl
I will confirm that the application remains healthy after remediation.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/health
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 1.73
command: curl -s -X GET --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/recheck-health.txt http://172.30.96.10:8000/health
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

### 9. shell_exec
I will require the expected before/after statuses and policy headers in the actual saved evidence before declaring remediation verified.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: {
  "baseline_debug": true,
  "debug_closed": true,
  "csp_present": true,
  "nosniff_present": true
}

stderr: 
duration_seconds: 0.62
command: bash /opt/workspace/tmp/shell_18787ffa314941e08104f965c868ce8a.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 103
stderr_chars: 0
stdout_bytes: 103
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 103
inline_stderr_chars: 0
estimated_inline_tokens: 26
requested_timeout_seconds: 45
effective_timeout_seconds: 45
```

### 10. workspace_read_file
The comparison artifact is present and readable. I will report the observed fix and the checks that were not performed.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/comparison.json
encoding: text
bytes: 102
total_bytes: 102
offset: 0
truncated: False
next_offset: None
content: {
  "baseline_debug": true,
  "debug_closed": true,
  "csp_present": true,
  "nosniff_present": true
}
```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
