# Hercules Tool Routing

## Contents

- [Routing rules](#routing-rules)
- [Core and workspace](#core-and-workspace)
- [Reconnaissance](#reconnaissance)
- [Network and Nmap](#network-and-nmap)
- [Web assessment](#web-assessment)
- [Exploitation](#exploitation)
- [Password and CTF](#password-and-ctf)
- [Browser](#browser)
- [Parameter repair](#parameter-repair)

## Routing rules

Use the most specific structured tool that fits. Move from passive discovery to active validation, then to exploitation only with explicit authorization. The full surface is 45 tools with Metasploit and 40 without it; operator opt-outs can make fewer tools available.

Inspect the tools the client actually exposes before planning. If an optional
tool is absent, prefer another structured capability. Do not assume an omitted
capability's binary exists. Use `shell_exec` only
when the underlying binary is available, the operation remains authorized, and
the loss of structured target/output guarantees is explicit.

## Parameter repair

Read [parameter-reference.md](parameter-reference.md) before retrying an
invalid call, using a consolidated selector, or relying on an optional
parameter. It lists every live public parameter, conditional requirement, and
administrator escape hatch. Do not guess parameter names: compatibility
middleware may drop unknown fields.

## Core and workspace

| Need | Tool | Guidance |
| --- | --- | --- |
| Run a bounded command not covered elsewhere | `shell_exec` | Administrator escape hatch; prefer a structured tool and inspect timeout/artifact fields. |
| Start a long command | `shell_exec_background` | Supply a unique job ID, then poll instead of blocking. |
| Poll or tail a job | `shell_check_job` | Increase `tail_lines` only when necessary. |
| Stop a background job | `shell_kill_job` | Confirm the returned state. |
| Replace the container generation | `system_start_new_session` | Workspace persists; container-local state does not. |
| See Hercules sessions | `system_list_sessions` | Distinct from browser and Metasploit sessions. |
| Deliberately stop the container | `system_stop_container` | Terminal until a new system session is started. |
| Choose listener/reachable addresses | `system_network_info` | Use in the current MCP session before payload/listener configuration. Concurrent IDE clients can have different effective ports. |
| Read text or binary evidence | `workspace_read_file` | Choose `text` or `base64` encoding; page large files with `offset` and `max_bytes`. |
| Write text or binary input | `workspace_write_file` | Use exactly one of text `content` or binary-safe `content_base64`. |

Read `workspace-and-evidence.md` before pruning, migrating, paging large
evidence, or recovering a stale background job.

## Reconnaissance

| Need | Tool | Selectors or progression |
| --- | --- | --- |
| Registration and ownership data | `recon_whois` | Passive starting point for an authorized domain/IP. |
| Subdomains or ASN footprint | `recon_amass` | Start passive; enable `active`/`brute` only when allowed. |
| One DNS query or bulk resolution | `recon_dns` | `dig` for precise records/AXFR; `dnsx` for multiple names. |

## Network and Nmap

| Need | Tool | Selectors or progression |
| --- | --- | --- |
| Port/service scan | `nmap_scan` | `quick` → `port`/`aggressive`; `script` for installed NSE; `custom` only for trusted raw arguments. |
| Author missing NSE logic | `nmap_write_nse_script` | Read `nmap-nse.md`; write a complete, scoped Lua script. |
| Run authored NSE | `nmap_run_nse_script` | Run only the named custom script and pass narrow script args. |
| Deterministic HTTP request | `network_curl` | Prefer over browser when DOM or session interaction is unnecessary. |
| Connect, listen, or interact with a socket | `ncat` | Actions: `connect`, `listen`, `interact`; background listeners require follow-up. |
| Packet/firewall behavior | `network_hping3` | Intrusive raw-packet testing; use narrow counts and ports. |

Choose installed NSE first: use `nmap_scan(mode="script", scripts="...")` when a shipped script or category expresses the check. Author custom NSE only for protocol logic, parsing, or evidence that existing scripts cannot provide.

For complex custom authoring, read `resource://agent_skills/nse` before writing.
Use `extra_args` and `raw_args` only as trusted administrator input; they are not
substitutes for structured target, port, script, and mode fields.

## Web assessment

| Need | Tool | Selectors or progression |
| --- | --- | --- |
| Live HTTP/metadata | `web_scan` | `httpx` for reachability; `whatweb` for technology. |
| WAF/CMS/parameters/server checks | `web_scan` | `wafw00f`, `wpscan`, `arjun`, or `nikto` as specifically justified. |
| Content discovery | `fuzz_dirs` | `ffuf` for flexible matching; `gobuster` for simple directory discovery. |
| XSS or command injection | `web_vuln_scan` | `dalfox` for XSS; `commix` for command injection. |
| Known-template vulnerability checks | `nuclei_run` | Prefer tags/severity or installed template paths; keep rate limits scoped. |
| Author missing Nuclei detection | `nuclei_write_template` | Read `nuclei.md`, use strong evidence, validate, then run explicitly. |
| SQL injection workflow | `sqlmap_run` | Actions: `scan_basic`, `scan_custom`, `enumerate`, `dump`, `os_cmd`. For `enumerate`, choose `dbs`, `tables`, `columns`, `users`, `privileges`, or `passwords`. |

Do not substitute a browser for broad scanning. Use browser tools to reproduce one flow, inspect rendered state, or collect visual evidence after discovery.

For complex custom templates, read `resource://agent_skills/nuclei`. Prefer
`severity`, `tags`, `templates`, and `rate_limit` over raw `extra_args`. Use
`include_raw` only for exact request/response evidence or parser debugging.

## Exploitation

| Need | Tool | Selectors or progression |
| --- | --- | --- |
| Search or retrieve Exploit-DB material | `searchsploit` | `search` before `get`; review retrieved code before use. |
| Find a Metasploit module | `metasploit_search` | Match the observed product/version and review module requirements. |
| Run a module | `metasploit_run_module` | Choose module type `exploit`, `auxiliary`, or `post`; supply validated options and prefer check/safe behavior. |
| Sessions and jobs | `metasploit_manage` | `list_sessions`, `interact_session`, `close_session`, `list_jobs`, `stop_job`. |
| Produce a payload file | `metasploit_generate_payload` | Returns a workspace path, size, and checksum; do not expect binary stdout. |
| Start a reverse listener | `metasploit_start_listener` | Derive reachable LHOST/LPORT with `system_network_info`. |

Read `exploitation-and-sessions.md` before module execution, payload generation, or listener work.
Read `post-exploitation-resources.md` after a session proves local execution
and privilege-escalation enumeration is authorized.

## Password and CTF

| Need | Tool | Guidance |
| --- | --- | --- |
| Authorized online credential testing | `bruteforce_hydra` | Confirm lockout/rate limits and use the smallest credential set. |
| Offline hash recovery | `crack_john` | Prefer a known format and bounded wordlist/rules. |
| Firmware/archive inspection | `ctf_binwalk` | Extraction stays in the workspace. |
| Steganography inspection/extraction | `ctf_steghide` | Actions: `info`, then `extract`; passphrases are sensitive. |

## Browser

| Need | Tool | Guidance |
| --- | --- | --- |
| Start/navigate with a launch profile | `browser_open` | Per-call proxy overrides configured proxy; profile changes relaunch the session. |
| Obtain stable interactive references | `browser_snapshot` | Use compact first; request detail/iframes only when needed. |
| Act on a page | `browser_act` | Actions: `click`, `fill`, `type`, `press`, `hover`, `select`, `check`, `uncheck`. Target by `ref`, `css`, `role`, `text`, or `label`; prefer refs. |
| Read DOM/page values | `browser_read` | Read `text`, `html`, `value`, `url`, or `title`; target by `ref`, `css`, `role`, `text`, or `label`. |
| Capture visible evidence | `browser_screenshot` | Returns native image content; use `annotate` for reference overlays. |
| Evaluate page JavaScript | `browser_eval` | Use for targeted state inspection, not arbitrary browsing logic. |
| Synchronize with the page | `browser_wait` | Conditions: `selector`, `text`, `url`, `load`, or bounded milliseconds with `ms`. |
| List/close/stream sessions | `browser_session` | Actions: `current`, `list`, `close`, `close_all`, `stream`. Stream requires a preconfigured loopback port. |
| Load controller documentation | `browser_skill` | Read before using unfamiliar agent-browser commands. |
| Run raw controller commands | `browser_cmd` | Administrator escape hatch; call `browser_skill` first. |
