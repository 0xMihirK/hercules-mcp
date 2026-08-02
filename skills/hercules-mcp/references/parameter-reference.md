# Hercules Parameter Reference

Use this reference to repair a tool call or choose a selector. Parameters shown
in **bold** are always required. A parameter not listed for a tool is not part
of its public schema and may be dropped by compatibility middleware.

Consolidated selector fields include `tool`, `module_type`, `encoding`,
`target_type`, `what`, and `condition`; use only the values listed below.

## Core, workspace, and system

| Tool | Parameters and conditions |
| --- | --- |
| `shell_exec` | **`command`**; `timeout`; `raw` disables semantic compaction but not safety sanitation or output bounds. Administrator escape hatch. |
| `shell_exec_background` | **`command`**, **`job_id`**. Use a unique non-secret `job_id`. Administrator escape hatch. |
| `shell_check_job` | **`job_id`**; `tail_lines`. |
| `shell_kill_job` | **`job_id`**. |
| `workspace_read_file` | **`path`**; `encoding=text|base64`; `offset`; `max_bytes`. Continue from `next_offset` when `truncated=true`. |
| `workspace_write_file` | **`path`**; exactly one of `content` or `content_base64`; `mode`. |
| `system_start_new_session` | No parameters. |
| `system_list_sessions` | No parameters. |
| `system_stop_container` | No parameters. |
| `system_network_info` | No parameters. |

## Reconnaissance, network, and web

| Tool | Parameters and selectors |
| --- | --- |
| `recon_whois` | **`domain`**; raw `extra_args`; `include_raw`. |
| `recon_amass` | **`domain`**; `active`; `brute`; raw `extra_args`. |
| `recon_dns` | **`tool=dig|dnsx`**; `target`; `domains`; `record_type`; `server`; `short`; `axfr`; `silent`; raw `extra_args`. `dig` needs `target`; `dnsx` needs `domains` or `target`. |
| `nmap_scan` | **`mode=quick|aggressive|port|script|custom`**; `target`; `ports`; `scripts`; raw `raw_args`; raw `extra_args`. `target` is required except for `custom`; `port` also needs `ports`; `script` also needs `scripts`; `custom` needs `raw_args`. |
| `nmap_write_nse_script` | **`name`**, **`content`**. Read `resource://agent_skills/nse` before writing missing logic. |
| `nmap_run_nse_script` | **`target`**, **`script_name`**; raw `extra_args`. |
| `network_curl` | **`url`**; `method`; `headers`; `data`; `cookie`; `include_headers`; `follow_redirects`; raw `extra_args`. |
| `ncat` | **`action=connect|listen|interact`**; `target`; `port`; `listen_port`; `job_id`; `command`; `tail_lines`; `execute`; `udp`; raw `extra_args`; `background`. `connect` needs `target` and `port`; listener/interact fields depend on the selected action. |
| `network_hping3` | **`target`**; `count`; `syn`; `port`; raw `extra_args`. |
| `web_scan` | **`tool=httpx|whatweb|wafw00f|wpscan|arjun|nikto`**; `target`; `urls`; `title`; `tech_detect`; `status_code`; `threads`; `agg_level`; `tuning`; `enumerate`; `api_token`; `method`; raw `extra_args`; `include_raw`. `httpx` can use `urls`; other selectors require the target form documented by the usage error. |
| `fuzz_dirs` | **`target_url`**; `wordlist`; `tool=ffuf|gobuster`; `extensions`; `threads`; raw `extra_args`; `include_raw`. |
| `web_vuln_scan` | **`tool=dalfox|commix`**, **`target_url`**; `data`; `cookie`; `threads`; raw `extra_args`; `include_raw`. |
| `sqlmap_run` | **`action=scan_basic|scan_custom|enumerate|dump|os_cmd`**, **`target_url`**; `method`; `data`; `cookies`; `level`; `risk`; `techniques`; `tamper`; `proxy`; `forms`; raw `extra_args`; `enum_what=dbs|tables|columns|users|privileges|passwords`; `db`; `table`; `command`; `include_raw`. `enumerate` needs `enum_what`; `dump` uses `db`/`table`; `os_cmd` needs `command`. |
| `nuclei_run` | **`targets`**; `templates`; `severity`; `tags`; `rate_limit`; raw `extra_args`; `include_raw`. Prefer installed templates/tags. |
| `nuclei_write_template` | **`path`**, **`content`**. Read `resource://agent_skills/nuclei` before authoring missing detection logic. |

