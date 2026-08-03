"""
Agent-facing MCP guidance and structured usage errors.

This module intentionally contains runtime metadata, not only contributor
documentation. FastMCP exposes these strings to clients so agents can choose
tools with less trial and error.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from hercules.core.security import redact_secrets

SERVER_INSTRUCTIONS = """
Hercules runs authorized security tools in a managed Kali container. Confirm
scope, start passive/light, verify evidence, and escalate only when authorized.
Prefer structured tools; shell_exec, browser_cmd, raw_args, and extra_args are
administrator escape hatches outside complete structured-target guarantees.

Use HTTP tools for direct requests and browser_open -> wait/snapshot ->
act/read -> screenshot for JavaScript, session state, interaction, or visual
evidence. Browser configuration cannot guarantee CAPTCHA/bot avoidance.

Prefer installed NSE/Nuclei content. For missing logic read
resource://agent_skills/nse or resource://agent_skills/nuclei before authoring.
After authorized local execution, select only the needed linpeas, winpeas,
powerup, gtfobins, or lolbas post-exploitation resource; enumeration does not
authorize escalation.

Interpret exit_code separately from findings. Check timed_out, terminated,
partial_output, output_filtered, output_complete, evidence_complete, parsed
results, and artifact paths. Use bounded workspace paging instead of repeating
a scan. Unknown parameters may be dropped; use only the live schema. Operators
may disable optional tools, including Metasploit.
""".strip()


def _clip_guidance(value: str, maximum: int) -> str:
    """Bound fixed MCP context while leaving full guidance in the skill."""
    text = " ".join(value.split())
    if len(text) <= maximum:
        return text
    clipped = text[: maximum + 1]
    boundary = max(clipped.rfind(". "), clipped.rfind("; "), clipped.rfind(", "))
    if boundary >= maximum // 2:
        clipped = clipped[: boundary + 1]
    else:
        clipped = clipped[:maximum].rstrip()
    return clipped.rstrip(" ,;") + "…"


def _desc(
    use_case: str,
    workflow_position: str,
    important_notes: str,
    examples: str,
) -> str:
    del workflow_position  # Detailed sequencing lives in the progressive skill.
    example = examples.splitlines()[0] if examples else ""
    return (
        f"Purpose: {_clip_guidance(use_case, 125)}\n"
        f"Constraints: {_clip_guidance(important_notes, 190)}\n"
        f"Example: {_clip_guidance(example, 105)}"
    )


TOOL_DESCRIPTIONS = {
    "nmap_scan": _desc(
        "Run Nmap using mode=quick|aggressive|port|script|custom for host discovery, service enumeration, NSE execution, or fully custom Nmap arguments.",
        "Recon and vulnerability verification before deeper web, exploit, or post-exploitation work.",
        "quick/aggressive/port/script require target. port requires ports. script requires scripts. extra_args is preserved for quick, aggressive, port, and script modes. custom requires raw_args and does not target-validate unless the operator encoded target validation elsewhere. XML output is parsed before compaction; raw XML may be preserved as an artifact. quick/port/script use light concurrency; aggressive and broad custom scans can run longer.",
        "nmap_scan(mode='quick', target='scanme.nmap.org')\nnmap_scan(mode='script', target='host', scripts='vuln', extra_args='-sV')",
    ),
    "nmap_write_nse_script": _desc(
        "Write a custom NSE script into the container and update the Nmap script database.",
        "Custom NSE authoring after reading resource://agent_skills/nse.",
        "Pass name without path separators; Hercules sanitizes it and writes /opt/workspace/nmap-scripts/<name>.nse. Use nmap_run_nse_script to execute that managed artifact. Include NSEDoc metadata and correct categories in content.",
        "nmap_write_nse_script(name='http-custom-check', content='description = [[...]]\\nauthor = ...')",
    ),
    "nmap_run_nse_script": _desc(
        "Run a previously written custom NSE script against a validated target.",
        "Custom reconnaissance, protocol testing, vulnerability verification, and exploit workflow checks.",
        "Requires target and script_name. extra_args can pass -p, -sV, --script-args, --script-trace, -d, or -v. XML output is parsed when possible, preserving script output fields.",
        "nmap_run_nse_script(target='host', script_name='http-custom-check', extra_args='-p80 --script-trace')",
    ),
    "web_scan": _desc(
        "Run one web fingerprinting scanner selected by tool=httpx|whatweb|wafw00f|nikto|wpscan|arjun.",
        "Web reconnaissance and application fingerprinting before vulnerability-specific checks.",
        "httpx accepts urls or target and supports threads. whatweb uses agg_level. nikto supports tuning. wpscan supports enumerate and api_token. arjun supports method and threads. include_raw=True returns more raw-like output for high-noise scanners. Targeted variants enforce target validation.",
        "web_scan(tool='httpx', urls='http://a,http://b', threads=20)\nweb_scan(tool='nikto', target='http://host', tuning='x', include_raw=False)",
    ),
    "web_vuln_scan": _desc(
        "Run web vulnerability scanners selected by tool=dalfox|commix.",
        "Focused web vulnerability verification after recon or parameter discovery.",
        "Requires target_url. Dalfox maps threads to --worker and supports cookie and extra_args. Commix supports data, cookie, threads when native support exists, and extra_args. include_raw=True keeps fuller scanner output while still bounded by artifacts/truncation.",
        "web_vuln_scan(tool='dalfox', target_url='http://host/?q=1', threads=8)\nweb_vuln_scan(tool='commix', target_url='http://host/cmd', data='x=1', cookie='sid=1')",
    ),
    "fuzz_dirs": _desc(
        "Discover web paths with gobuster or ffuf while preserving thread control.",
        "Content discovery after a live HTTP service is confirmed.",
        "Requires target_url. tool defaults to gobuster; ffuf is selected with tool='ffuf'. threads controls native fuzzer concurrency. Missing wordlists return repair guidance and example paths. include_raw=True disables compact defaults.",
        "fuzz_dirs(target_url='http://host', wordlist='/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt', threads=30)\nfuzz_dirs(target_url='http://host', tool='ffuf', extensions='php,txt')",
    ),
    "ncat": _desc(
        "Use ncat with action=connect|listen|interact for TCP/UDP connections and background listeners.",
        "Networking, reverse shell handling, callback listeners, and ad hoc protocol interaction.",
        "connect requires target and port and runs foreground. listen can run foreground or background; background=True creates a job_id and pipe. interact requires job_id and can send command then read tail_lines. Use udp=True for UDP. Listeners are heavy concurrency.",
        "ncat(action='listen', port=4444, job_id='listener1')\nncat(action='interact', job_id='listener1', command='id', tail_lines=100)",
    ),
    "network_curl": _desc(
        "Make HTTP requests with curl using methods, headers, cookies, data, redirects, and extra curl arguments.",
        "Manual web probing, proof collection, API testing, and exploit verification.",
        "The URL is target-validated. Output is mostly raw aside from terminal cleanup and truncation. Use headers as comma-separated Header: value strings. Prefer nuclei_run or web_scan for repeatable template/scanner workflows.",
        "network_curl(url='http://host/path', method='POST', data='a=1', cookie='sid=1')",
    ),
    "network_hping3": _desc(
        "Craft packets with hping3 for firewall, service, or packet-level testing.",
        "Network validation and low-level packet checks after target scope is confirmed.",
        "Requires target. count, syn, port, and extra_args map to hping3. Runs with light concurrency and target validation.",
        "network_hping3(target='host', count=3, syn=True, port=80)",
    ),
    "recon_dns": _desc(
        "Run DNS lookups with tool=dig|dnsx for single-record queries or bulk resolution.",
        "DNS reconnaissance before port scanning and web probing.",
        "dig uses target, record_type, server, short, axfr, and extra_args. dnsx uses domains or target and silent/extra_args. Use recon_amass for subdomain enumeration and recon_whois for registrar data.",
        "recon_dns(tool='dig', target='example.com', record_type='MX', short=True)\nrecon_dns(tool='dnsx', domains='a.example.com,b.example.com', extra_args='-a')",
    ),
    "recon_whois": _desc(
        "Collect WHOIS registration data for a domain.",
        "Passive recon and ownership/context gathering.",
        "Use include_raw=True if registry boilerplate or exact legal text is needed. Default output preserves registrar, dates, nameservers, statuses, DNSSEC, and contact fields while compacting terms-of-use noise.",
        "recon_whois(domain='example.com')",
    ),
    "recon_amass": _desc(
        "Enumerate subdomains with amass using passive, active, and brute-force modes.",
        "Subdomain reconnaissance after scope and target validation are established.",
        "Requires domain and validates it. active=False uses passive mode. brute=True enables brute force. This is heavy and can take up to 20 minutes.",
        "recon_amass(domain='example.com', active=False)\nrecon_amass(domain='example.com', active=True, brute=True)",
    ),
    "metasploit_search": _desc(
        "Search Metasploit exploit, auxiliary, and post modules by keyword, service name, or CVE.",
        "Exploit planning before metasploit_run_module or metasploit_start_listener.",
        "Returns available modules that may help with the query. Broaden the query if the list is empty. Metasploit must be enabled and RPC available.",
        "metasploit_search(query='vsftpd')\nmetasploit_search(query='CVE-2011-2523')",
    ),
    "metasploit_run_module": _desc(
        "Run a Metasploit exploit, auxiliary, or post module through the RPC API.",
        "Exploitation and post-exploitation automation after module selection.",
        "module_type is usually exploit, auxiliary, or post. options should contain module datastore options such as RHOSTS/RPORT/TARGETURI. payload and payload_options are used for exploits. Payload listener keys accidentally placed in options are auto-routed when possible.",
        "metasploit_run_module(module_type='exploit', module_name='unix/ftp/vsftpd_234_backdoor', options={'RHOSTS':'10.0.0.5'})",
    ),
    "metasploit_manage": _desc(
        "Manage Metasploit sessions and jobs with action=list_sessions|interact_session|close_session|list_jobs|stop_job.",
        "Session management after exploitation and listener/job cleanup.",
        "interact_session requires session_id and command. close_session requires session_id. stop_job requires job_id. Outputs include active sessions/jobs where available so agents can correct stale IDs.",
        "metasploit_manage(action='list_sessions')\nmetasploit_manage(action='interact_session', session_id=1, command='id')",
    ),
    "metasploit_generate_payload": _desc(
        "Generate a payload through Metasploit RPC or msfvenom fallback.",
        "Payload preparation for exploit chains, listeners, and manual delivery.",
        "Pass payload and options such as LHOST/LPORT. format controls output format. Successful RPC generation writes payload bytes into /opt/workspace/payloads/.",
        "metasploit_generate_payload(payload='linux/x86/meterpreter/reverse_tcp', options={'LHOST':'10.0.0.1','LPORT':4444}, format='elf')",
    ),
    "metasploit_start_listener": _desc(
        "Start exploit/multi/handler as a Metasploit background job.",
        "Reverse shell or Meterpreter callback handling before exploit delivery.",
        "Requires payload_type, lhost, and lport. lport must be 1-65535. Use system_network_info first to choose LHOST/LPORT on bridge-networked hosts. Manage jobs with metasploit_manage.",
        "metasploit_start_listener(payload_type='linux/x86/meterpreter/reverse_tcp', lhost='10.0.0.1', lport=4444)",
    ),
    "sqlmap_run": _desc(
        "Run sqlmap with action=scan_basic|scan_custom|enumerate|dump|os_cmd.",
        "SQL injection detection, enumeration, dumping, or OS command checks.",
        "Requires target_url and target validation. Always uses --batch and a workspace output directory. scan_custom supports method, data, cookies, level, risk, techniques, tamper, proxy, forms, and extra_args. include_raw=True preserves fuller logs.",
        "sqlmap_run(action='scan_basic', target_url='http://host/item?id=1')\nsqlmap_run(action='dump', target_url='http://host/item?id=1', db='app', table='users')",
    ),
    "searchsploit": _desc(
        "Search or mirror Exploit-DB entries with action=search|get.",
        "Exploit research before manual validation or Metasploit module selection.",
        "Search returns JSON when available and may degrade overly specific queries to broader terms. include_raw=True avoids result capping. get mirrors an exploit by ID and returns content when available.",
        "searchsploit(action='search', query_or_id='apache 2.4')\nsearchsploit(action='get', query_or_id='49757')",
    ),
    "bruteforce_hydra": _desc(
        "Run Hydra for online credential testing against a service.",
        "Credential attack workflows where authorized credentials testing is in scope.",
        "Requires target, service, usernames, and passwords. Prefix usernames/passwords with file: for wordlists. Target is validated. Output summary keeps credential findings.",
        "bruteforce_hydra(target='host', service='ftp', usernames='msfadmin', passwords='msfadmin')",
    ),
    "crack_john": _desc(
        "Run John the Ripper against supplied hashes using a wordlist.",
        "Offline hash cracking and CTF/password recovery workflows.",
        "Hashes are written to a temporary workspace file, cracked with john, shown with john --show, then the temp file is removed. Use format and extra_args when hash type needs explicit selection.",
        "crack_john(hashes='$y$j9T$...', format='crypt', wordlist='/usr/share/wordlists/rockyou.txt')",
    ),
    "nuclei_run": _desc(
        "Run Nuclei templates against one or more targets with JSONL output.",
        "Template-driven vulnerability verification and custom template execution.",
        "targets is comma-separated. templates can point to a workspace template from nuclei_write_template or installed template paths. severity, tags, rate_limit, and extra_args tune execution. include_raw=True keeps request/response-heavy JSON fields; default compact mode returns matches.",
        "nuclei_run(targets='http://host', templates='/opt/workspace/nuclei-templates/check.yaml', rate_limit=5)",
    ),
    "nuclei_write_template": _desc(
        "Write a custom Nuclei YAML template into /opt/workspace/nuclei-templates.",
        "Custom vulnerability checks after reading resource://agent_skills/nuclei.",
        "Path traversal is rejected. Use relative paths such as custom/check.yaml. Validate with nuclei -validate via shell_exec or run with nuclei_run using the returned path.",
        "nuclei_write_template(path='custom/basic-detect.yaml', content='id: basic-detect\\ninfo: ...')",
    ),
    "shell_exec": _desc(
        "Execute a non-interactive shell command inside the Kali container.",
        "Escape hatch for Linux commands, missing tools, package checks, custom validation, and artifact inspection.",
        "raw=True disables semantic compaction but retains safety bounds and artifacts. This is non-interactive; use shell_exec_background or ncat/listeners for long-running jobs.",
        "shell_exec(command='id && pwd')\nshell_exec(command='apt-get update && apt-get install -y jq', timeout=600)",
    ),
    "shell_exec_background": _desc(
        "Start a long-running shell command as a background job.",
        "Listeners, servers, long scans, and commands that need periodic output checks.",
        "Requires job_id. Use shell_check_job to read output and shell_kill_job to stop the process. Background jobs share the current container session.",
        "shell_exec_background(command='python3 -m http.server 8000', job_id='http8000')",
    ),
    "shell_check_job": _desc(
        "Read status and tail output from a background shell job.",
        "Monitoring background listeners, long scans, and helper services.",
        "Requires job_id. tail_lines controls how much recent output is returned. If output is too short, increase tail_lines or inspect artifacts with workspace_read_file/shell_exec.",
        "shell_check_job(job_id='http8000', tail_lines=100)",
    ),
    "shell_kill_job": _desc(
        "Stop a background shell job by job_id.",
        "Cleanup for listeners, servers, and stuck commands.",
        "Requires job_id. Use shell_check_job first if you need final output. The response says whether a process was killed.",
        "shell_kill_job(job_id='http8000')",
    ),
    "workspace_read_file": _desc(
        "Read a bounded file chunk inside the owned container workspace.",
        "Artifact review, custom script inspection, and result collection.",
        "Relative paths resolve under /opt/workspace. Paths outside it and symlink/reparse escapes are rejected. encoding='base64' reads binary data. For large files, continue with offset=next_offset and a bounded max_bytes until truncated=false.",
        "workspace_read_file(path='nuclei-templates/custom/check.yaml')\nworkspace_read_file(path='payload.exe', encoding='base64', offset=0, max_bytes=1048576)",
    ),
    "workspace_write_file": _desc(
        "Atomically write content to a file in the owned container workspace.",
        "Preparing payloads, helper scripts, target lists, and custom config files.",
        "Relative paths resolve under /opt/workspace; paths outside it and symlink/reparse escapes are rejected. Supply either content or content_base64, never both. mode defaults to 0644. For NSE and Nuclei authoring prefer the dedicated write tools.",
        "workspace_write_file(path='targets.txt', content='http://host\\n')\nworkspace_write_file(path='payload.bin', content_base64='AAE=', mode='0644')",
    ),
    "system_start_new_session": _desc(
        "Start a fresh Hercules container session with a clean mounted workspace.",
        "Session lifecycle management when switching targets or engagements.",
        "Creates a new workspace and stops the current container. Previous host workspace data is preserved. Metasploit RPC is reinitialized when enabled.",
        "system_start_new_session()",
    ),
    "system_list_sessions": _desc(
        "List Hercules session workspaces on the host.",
        "Workspace audit, cleanup planning, and confirming active session state.",
        "Returns active_session, total_sessions, and per-session metadata where available. Does not modify the container.",
        "system_list_sessions()",
    ),
    "system_stop_container": _desc(
        "Stop and remove the current Hercules container while preserving workspace files.",
        "End-of-engagement cleanup when no further tools need to run.",
        "After this tool succeeds, MCP tools that require the container cannot run until a new session is started. It stops background jobs and container-side processes.",
        "system_stop_container()",
    ),
    "system_network_info": _desc(
        "Inspect host/container networking and recommend an LHOST for callbacks.",
        "Exploit and listener setup before Metasploit or ncat reverse shell workflows.",
        "Call this in the current MCP session before choosing callback ports. It returns effective RPC, listener, and browser-stream ports; concurrent IDE clients may receive a collision-free range instead of the configured defaults.",
        "system_network_info()",
    ),
    "ctf_binwalk": _desc(
        "Analyze and optionally extract firmware, archives, and embedded files with binwalk.",
        "CTF, forensics, firmware review, and artifact unpacking.",
        "extract=True adds extraction flags and --run-as=root unless extra_args already specifies --run-as. Absolute paths extract from their containing directory to avoid duplicate paths.",
        "ctf_binwalk(filepath='/opt/workspace/sample.bin', extract=True)",
    ),
    "ctf_steghide": _desc(
        "Inspect or extract steghide payloads with action=info|extract.",
        "Steganography and CTF artifact workflows.",
        "Pass filepath and optional passphrase. Without a passphrase Hercules passes an empty one to avoid an interactive prompt. extra_args can tune steghide behavior.",
        "ctf_steghide(action='info', filepath='/opt/workspace/image.jpg')\nctf_steghide(action='extract', filepath='/opt/workspace/image.jpg', passphrase='secret')",
    ),
    "browser_open": _desc(
        "Open a URL in cloakbrowser Chromium and start an interactive browsing session. This is the entry point for driving a real browser to test a JavaScript-heavy site, reproduce a web bug, handle an operator-authorized challenge, or capture visual evidence.",
        "First step of any browser workflow. Follow with browser_snapshot to see the page, then browser_act/browser_read to interact. Use instead of network_curl/web_scan when the target needs a real JavaScript-capable browser.",
        "url is scope-validated and redirects are revalidated. fingerprint is compatibility-only and non-empty values are rejected. Proxy precedence is parameter, BROWSER_PROXY_URL, then direct; profile changes relaunch.",
        "browser_open(url='https://app.target.test/login', session='recon', timezone='America/New_York', locale='en-US')\nbrowser_open(url='https://target.test', session='vpn1', proxy='http://127.0.0.1:8080')",
    ),
    "browser_snapshot": _desc(
        "Capture the page's accessibility tree as compact text with stable element references (@e1, @e2, ...). This is how the agent 'sees' the page and obtains the @refs used by browser_act and browser_read.",
        "Call right after browser_open and again after any navigation or interaction that changes the DOM. Required before browser_act/browser_read because those tools address elements by @ref from the latest snapshot.",
        "compact is default; detailed requests an uncompacted unlimited-depth tree. Use interactive, include_urls, depth, or selector to narrow/expand it. Iframes auto-inline; inline_iframes is a compatibility hint.",
        "browser_snapshot(session='recon')\nbrowser_snapshot(session='recon', detailed=True)\nbrowser_snapshot(session='recon', inline_iframes=True)",
    ),
    "browser_act": _desc(
        "Interact with a page element: click, fill, type, press a key, hover, select an option, or (un)check. Target the element by an @ref from browser_snapshot, by CSS selector, or semantically by role/text/label.",
        "Core interaction step after browser_snapshot. Re-snapshot afterwards if the action changes the page. Use browser_read to verify the result (e.g. new URL or element text).",
        "Use browser_snapshot refs when available. ref/CSS supports all actions. Semantic role/text/label supports click, fill, check, and hover only; use name/exact for accessible matching.",
        "browser_act(action='fill', target='e3', value='admin', session='recon')\nbrowser_act(action='click', target='e7', session='recon')\nbrowser_act(action='press', value='Enter', session='recon')\nbrowser_act(action='click', target='Sign in', target_type='text', session='recon')",
    ),
    "browser_read": _desc(
        "Read data from the page: visible text, inner HTML, an input value, or the page-level URL/title. Use it to verify state after interaction or to extract content.",
        "Use after browser_snapshot/browser_act to confirm results (e.g. did the URL change after a click?) or to scrape a value. Pairs with browser_act in the test/verify loop.",
        "url/title are page-level. ref/CSS supports text/html/value; semantic role/text/label supports text only with optional name/exact. Use snapshot/ref or CSS for unsupported combinations.",
        "browser_read(what='url', session='recon')\nbrowser_read(what='text', target='e5', session='recon')\nbrowser_read(what='value', target='input#email', target_type='css', session='recon')",
    ),
    "browser_screenshot": _desc(
        "Capture a validated PNG screenshot of the current page as native inline MCP image content and save it into the container workspace.",
        "Use to document a finding, capture a rendered PoC, or inspect a page visually. Run after the page has loaded/settled (browser_wait helps).",
        "Shots save to /opt/workspace/browser/<session>/ by default. A relative path resolves under that per-session directory and rejects '..'. full=True captures the scrollable page. annotate=True adds agent-browser element annotations. Every successful call returns ImageContent plus structured path, MIME type, byte count, dimensions, and command status. return_base64=True only adds the legacy base64 metadata copy.",
        "browser_screenshot(session='recon')\nbrowser_screenshot(session='recon', path='login_page.png', full=True, annotate=True)\nbrowser_screenshot(session='recon', return_base64=True)",
    ),
    "browser_eval": _desc(
        "Run arbitrary JavaScript in the page context and return the result. Use for custom DOM extraction, probing JS state, or verifying anti-bot signals.",
        "Use when snapshot/read are not enough — e.g. to read navigator properties, evaluate complex selectors, or trigger page JS. A quick stealth check is to evaluate navigator.webdriver (should be false/undefined under the stealth browser).",
        "The JS is written to a workspace temp file and evaluated to avoid quoting issues. Return a JSON-serializable value (wrap objects in JSON.stringify) for clean output. Runs in the page's main world for the given session.",
        "browser_eval(js=\"JSON.stringify({wd: navigator.webdriver, plugins: navigator.plugins.length})\", session='recon')\nbrowser_eval(js=\"document.querySelectorAll('a').length\", session='recon')",
    ),
    "browser_wait": _desc(
        "Wait for a condition before continuing: an element/selector to appear, a fixed number of milliseconds, specific text, a URL pattern, or a load state.",
        "Use between navigation/interaction and snapshot/read on dynamic or SPA pages so you act on settled content instead of a half-rendered DOM.",
        "condition selects the mode: selector (CSS/@ref in value), ms (milliseconds in value), text (value is the text to await), url (value is a URL glob like '**/dashboard'), or load (value is a load state like 'networkidle'). Keep waits bounded; prefer specific conditions over long fixed sleeps.",
        "browser_wait(condition='load', value='networkidle', session='recon')\nbrowser_wait(condition='text', value='Welcome', session='recon')\nbrowser_wait(condition='ms', value='1500', session='recon')",
    ),
    "browser_session": _desc(
        "Manage isolated stealth browser identities and the optional loopback-only live-view stream. Each session has its own cookies, storage, history, and fingerprint context.",
        "Use to run independent identities, list sessions, close contexts, or watch the selected session through the configured host-loopback stream.",
        "action selects current, list, close, close_all, or stream. Stream discovers the selected session's loopback WebSocket and safely relays it to the configured host port. Closing sessions frees memory.",
        "browser_session(action='list')\nbrowser_session(action='close', session='recon')\nbrowser_session(action='stream', stream_port=4848)",
    ),
    "browser_skill": _desc(
        "Load agent-browser's own built-in skill documentation — the authoritative, version-matched command reference and agent guidance for the underlying browser engine.",
        "Call this when you need exact syntax for any browser capability, especially before using browser_cmd for an advanced/unlisted feature. The 'core' skill covers most browser tasks.",
        "With no name it lists available skills; name='core' (default) with full=True returns the complete command reference. This makes the agent self-aware of every agent-browser command so it can drive the browser through browser_cmd precisely.",
        "browser_skill()\nbrowser_skill(name='core', full=True)",
    ),
    "browser_cmd": _desc(
        "Escape hatch that runs ANY agent-browser command against the current stealth session — giving access to the COMPLETE browser feature set beyond the convenience tools. This is to browser_* what shell_exec is to the shell.",
        "Use for any capability not covered by browser_open/snapshot/act/read/screenshot/eval/wait: cookies, storage, network capture, device/geo emulation, tabs, frames, dialogs, diffs, tracing, React inspection, web vitals, and more. Call browser_skill(name='core', full=True) first if unsure of exact syntax.",
        "Call browser_skill(name='core', full=True) first. args is raw administrator input for controller features absent from structured tools; target/sensitive guarantees are limited and every call is audit-logged.",
        "browser_cmd(args='cookies list', session='recon')\nbrowser_cmd(args=\"set device 'iPhone 15'\", session='recon')\nbrowser_cmd(args='network har /opt/workspace/browser/recon.har', session='recon')\nbrowser_cmd(args='get attr e5 href', session='recon')",
    ),
}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, dict)):
        return list(value)
    return [value]


def usage_error(
    tool: str,
    error_type: str,
    message: str,
    *,
    received: Any = None,
    expected: Any = None,
    examples: Any = None,
    next_steps: Any = None,
    **extra: Any,
) -> dict:
    """Return a consistent, agent-repairable tool usage error."""
    result = {
        "tool": tool,
        "status": "error",
        "error_type": error_type,
        "message": message,
    }
    if received is not None:
        result["received"] = received
    if expected is not None:
        result["expected"] = expected
    example_list = _as_list(examples)
    if example_list:
        result["examples"] = example_list
    next_step_list = _as_list(next_steps)
    if next_step_list:
        result["next_steps"] = next_step_list
    for key, value in extra.items():
        if value is not None:
            result[key] = value
    return result


def selector_error(
    tool: str,
    selector_name: str,
    received: Any,
    expected: Iterable[str],
    *,
    examples: Any = None,
    next_steps: Any = None,
) -> dict:
    expected_values = list(expected)
    return usage_error(
        tool,
        "invalid_selector",
        f"Invalid {selector_name!r} selector for {tool}.",
        received={selector_name: received},
        expected={selector_name: expected_values},
        examples=examples,
        next_steps=next_steps or f"Choose one of: {', '.join(expected_values)}.",
    )


def missing_param_error(
    tool: str,
    parameter: str,
    *,
    when: str = "",
    examples: Any = None,
    next_steps: Any = None,
) -> dict:
    message = f"Missing required parameter {parameter!r}."
    if when:
        message += f" Required when {when}."
    return usage_error(
        tool,
        "missing_required_parameter",
        message,
        expected={parameter: "non-empty value"},
        examples=examples,
        next_steps=next_steps or f"Provide {parameter} and retry the tool call.",
    )


def target_error(tool: str, target: str, exc: Exception, config: Any = None) -> dict:
    message = redact_secrets(str(exc))
    lowered = message.lower()
    error_type = "target_not_allowed" if "blocked" in lowered or "allowed targets" in lowered else "invalid_target"
    return usage_error(
        tool,
        error_type,
        message,
        received={"target": redact_secrets(target)},
        expected={
            "allowed_targets": getattr(config, "allowed_targets", None),
            "blocked_targets": getattr(config, "blocked_targets", None),
        },
        next_steps=[
            "Use a target inside the configured authorization scope.",
            "If the scope is wrong, ask the operator to update ALLOWED_TARGETS or BLOCKED_TARGETS.",
        ],
    )


def path_error(tool: str, path: str, message: str, *, examples: Any = None) -> dict:
    return usage_error(
        tool,
        "invalid_path",
        message,
        received={"path": path},
        expected="A relative workspace-safe path without '..' path traversal.",
        examples=examples,
        next_steps="Use a relative path such as custom/check.yaml.",
    )


def backend_unavailable(tool: str, message: str, *, next_steps: Any = None) -> dict:
    return usage_error(
        tool,
        "backend_unavailable",
        message,
        next_steps=next_steps or "Start the required backend service or run Hercules with that backend enabled.",
    )
