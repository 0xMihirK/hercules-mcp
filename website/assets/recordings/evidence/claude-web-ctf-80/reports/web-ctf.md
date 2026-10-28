# Chained web CTF

Hercules tool results from a disposable local lab.

## Verified observations

### 3. network_curl
I will inspect declared routes before guessing endpoints.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/robots.txt
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 1.46
command: curl -s -X GET --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/robots.txt http://172.30.96.10:8000/robots.txt
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
The draft API is listed. I will test its unauthenticated behavior before exploring browser state.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/robots.txt
encoding: text
bytes: 205
total_bytes: 205
offset: 0
truncated: False
next_offset: None
content: HTTP/1.0 200 OK
Server: AtlasLab/1.0 
Date: Mon, 26 Oct 2026 23:22:31 GMT
Content-Type: text/plain
Content-Length: 52
X-Hercules-Lab: disposable

User-agent: *
Disallow: /debug
Disallow: /api/draft

```

### 5. network_curl
I will preserve the rejected request. It should tell us which prerequisite is missing.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/api/draft
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.2
command: curl -s -X GET --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/draft-denied.txt http://172.30.96.10:8000/api/draft
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

### 6. browser_skill
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

### 7. browser_open
The challenge offers a draft-session bootstrap. I will follow that local clue in the actual browser.

Actual response excerpt:
```text
tool: browser_open
url: http://172.30.96.10:8000/ctf/bootstrap
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
duration_seconds: 2.8
command: agent-browser --json --session review open http://172.30.96.10:8000/ctf/bootstrap
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 374
stderr_chars: 0
stdout_bytes: 374
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 94
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
url
```

### 8. browser_snapshot
The page reveals a route-header requirement. I will combine it with the disposable session cookie instead of putting the value in the URL.

Actual response excerpt:
```text
tool: browser_snapshot
session: review
exit_code: 0
stdout: - generic
  - heading "Draft session ready" [level=1, ref=e1]
  - StaticText "X-Draft-Route: atlas-7"

stderr: 
duration_seconds: 0.18
command: agent-browser --session review snapshot -c
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 102
stderr_chars: 0
stdout_bytes: 102
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 102
inline_stderr_chars: 0
estimated_inline_tokens: 26
requested_timeout_seconds: 60
effective_timeout_seconds: 60
iframes_auto_inlined: True
browser_backend: obscura
csp_enforced: False
native_browser_downloads: False
warnings: Obscura does NOT enforce CSP. Script execution is not proof of a Chromium CSP bypass. Native browser downloads are unsupported. The browser has NO SSRF boundary on host networking: it can reach host-local, LAN, and cloud-metadata (169.254.169.254) services, so only browse authorized targets.
```

### 9. network_curl
The cookie alone may be insufficient. I will retain that negative control before sending the discovered header.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/api/draft
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.18
command: curl -s -X GET --proto =http,https -i -L -b *** --max-time 5 -o /opt/workspace/artifacts/draft-no-header.json http://172.30.96.10:8000/api/draft
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

### 10. workspace_read_file
The rejection names the missing prerequisite; I will not count this branch as a solved challenge.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/draft-no-header.json
encoding: text
bytes: 201
total_bytes: 201
offset: 0
truncated: False
next_offset: None
content: HTTP/1.0 400 Bad Request
Server: AtlasLab/1.0 
Date: Mon, 26 Oct 2026 23:23:52 GMT
Content-Type: application/json
Content-Length: 33
X-Hercules-Lab: disposable

{"error": "route header missing"}
```

### 11. network_curl
A separate candidate is available. I will check its digest before accepting the first flag-like string.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/ctf/decoy
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.21
command: curl -s -X GET --proto =http,https -i -L --max-time 5 -o /opt/workspace/artifacts/decoy.json http://172.30.96.10:8000/ctf/decoy
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

### 12. shell_exec
The decoy's digest does not match. I will keep it as a rejected candidate.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: decoy checksum mismatch; rejected

stderr: 
duration_seconds: 0.3
command: bash /opt/workspace/tmp/shell_24a9828f471f4bab965e305efa83b0d2.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 34
stderr_chars: 0
stdout_bytes: 34
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 34
inline_stderr_chars: 0
estimated_inline_tokens: 9
requested_timeout_seconds: 45
effective_timeout_seconds: 45
```

### 13. network_curl
Both prerequisites are now observed. I will send the scoped request and save the actual response.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.96.10:8000/api/draft
redirects_followed: True
exit_code: 0
stdout: 
stderr: 
duration_seconds: 1.45
command: curl -s -X GET --proto =http,https -i -L -H '***' -b *** --max-time 5 -o /opt/workspace/artifacts/draft-flag.txt http://172.30.96.10:8000/api/draft
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

### 14. shell_exec
I will verify the returned flag against its digest. The report will document the rejected request and the two required state elements.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: {"flag": "HERCULES{state_and_requests_tell_the_story}", "checksum_match": true, "sha256": "1599e7f57f275f7e8ec73c7da7defc6109710466e158b4ef5bea0bdb7ffe9f4d"}

stderr: 
duration_seconds: 0.21
command: bash /opt/workspace/tmp/shell_a16c74a014d345a2ac530fd2c0bf7804.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 158
stderr_chars: 0
stdout_bytes: 158
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 158
inline_stderr_chars: 0
estimated_inline_tokens: 40
requested_timeout_seconds: 45
effective_timeout_seconds: 45
```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
