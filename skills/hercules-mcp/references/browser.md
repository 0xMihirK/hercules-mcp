# Browser Workflow

## Contents

- [Choose browser versus HTTP tools](#choose-browser-versus-http-tools)
- [Reliable interaction loop](#reliable-interaction-loop)
- [Screenshots and evidence](#screenshots-and-evidence)
- [Sessions and launch profiles](#sessions-and-launch-profiles)
- [Escape hatch and recovery](#escape-hatch-and-recovery)

## Choose browser versus HTTP tools

Use `network_curl`, `web_scan`, or a focused scanner when a direct request provides the needed evidence. Use the browser when the task requires rendered JavaScript, cookies or login state, DOM interaction, accessibility references, client-side navigation, or a visual record.

The browser improves fingerprint and proxy configuration consistency. It does not guarantee CAPTCHA or bot-detection avoidance. Do not claim that Docker supplies residential egress.

The sole backend is pinned **Obscura 0.2.5**, driven by agent-browser **0.39.1**.
**CSP is not enforced**: executing a script here does not demonstrate a CSP
bypass in Chromium. Every response advertises this. Rendering, iframe/AX
behavior, storage-state support, media, and service workers are not Chromium
parity; an unsupported feature is not evidence that the target is broken.
Tracker blocking is disabled so a target's requests are not silently filtered.

The pinned controller's domain filter leaks image and redirected requests, and there
is **no SSRF gateway/firewall**. On host networking the browser reaches any
destination it is pointed at — including host-local, the LAN, and cloud-metadata
(`169.254.169.254`). Only browse explicitly authorized targets. Root shell commands remain
administrator escape hatches, not confined browser operations.

## Reliable interaction loop

1. Call `browser_open` with the authorized URL and a stable session name.
2. Call `browser_wait(condition="load", value="...")` or wait for a specific selector/text when the page is dynamic.
3. Call `browser_snapshot` and select a current `@ref`. Use
   `interactive=true` for the smallest action-oriented tree,
   `include_urls=true` when link destinations matter, `depth` to bound a deep
   tree, and `selector` to scope a region. Iframes are auto-inlined one level.
4. Call `browser_act` using the ref. Prefer `fill` for replacing input and `type` for incremental typing.
5. Resnapshot after navigation, modal changes, or substantial DOM replacement.
6. Call `browser_read` for precise text/value/URL/title evidence.
7. Call `browser_screenshot` when visual evidence matters.

Prefer refs over CSS. Use role, text, or label targeting for semantic
click/fill/check/hover or text reads when no stable ref is available. Role
targeting accepts an accessible `name`. Semantic HTML/value reads and semantic
type/select/uncheck actions are not supported by the controller; obtain a ref
or use CSS. Keep separate authentication contexts in separate sessions.

## Screenshots and evidence

`browser_screenshot` returns validated PNG bytes as native MCP image content plus structured path, MIME type, dimensions, byte count, command status, and optional compatibility base64.

- Use `annotate=true` when the image should show interactive reference overlays.
- Use `full=true` only when the whole document is needed.
- Leave `return_base64=false` unless a legacy client explicitly requires metadata base64.
- Treat `image_read_error` as failure even when the screenshot command exited successfully.
- Use the workspace path to retain or reread the captured evidence.

## Sessions and launch profiles

Proxy precedence is `browser_open(proxy=...)`, then `BROWSER_PROXY_URL`, then
direct host egress. Responses expose only sanitized proxy state/host. When
proxy, timezone, allowed domains, or container generation changes,
Hercules relaunches the affected session. The pinned controller does not expose
deterministic fingerprint selection; a non-empty `fingerprint` is rejected
rather than reported as applied.
Explicit locale is also rejected. The adapter rejects persistent profiles,
storage-state launch flags, custom CAs, Chrome arguments, extensions, and proxy
bypass (including inherited `NO_PROXY`). Do not remove meaningful operator
settings or disable TLS to work around an error. There is no automatic fallback.

Obscura has no WebRTC media stack; Chromium's UDP policy flag is not passed.
Public egress verification must be user-initiated against an authorized IP-check page.

Call `system_network_info` before assuming where a local service lives. The runtime
uses host networking, so `localhost` and `127.0.0.1` are the host itself. The browser
has no SSRF boundary and can reach host-local, the LAN, and cloud-metadata services —
only open explicitly authorized targets; do not rewrite localhost implicitly.
Upstream HTTP(S) CONNECT and locally
resolved SOCKS5 are supported; unverifiable remote-DNS modes are rejected, never
silently changed.

Use `browser_session` to list, inspect, close, or close all sessions. A live stream works when `BROWSER_STREAM_PORT` was configured before container startup. Hercules discovers the selected session's actual loopback WebSocket, replaces the generation-bound relay when the session changes, and exposes only the configured host-loopback port.

## Escape hatch and recovery

`browser_eval` takes `js`, not `script`, and evaluates a JavaScript expression.
For example, `js="document.title"` or
`js="(async () => { const value = await Promise.resolve(document.title); return value; })()"`.
Use an IIFE for statements, `return`, or `await`; top-level `return`/`await`
may be rejected. Do not repeatedly retry the same invalid syntax.

Call `browser_skill(name="core", full=true)` before `browser_cmd` when the structured browser surface is insufficient. Treat `browser_cmd` arguments as raw trusted-administrator input.
The packaged upstream command reference is version-matched, but Chrome-only
features described there are not promises of Obscura support. Use browser
responses and the limitations above as the effective capability contract.

### Downloads

Native browser download events/paths are unsupported; a CDP acknowledgement
does not prove bytes were saved. For a direct authorized URL, use `network_curl`
with its file-output option or `shell_exec` to save the complete response:

```sh
curl --fail --location --output /opt/workspace/challenge/handout.bin https://authorized.example/handout.bin
test -s /opt/workspace/challenge/handout.bin && sha256sum /opt/workspace/challenge/handout.bin
```

Browser redirects are not bounded — there is no gateway or private-IP deny on host
networking. `shell_exec` is privileged and equally unconfined. For authenticated
files, deliberately supply the required private headers/cookies without printing
them; there is no automatic credential replay. Save POST/API response bytes
when applicable. Blob/generated downloads may not be reproducible: report
unsupported rather than inventing a file or success. Check expected size/type
as well as the checksum; an HTML login page is not the requested binary.

After container replacement or `system_start_new_session`, open the page again and rebuild browser state from workspace evidence. Do not assume old refs, daemons, cookies, or tabs survived.
