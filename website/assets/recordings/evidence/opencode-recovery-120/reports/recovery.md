# Timeout and job recovery

Hercules tool results from a disposable local lab.

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
pid: 61
pgid: 61
is_running: False
state: completed
generation: 1
stale: False
created_at: 2026-10-27T06:32:28.404547+00:00
updated_at: 2026-10-27T06:33:13.805088+00:00
finished_at: 2026-10-27T06:32:36Z
exit_code: 0
total_lines: 3
showing_last: 30
output: Starting scoped lab probe
Slow endpoint exceeded the bounded request timeout
Narrow the next check to /health

log_path: /opt/workspace/jobs/lab-recovery.log
```

### 5. system_list_sessions
I will inspect Hercules's current managed-job inventory; a harness task identifier would not identify this shell job.

Actual response excerpt:
```text
tool: system_list_sessions
active_session: 66989b0e
total_sessions: 1
sessions: session_id: 66989b0e
is_active: True
file_count: 16
total_size_mb: 0.02
path: C:\Users\Mihir Katoch\OneDrive\Documents\ChatGPT\hercules-mcp\website\test-results\labs\opencode-recovery-120-1793082654505406800\workspace\66989b0e
total_bytes: 17122
created_at: 2026-10-27T06:31:05.620614+00:00
last_used_at: 2026-10-27T06:33:27.566976+00:00
state: active
generation: 1
pinned: False
owned: True
retention_eligible: False
host_workspace: C:\Users\Mihir Katoch\OneDrive\Documents\ChatGPT\hercules-mcp\website\test-results\labs\opencode-recovery-120-1793082654505406800\workspace\66989b0e
container_workspace: /opt/workspace
session_id: 66989b0e
generation: 1
container_running: True
runtime_state: attached
runtime_state_source: manager_attachment_not_docker_inspection
workspace_state_source: recorded_manifest
current_owner: pid: 38672
instance_id: e47d042672d74b0c8a29feeab6fbb3b9
job_inventory: jobs: job_id: lab-recovery
state: completed
generation: 1
stale: False
log_path: /opt/workspace/jobs/lab-recovery.log
truncate
```

### 6. workspace_read_file
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
content: curl: (28) Operation timed out after 1001 milliseconds with 0 bytes received

```

### 7. network_curl
I will confirm that the discovered HTTP service responds, retaining the response as a file.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.95.10:8000/health
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 1.42
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

### 8. workspace_read_file
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
Date: Tue, 27 Oct 2026 06:33:48 GMT
Content-Type: application/json
Content-Length: 37
X-Hercules-Lab: disposable

{"status": "ok", "remediated": false}
```

### 9. shell_check_job
I will verify the background job's final state before cleanup and reporting.

Actual response excerpt:
```text
tool: shell_check_job
job_id: lab-recovery
pid: 61
pgid: 61
is_running: False
state: completed
generation: 1
stale: False
created_at: 2026-10-27T06:32:28.404547+00:00
updated_at: 2026-10-27T06:34:09.721344+00:00
finished_at: 2026-10-27T06:32:36Z
exit_code: 0
total_lines: 3
showing_last: 30
output: Starting scoped lab probe
Slow endpoint exceeded the bounded request timeout
Narrow the next check to /health

log_path: /opt/workspace/jobs/lab-recovery.log
```

### 10. shell_exec
I will record the revised scope and verified recovery alongside the partial output.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: Recovery: slow request timed out at its explicit budget; fresh /health probe succeeded.

stderr: 
duration_seconds: 0.25
command: bash /opt/workspace/tmp/shell_f1fb51f53e854fed997b0ae9cd0a2035.sh
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
requested_timeout_seconds: 45
effective_timeout_seconds: 45
```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
