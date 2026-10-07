# Browser workflow review

Real Hercules tools in a disposable local lab. Model decisions and this report are scripted.

## Verified observations

### 3. browser_skill
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

### 4. browser_open
I will check the live local page in the native browser backend rather than infer behavior from headers.

Actual response excerpt:
```text
tool: browser_open
url: http://172.30.82.10:8000/login
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
duration_seconds: 1.77
command: agent-browser --json --session review open http://172.30.82.10:8000/login
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 363
stderr_chars: 0
stdout_bytes: 365
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 91
browser_result: success: True
data: lifecycle: effectiveLaunch: browserLaunched: True
engine: chrome
launchHash: 4021734320023416421
launched: False
relaunchedBrowser: False
restartedBackground: False
restoreStatus: not_configured
reused: True
saveStatus: not_attempted
title: Atlas lab — sign in
url: http://172.30.82.10:8000/login
error: None
structured_output: True
stdout_replaced_by: browser_result
```

### 5. browser_snapshot
The page has loaded. I will inspect the current accessibility tree before choosing form controls.

Actual response excerpt:
```text
tool: browser_snapshot
session: review
exit_code: 0
stdout: - heading "Atlas operations" [level=1, ref=e1]
- textbox "Email" [required, ref=e2]
- textbox "Password" [required, ref=e3]
- button "Sign in" [ref=e4]

stderr: 
duration_seconds: 0.23
command: agent-browser --session review snapshot -i -c
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 152
stderr_chars: 0
stdout_bytes: 152
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 152
inline_stderr_chars: 0
estimated_inline_tokens: 38
iframes_auto_inlined: True
```

### 6. browser_act
The email control has a label in the fresh snapshot. I will fill the disposable account address.

Actual response excerpt:
```text
tool: browser_act
session: review
exit_code: 0
stderr: 
duration_seconds: 0.27
command: agent-browser --json --session review find label Email fill ***
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 341
stderr_chars: 0
stdout_bytes: 341
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 86
browser_result: success: True
data: filled: [data-agent-browser-located='true']
lifecycle: effectiveLaunch: browserLaunched: True
engine: chrome
launchHash: 4021734320023416421
launched: False
relaunchedBrowser: False
restartedBackground: False
restoreStatus: not_configured
reused: True
saveStatus: not_attempted
error: None
structured_output: True
stdout_replaced_by: browser_result
```

### 7. browser_act
I will fill the fixture-only password; no personal credentials are used.

Actual response excerpt:
```text
tool: browser_act
session: review
exit_code: 0
stderr: 
duration_seconds: 0.23
command: agent-browser --json --session review find label Password fill ***
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 341
stderr_chars: 0
stdout_bytes: 341
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 86
browser_result: success: True
data: filled: [data-agent-browser-located='true']
lifecycle: effectiveLaunch: browserLaunched: True
engine: chrome
launchHash: 4021734320023416421
launched: False
relaunchedBrowser: False
restartedBackground: False
restoreStatus: not_configured
reused: True
saveStatus: not_attempted
error: None
structured_output: True
stdout_replaced_by: browser_result
```

### 8. browser_act
Both controls are filled. I will submit the actual local form and inspect the resulting page.

Actual response excerpt:
```text
tool: browser_act
session: review
exit_code: 0
stderr: 
duration_seconds: 0.31
command: agent-browser --json --session review find role button click --name 'Sign in'
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 310
stderr_chars: 0
stdout_bytes: 310
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 78
browser_result: success: True
data: clicked: @e5
lifecycle: effectiveLaunch: browserLaunched: True
engine: chrome
launchHash: 4021734320023416421
launched: False
relaunchedBrowser: False
restartedBackground: False
restoreStatus: not_configured
reused: True
saveStatus: not_attempted
error: None
structured_output: True
stdout_replaced_by: browser_result
```

### 9. browser_snapshot
The dashboard confirms successful authentication. I will retain evidence rather than infer success from the click.

Actual response excerpt:
```text
tool: browser_snapshot
session: review
exit_code: 0
stdout: - heading "Dashboard" [level=1, ref=e1]

stderr: 
duration_seconds: 0.2
command: agent-browser --session review snapshot -c
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 40
stderr_chars: 0
stdout_bytes: 40
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 40
inline_stderr_chars: 0
estimated_inline_tokens: 10
iframes_auto_inlined: True
```

### 10. network_curl
I will independently confirm that an incorrect fixture password is rejected; the successful browser flow alone does not test this branch.

Actual response excerpt:
```text
tool: network_curl
url: http://172.30.82.10:8000/login
redirects_followed: False
redirect_note: Redirect following is disabled while target scopes are configured.
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.3
command: curl -s -X POST --proto =http,https -i -d 'email=reviewer%40lab.test&password=*** --max-time 5 -o /opt/workspace/artifacts/login-rejected.txt http://172.30.82.10:8000/login
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

### 11. browser_screenshot
I will save the verified final page. The report will distinguish tested authentication behavior from untested security properties.

Actual response excerpt:
```text
tool: browser_screenshot
session: review
path: /opt/workspace/browser/review/artifacts/dashboard.png
mime_type: image/png
annotated: False
exit_code: 0
stdout: ✓ Screenshot saved to /opt/workspace/browser/review/artifacts/dashboard.png

stderr: 
duration_seconds: 0.42
command: agent-browser --session review screenshot /opt/workspace/browser/review/artifacts/dashboard.png
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 76
stderr_chars: 0
stdout_bytes: 78
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 76
inline_stderr_chars: 0
estimated_inline_tokens: 19
bytes: 10179
width: 1280
height: 599
```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
