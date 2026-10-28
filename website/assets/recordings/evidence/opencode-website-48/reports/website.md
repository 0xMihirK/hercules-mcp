# Web and API exposure

Hercules tool results from a disposable local lab.

## Verified observations

### 3. fuzz_dirs
I will discover only the fixture's small route list, with bounded concurrency and a retained tool result.

Actual response excerpt:
```text
tool: fuzz_dirs
target: http://172.30.95.10:8000
fuzzer: ffuf
exit_code: 0
stderr: 
duration_seconds: 2.23
command: ffuf -u http://172.30.95.10:8000/FUZZ -w /opt/workspace/paths.txt -t 2 -ic -s -json -mc all -fc 404 -rate 15
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 1708
stderr_chars: 30
stdout_bytes: 1708
stderr_bytes: 30
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 427
requested_timeout_seconds: 600
effective_timeout_seconds: 600
raw_artifact: /opt/workspace/logs/exec_raw_20261027_043648_662805.txt
raw_artifacts: combined: /opt/workspace/logs/exec_raw_20261027_043648_662805.txt
filter_notes: output transformed; see output_transform statistics
raw output preserved in artifact
output_transform: stream: stderr
type: terminal_render
semantic: False
removed_lines: 7
removed_chars: 30
filter_version: 1
results: input: FFUFHASH: ODY0NGUx
FUZZ: cm9ib3RzLnR4dA==
position: 1
status: 200
length: 52
words: 4
lines: 4
content-type: 
```

### 4. web_scan
Directory discovery found a lead. I will fingerprint the actual application before selecting a verification check.

Actual response excerpt:
```text
tool: web_scan
selected_tool: whatweb
target: http://172.30.95.10:8000
exit_code: 0
stdout: http://172.30.95.10:8000 [200 OK] Country[RESERVED][ZZ], HTML5, HTTPServer[AtlasLab/1.0], IP[172.30.95.10], PasswordField[password], Title[Atlas lab — sign in], UncommonHeaders[x-hercules-lab]

stderr: 
duration_seconds: 2.87
command: whatweb -a 1 --color=NEVER  http://172.30.95.10:8000
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 193
stderr_chars: 0
stdout_bytes: 195
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 193
inline_stderr_chars: 0
estimated_inline_tokens: 49
requested_timeout_seconds: 120
effective_timeout_seconds: 120
```

### 5. nuclei_write_template
I will author a local Nuclei check requiring both HTTP 200 and the explicit disposable debug marker.

Actual response excerpt:
```text
tool: nuclei_write_template
path: /opt/workspace/nuclei-templates/lab-debug.yaml
message: Template written to /opt/workspace/nuclei-templates/lab-debug.yaml
```

### 6. nuclei_run
I will run only this local template. Built-in online template updates and interactsh are disabled.

Actual response excerpt:
```text
tool: nuclei_run
targets: http://172.30.95.10:8000
exit_code: 0
stderr: 
duration_seconds: 3.37
command: nuclei -jsonl -nc -or -ot -silent -target http://172.30.95.10:8000 -rate-limit 10 -t /opt/workspace/nuclei-templates/lab-debug.yaml -duc -ni
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 659
stderr_chars: 0
stdout_bytes: 659
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 165
requested_timeout_seconds: 600
effective_timeout_seconds: 600
raw_artifact: /opt/workspace/logs/nuclei_raw_20261027_043723_697885.txt
raw_artifacts: combined: /opt/workspace/logs/nuclei_raw_20261027_043723_697885.txt
filter_notes: raw output preserved in artifact
matches: template-id: hercules-lab-debug
template-path: /opt/workspace/nuclei-templates/lab-debug.yaml
info: name: Disposable Atlas debug endpoint
author: hercules-showcase
tags: None
severity: info
type: http
host: 172.30.95.10
port: 8000
scheme: http
url: http://172.30.95.10:80
```

### 7. network_curl
I will test the suspected backup route independently. Its normal 404 must be rejected rather than counted as an exposure.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.95.10:8000/backup
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.13
command: curl -s -X GET --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/backup-404.html http://172.30.95.10:8000/backup
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

### 8. browser_skill
Before browser operations, I will read Hercules's actual browser guidance and use fresh snapshots for targeting.

