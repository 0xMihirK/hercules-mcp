# Background-job recovery

Real Hercules tools in a disposable local lab. Model decisions and this report are scripted.

## Verified observations

### 3. shell_exec_background
I will start a bounded background request and retain its output. A slow service should not stall the entire investigation.

Actual response excerpt:
```text
tool: shell_exec_background
job_id: lab-recovery
message: Process started in background. Use shell_check_job to see live output.
```

### 4. shell_check_job
I will inspect the job using the ID Hercules actually returned, keeping partial output visible.

Actual response excerpt:
```text
tool: shell_check_job
job_id: lab-recovery
pid: 31
pgid: 31
is_running: False
state: completed
generation: 1
stale: False
created_at: 2026-10-07T10:14:24.369841+00:00
updated_at: 2026-10-07T10:15:14.554023+00:00
finished_at: 2026-10-07T10:14:34Z
exit_code: 0
total_lines: 3
showing_last: 30
output: Starting scoped lab probe
Slow endpoint exceeded the bounded request timeout
Narrow the next check to /health

log_path: /opt/workspace/jobs/lab-recovery.log
```

### 5. workspace_read_file
The request exceeded its one-second budget. I will preserve that diagnostic and narrow the investigation rather than report the service as absent.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/slow-partial.txt
encoding: text
bytes: 77
total_bytes: 77
offset: 0
truncated: False
next_offset: None
content: curl: (28) Operation timed out after 1002 milliseconds with 0 bytes received

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
duration_seconds: 0.16
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

### 7. workspace_read_file
The narrow health request succeeded. This confirms a slow endpoint rather than a complete service outage.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/health.txt
encoding: text
bytes: 196
total_bytes: 196
offset: 0
truncated: False
next_offset: None
content: HTTP/1.0 200 OK
Server: AtlasLab/1.0 
Date: Wed, 07 Oct 2026 10:15:43 GMT
Content-Type: application/json
Content-Length: 37
X-Hercules-Lab: disposable

{"status": "ok", "remediated": false}
```

### 8. shell_check_job
I will verify the background job's final state before cleanup and reporting.

Actual response excerpt:
```text
tool: shell_check_job
job_id: lab-recovery
pid: 31
pgid: 31
is_running: False
state: completed
generation: 1
stale: False
created_at: 2026-10-07T10:14:24.369841+00:00
updated_at: 2026-10-07T10:16:07.218547+00:00
finished_at: 2026-10-07T10:14:34Z
exit_code: 0
total_lines: 3
showing_last: 30
output: Starting scoped lab probe
Slow endpoint exceeded the bounded request timeout
Narrow the next check to /health

log_path: /opt/workspace/jobs/lab-recovery.log
```

### 9. shell_exec
I will record the revised scope and verified recovery alongside the partial output.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: Recovery: slow request timed out at its explicit budget; fresh /health probe succeeded.

stderr: 
duration_seconds: 0.25
command: bash /opt/workspace/tmp/shell_65b4b56296114314b7e78137322fd5c3.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 88
stderr_chars: 0
stdout_bytes: 88
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 88
inline_stderr_chars: 0
estimated_inline_tokens: 22
```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
