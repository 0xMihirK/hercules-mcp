# TLS and protocol review

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
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 29445
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 0

;; QUESTION SECTION:
;172.30.95.10.			IN	A

;; ANSWER SECTION:
172.30.95.10.		60	IN	A	172.30.95.10

;; Query time: 0 msec
;; SERVER: 172.30.95.10#53(172.30.95.10) (UDP)
;; WHEN: Mon Oct 26 22:46:50 UTC 2026
;; MSG SIZE  rcvd: 46


stderr: 
duration_seconds: 0.14
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

### 4. network_curl
I will inspect the first redirect without following it, so each hop remains explicit.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.95.10:8080
redirects_followed: False
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.19
command: curl -s -X GET --proto =http,https -i --max-time 5 -o /opt/workspace/artifacts/redirect.txt http://172.30.95.10:8080
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
The first hop redirects to the local TLS endpoint. I will verify the certificate before requesting that destination.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/redirect.txt
encoding: text
bytes: 246
total_bytes: 246
offset: 0
truncated: False
next_offset: None
content: HTTP/1.0 302 Found
Server: AtlasLab/1.0 
Date: Mon, 26 Oct 2026 22:46:58 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 33
X-Hercules-Lab: disposable
Location: https://172.30.95.10:8443/login

Redirect to the lab TLS endpoint.
```

### 6. shell_exec
I will validate the actual chain with the supplied lab CA, preserving OpenSSL diagnostics.

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
   v:NotBefore: Oct 26 22:45:15 2026 GMT; NotAfter: Nov 25 22:45:15 2026 GMT
---
Server certificate
-----BEGIN CERTIFICATE-----
MIIDEzCCAfugAwIBAgIUQqivxl3zZJhg55kXU9m+d9piepowDQYJKoZIhvcNAQEL
BQAwDjEMMAoGA1UEAwwDbGFiMB4XDTI2MTAyNjIyNDUxNVoXDTI2MTEyNTIyNDUx
NVowDjEMMAoGA1UEAwwDbGFiMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKC
AQEAp+6IkpKqepy3+lQM9aT4x+s0O+lrQUbED4SjGRcI65zRZEcK3MU7yiiHATGu
W2gy+ZkZHLfQ30LAWueYwilK6XCJOy1hjoufHBLsPDGTPZpcI8jAsc2kaFAhvmth
CPF0oOW17dI51r4ah7pG3RJUPWggTGTLKar2sGEk3HnJb2NCx8kRcZ8aiqOXT0yV
Kt6WvlMBs6COUiLKF6B/h8Qn7YIaz+3i6r+/dVAIdm4LDDtHbWpLbFzkKD57gE+j
89wfjdRHmFGoK3D+FFpl09tz0c8zXIEzAri/scQRyUa/B+4g5Z0RM9yz3DudD30F
G7BXUz7NjD+TPdMWcbQfnSA5PwIDAQABo2kwZzAdBgNVHQ4EFgQUEqqRn1Al/FeB
8nq+Yn41uY7Is4QwHwYDVR0jBBgwFoAUEqqRn1Al/FeB8nq+Yn41uY7Is4QwDwYD
VR0TAQH/BAUwAwEB/zAUBgNVHREEDTALggNsYWKHBKweXwowDQYJKoZIhvcNAQEL
BQADgg
```

### 7. network_curl
The lab chain verifies. I will request the TLS page with certificate validation enabled and retain the response.

Actual response excerpt:
```text
tool: network_curl
url: https://172.30.95.10:8443/login
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 3.38
command: curl -s -X GET --proto =http,https -i -L --cacert /opt/workspace/lab-cert.pem --max-time 5 -o /opt/workspace/artifacts/tls-login.html https://172.30.95.10:8443/login
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
I will observe how the browser handles the redirect. A supplied curl CA does not automatically establish browser trust.

Actual response excerpt:
```text
tool: browser_open
url: http://172.30.95.10:8080
session: review
stealth: Obscura TLS/fingerprint profile; tracker blocking disabled
proxy_enabled: False
proxy_host: 
timezone: 
locale: 
session_relaunched: False
next_step: Call browser_snapshot to see the page and obtain @refs.
exit_code: 1
stdout: {"success":false,"data":null,"error":"CDP error (Page.navigate): Network error: Network error: https://172.30.95.10:8443/login: error sending request for uri (https://172.30.95.10:8443/login): client error (Connect): [CERTIFICATE_VERIFY_FAILED]"}