Actual response excerpt:
```text
tool: browser_skill
skill: core
exit_code: 0
stdout: ---
name: core
description: Core agent-browser usage guide. Read this before running any agent-browser commands. Covers the snapshot-and-ref workflow, navigating pages, interacting with elements (click, fill, type, select), extracting text and data, taking screenshots, managing tabs, handling forms and auth, waiting for content, running multiple browser sessions in parallel, and troubleshooting common failures. Use when the user asks to interact with a website, fill a form, click something, extract data, take a screenshot, log into a site, test a web app, or automate any browser task.
allowed-tools: Bash(agent-browser:*), Bash(npx agent-browser:*)
---

# agent-browser core

Fast browser automation CLI for AI agents. Chrome/Chromium via CDP, no Playwright or Puppeteer dependency. Accessibility-tree snapshots with compact `@eN` refs let agents interact with pages in ~200-400 tokens instead of parsing raw HTML.

Most normal web tasks (navigate, read, click, fill, extract, screenshot) are covered here. Load a specialized skill when the
```

### 9. browser_open
I will confirm the debug response in the browser before accepting the scanner lead.

Actual response excerpt:
```text
tool: browser_open
url: http://172.30.95.10:8000/debug
session: review
stealth: Obscura TLS/fingerprint profile; tracker blocking disabled
proxy_enabled: False
proxy_host: 
timezone: 
locale: 
session_relaunched: False
next_step: Call browser_snapshot to see the page and obtain @refs.
exit_code: 0
stderr: 
duration_seconds: 0.41
command: agent-browser --json --session review open http://172.30.95.10:8000/debug
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 366
stderr_chars: 0
stdout_bytes: 366
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 92
requested_timeout_seconds: 120
effective_timeout_seconds: 120
browser_result: success: True
data: lifecycle: effectiveLaunch: browserLaunched: True
engine: obscura
launchHash: 15879720535023231675
launched: False
relaunchedBrowser: False
restartedBackground: False
restoreStatus: not_configured
reused: True
saveStatus: not_attempted
targetId: page-1
title: 
url: http://172.30
```

### 10. browser_read
The browser confirms the disposable debug data. I will document this limited exposure without inventing credentials or exploitability.

Actual response excerpt:
```text
tool: browser_read
session: review
exit_code: 0
stderr: 
duration_seconds: 0.22
command: agent-browser --json --session review get text body
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 453
stderr_chars: 0
stdout_bytes: 453
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 114
requested_timeout_seconds: 30
effective_timeout_seconds: 30
browser_result: success: True
data: lifecycle: effectiveLaunch: browserLaunched: True
engine: obscura
launchHash: 15879720535023231675
launched: False
relaunchedBrowser: False
restartedBackground: False
restoreStatus: not_configured
reused: True
saveStatus: not_attempted
origin: http://172.30.95.10:8000/debug
text: {"build": "lab-2026.10", "debug": true, "environment": "disposable", "credentials": "none"}
error: None
structured_output: True
stdout_replaced_by: browser_result
browser_backend: obscura
csp_enforced: False
native_browser_downloads: False
warnings: Obscura does NOT enfor
```

### 11. browser_screenshot
I will save visual evidence alongside the raw HTTP and scanner artifacts.

Actual response excerpt:
```text
tool: browser_screenshot
session: review
path: /opt/workspace/browser/review/artifacts/debug.png
mime_type: image/png
annotated: False
exit_code: 0
stdout: ✓ Screenshot saved to /opt/workspace/browser/review/artifacts/debug.png

stderr: 
duration_seconds: 0.2
command: agent-browser --session review screenshot /opt/workspace/browser/review/artifacts/debug.png
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 72
stderr_chars: 0
stdout_bytes: 74
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 72
inline_stderr_chars: 0
estimated_inline_tokens: 18
requested_timeout_seconds: 90
effective_timeout_seconds: 90
bytes: 11330
width: 1280
height: 720
browser_backend: obscura
csp_enforced: False
native_browser_downloads: False
warnings: Obscura does NOT enforce CSP. Script execution is not proof of a Chromium CSP bypass. Native browser downloads are unsupported. The browser has NO SSRF boundary on host networking: it can reach host-local, LAN, and cloud-metadata (169.254.169.254)
```

### 12. network_curl
The profile endpoint is a separate hypothesis. I will test it without a session rather than assume the debug exposure grants account access.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.95.10:8000/api/profile
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.22
command: curl -s -X GET --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/profile-denied.json http://172.30.95.10:8000/api/profile
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
The API rejects unauthenticated access. I will keep this negative control out of the findings list.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/profile-denied.json
encoding: text
bytes: 196
total_bytes: 196
offset: 0
truncated: False
next_offset: None
content: HTTP/1.0 401 Unauthorized
Server: AtlasLab/1.0 
Date: Tue, 27 Oct 2026 04:38:58 GMT
Content-Type: application/json
Content-Length: 27
X-Hercules-Lab: disposable

{"error": "login required"}
```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
