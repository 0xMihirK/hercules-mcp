# Web CTF

Real Hercules tools in a disposable local lab. Model decisions and this report are scripted.

## Verified observations

### 3. network_curl
I will inspect declared routes before guessing endpoints.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.80.10:8000/robots.txt
redirects_followed: False
redirect_note: Redirect following is disabled while target scopes are configured.
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.19
command: curl -s -X GET --proto =http,https -i --max-time 5 -o /opt/workspace/artifacts/robots.txt http://172.30.80.10:8000/robots.txt
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
Date: Wed, 07 Oct 2026 09:14:32 GMT
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
url: http://172.30.80.10:8000/api/draft
redirects_followed: False
redirect_note: Redirect following is disabled while target scopes are configured.
exit_code: 0
stdout: 
stderr: 
duration_seconds: 1.48
command: curl -s -X GET --proto =http,https -i --max-time 5 -o /opt/workspace/artifacts/draft-denied.txt http://172.30.80.10:8000/api/draft
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
url: http://172.30.80.10:8000/ctf/bootstrap
session: review
stealth: cloak stealth Chromium
proxy_enabled: False
proxy_host: 
timezone: 
locale: 
session_relaunched: False
next_step: Call browser_snapshot to see the page and obtain @refs.
exit_code: 0
stderr: 
duration_seconds: 0.64
command: agent-browser --json --session review open http://172.30.80.10:8000/ctf/bootstrap
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 353
stderr_chars: 0
stdout_bytes: 353
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 89
browser_result: success: True
data: lifecycle: effectiveLaunch: browserLaunched: True
engine: chrome
launchHash: 14020672945813849277
launched: False
relaunchedBrowser: False
restartedBackground: False
restoreStatus: not_configured
reused: True
saveStatus: not_attempted
title: 
url: http://172.30.80.10:8000/ctf/bootstrap
error: None
structured_output: True
stdout_replaced_by: browser_result
```

### 8. browser_snapshot
The page reveals a route-header requirement. I will combine it with the disposable session cookie instead of putting the value in the URL.

Actual response excerpt:
```text
tool: browser_snapshot
session: review
exit_code: 0
stdout: - heading "Draft session ready" [level=1, ref=e1]
- code
  - StaticText "X-Draft-Route: atlas-7"

stderr: 
duration_seconds: 0.12
command: agent-browser --session review snapshot -c
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 97
stderr_chars: 0
stdout_bytes: 97
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 97
inline_stderr_chars: 0
estimated_inline_tokens: 25
iframes_auto_inlined: True
```

### 9. network_curl
Both prerequisites are now observed. I will send the scoped request and save the actual response.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.80.10:8000/api/draft
redirects_followed: False
redirect_note: Redirect following is disabled while target scopes are configured.
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.11
command: curl -s -X GET --proto =http,https -i -H '***' -b *** --max-time 5 -o /opt/workspace/artifacts/draft-flag.txt http://172.30.80.10:8000/api/draft
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

### 10. shell_exec
I will verify the returned flag against its digest. The report will document the rejected request and the two required state elements.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: {"flag": "HERCULES{state_and_requests_tell_the_story}", "checksum_match": true, "sha256": "1599e7f57f275f7e8ec73c7da7defc6109710466e158b4ef5bea0bdb7ffe9f4d"}

stderr: 
duration_seconds: 0.17
command: bash /opt/workspace/tmp/shell_929c9e75fcf84662b95ca62d745b26b6.sh
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
```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