stderr: 
duration_seconds: 0.4
command: agent-browser --json --session review open http://172.30.95.10:8080
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 247
stderr_chars: 0
stdout_bytes: 247
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 247
inline_stderr_chars: 0
estimated_inline_tokens: 62
requested_timeout_seconds: 120
effective_timeout_seconds: 120
browser_backend: obscura
csp_enforced: False
native_browser_downloads:
```

### 10. browser_open
I will check the live local page in the native browser backend rather than infer behavior from headers.

Actual response excerpt:
```text
tool: browser_open
url: http://172.30.95.10:8000/login
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
duration_seconds: 0.17
command: agent-browser --json --session review open http://172.30.95.10:8000/login
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 385
stderr_chars: 0
stdout_bytes: 387
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 97
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
title: Atlas lab — sign in
```

### 11. browser_screenshot
I will retain the reachable HTTP page for comparison and report any browser trust limitation separately from TLS chain validation.

Actual response excerpt:
```text
tool: browser_screenshot
session: review
path: /opt/workspace/browser/review/artifacts/http-login.png
mime_type: image/png
annotated: False
exit_code: 0
stdout: ✓ Screenshot saved to /opt/workspace/browser/review/artifacts/http-login.png

stderr: 
duration_seconds: 2.17
command: agent-browser --session review screenshot /opt/workspace/browser/review/artifacts/http-login.png
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 77
stderr_chars: 0
stdout_bytes: 79
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 77
inline_stderr_chars: 0
estimated_inline_tokens: 20
requested_timeout_seconds: 90
effective_timeout_seconds: 90
bytes: 18557
width: 1280
height: 720
browser_backend: obscura
csp_enforced: False
native_browser_downloads: False
warnings: Obscura does NOT enforce CSP. Script execution is not proof of a Chromium CSP bypass. Native browser downloads are unsupported. The browser has NO SSRF boundary on host networking: it can reach host-local, LAN, and cloud-metadata (
```

### 12. shell_exec
I will send a minimal raw request with Ncat and compare its response with the structured HTTP checks.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: HTTP/1.0 200 OK
Server: AtlasLab/1.0 
Date: Mon, 26 Oct 2026 22:49:13 GMT
Content-Type: application/json
Content-Length: 37
X-Hercules-Lab: disposable

{"status": "ok", "remediated": false}
stderr: 
duration_seconds: 0.24
command: bash /opt/workspace/tmp/shell_ea80bff0798043f2b0d3bbf718963bed.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 196
stderr_chars: 0
stdout_bytes: 196
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 189
inline_stderr_chars: 0
estimated_inline_tokens: 48
requested_timeout_seconds: 45
effective_timeout_seconds: 45
raw_artifact: /opt/workspace/logs/exec_raw_20261026_224913_311450.txt
raw_artifacts: combined: /opt/workspace/logs/exec_raw_20261026_224913_311450.txt
filter_notes: output transformed; see output_transform statistics
raw output preserved in artifact
output_transform: stream: stdout
type: terminal_render
semantic: False
removed_lines: 0
removed_chars: 7
filter_version: 1
```

### 13. shell_exec
The same protocol path should reject an absent route; this checks that the manual request did not merely hit a catch-all page.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: HTTP/1.0 404 Not Found
Server: AtlasLab/1.0 
Date: Mon, 26 Oct 2026 22:49:33 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 59
X-Hercules-Lab: disposable

<h1>Not found</h1><p>This route is absent from the lab.</p>
stderr: 
duration_seconds: 0.24
command: bash /opt/workspace/tmp/shell_a27ce2c7586a49eb880be28667f69cb8.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 233
stderr_chars: 0
stdout_bytes: 233
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 226
inline_stderr_chars: 0
estimated_inline_tokens: 57
requested_timeout_seconds: 45
effective_timeout_seconds: 45
raw_artifact: /opt/workspace/logs/exec_raw_20261026_224934_005717.txt
raw_artifacts: combined: /opt/workspace/logs/exec_raw_20261026_224934_005717.txt
filter_notes: output transformed; see output_transform statistics
raw output preserved in artifact
output_transform: stream: stdout
type: terminal_render
semantic: False
removed_lines: 0
removed_chars: 7
fi
```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
