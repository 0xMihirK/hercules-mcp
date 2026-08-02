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
proxy, locale, timezone, allowed domains, or container generation changes,
Hercules relaunches the affected session. The pinned controller does not expose
deterministic fingerprint selection; a non-empty `fingerprint` is rejected
rather than reported as applied.

When a proxy is active, non-proxied WebRTC UDP is blocked by default. Public egress verification must be user-initiated against an authorized IP-check page.

Use `browser_session` to list, inspect, close, or close all sessions. A live stream works when `BROWSER_STREAM_PORT` was configured before container startup. Hercules discovers the selected session's actual loopback WebSocket, replaces the generation-bound relay when the session changes, and exposes only the configured host-loopback port.

## Escape hatch and recovery

Call `browser_skill(name="core", full=true)` before `browser_cmd` when the structured browser surface is insufficient. Treat `browser_cmd` arguments as raw trusted-administrator input.

After container replacement or `system_start_new_session`, open the page again and rebuild browser state from workspace evidence. Do not assume old refs, daemons, cookies, or tabs survived.