## Exploitation, password, and CTF

| Tool | Parameters and selectors |
| --- | --- |
| `searchsploit` | **`action=search|get`**, **`query_or_id`**; `include_raw`. |
| `metasploit_search` | **`query`**. Optional capability: verify it is registered. |
| `metasploit_run_module` | **`module_type=exploit|auxiliary|post`**, **`module_name`**, **`options`**; `payload`; `payload_options`. Option keys/values are passed to the chosen module and must match its metadata. |
| `metasploit_manage` | **`action=list_sessions|interact_session|close_session|list_jobs|stop_job`**; `session_id`; `command`; `timeout`; `job_id`. Interaction/close needs `session_id`; interaction also needs `command`; stop needs `job_id`. |
| `metasploit_generate_payload` | **`payload`**, **`options`**; `format`. Returns a file artifact, not binary stdout. |
| `metasploit_start_listener` | **`payload_type`**, **`lhost`**, **`lport`**; `options`. |
| `bruteforce_hydra` | **`target`**, **`service`**, **`usernames`**, **`passwords`**; `port`; `options`. Credential and option surfaces are sensitive/raw administrator input. |
| `crack_john` | **`hashes`**; `format`; `wordlist`; raw `extra_args`. |
| `ctf_binwalk` | **`filepath`**; `extract`; raw `extra_args`. |
| `ctf_steghide` | **`action=info|extract`**, **`filepath`**; `passphrase`; raw `extra_args`. |

## Browser

| Tool | Parameters and conditions |
| --- | --- |
| `browser_open` | **`url`**; `session`; compatibility `fingerprint` (non-empty is rejected); `timezone`; `locale`; sensitive `proxy`. |
| `browser_snapshot` | `session`; compatibility `inline_iframes` (iframes are automatic); `compact`; `detailed`; `interactive`; `include_urls`; `depth` (`0` is unlimited); `selector`. |
| `browser_act` | **`action=click|fill|type|press|hover|select|check|uncheck`**; `target`; sensitive `value`; `target_type=ref|css|role|text|label`; accessible `name`; `exact`; `session`. `press` needs `value`; `fill`/`type`/`select` need `value`; semantic targets support only click/fill/check/hover. |
| `browser_read` | **`what=text|html|value|url|title`**; `target`; `target_type=ref|css|role|text|label`; accessible `name`; `exact`; `session`. URL/title need no target; semantic targets support only text. |
| `browser_screenshot` | `path`; `session`; `full`; `return_base64`; `annotate`. Native MCP image content is primary. |
| `browser_eval` | **`js`**; `session`. Administrator-level page script execution. |
| `browser_wait` | **`condition=selector|ms|text|url|load`**, `value`; `session`. Every condition requires `value`; milliseconds are bounded. |
| `browser_session` | **`action=current|list|close|close_all|stream`**; `session`; `stream_port`. `close` needs `session`; `stream` needs a configured/allowed loopback port. |
| `browser_skill` | `name`; `full`. Load this before unfamiliar raw controller syntax. |
| `browser_cmd` | **`args`**; `session`; `timeout`; `json`. Administrator escape hatch; read `browser_skill` first. |

## Raw-surface rule

`command`, browser `args`, JavaScript `js`, generic `options`, `raw_args`, and
`extra_args` can express operations outside structured target guarantees. Keep
them narrow, authorized, and non-secret in narration. Prefer named structured
parameters because Hercules quotes and validates those fields.
