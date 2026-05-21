# Hercules MCP Server: Project Completion & Handover Document

## 1. Project Overview & Objective
The **Hercules MCP Server** is an AI-orchestrated offensive security platform designed to bridge the gap between advanced Large Language Models (LLMs) and a fully-equipped, strictly sandboxed Kali Linux environment. 

The primary objective was to create a server that provides an **unrestricted, asynchronous, and robust** tool execution environment. The AI agent must never be handicapped by simplistic Python wrappers; instead, it has **100% mathematical feature parity** with the native CLI tools.

---

## 2. Current Architecture & Working Mechanism

The Hercules server operates via a dual-layered architecture: a lightweight Python FastMCP server running on the host machine, which proxies structured commands to a persistent, heavy-duty Kali Linux Docker container.

### 2.1. The Docker Engine Sandbox
*   **Base Image**: Built on `kalilinux/kali-rolling`, ensuring access to the latest security packages.
*   **Network Mode (`host`)**: The container shares the host's networking stack natively. If the host connects to an OpenVPN or WireGuard network, the Hercules container immediately inherits those routes, allowing seamless scanning of internal networks.
*   **Startup Speed**: All dependencies and tools are baked directly into the Docker layers. Using `hercules_setup.py`, the massive image is built once, resulting in a server startup time of **less than 5 seconds**.
*   **Session-Isolated Workspaces**: Each container instance gets a unique session ID and a dedicated subfolder (`workspace/{session_id}/`) on the host. This prevents artifacts from different targets or engagements from mixing. The agent can seamlessly tear down the current session and start a fresh one.

### 2.2. Asynchronous Execution (`docker_manager.py`)
Long-running security tools (e.g., Nmap, Amass, Hydra) historically block MCP servers, leading to timeouts. Hercules solves this via:
*   **Background Jobs**: Tools can be launched asynchronously using `nohup`.
*   **PID Tracking**: The system tracks process IDs, allowing the agent to poll for live status (`shell_check_job`) or terminate stuck/infinite loops via SIGKILL (`shell_kill_job`).

### 2.3. The `extra_args` Parity Paradigm
To guarantee the LLM agent is not artificially restricted by missing wrapper arguments, an `extra_args` string parameter is injected into all relevant tools. This acts as an "escape hatch", allowing the AI to dynamically append any esoteric native flag directly into the underlying bash command, unlocking the full potential of tools like Nikto, WPScan, and Whatweb.

---

## 3. Maintenance & Upgrades Guide

The architecture is highly modular. Follow these steps to maintain or expand the project:

### 3.1. Adding New Binaries/Tools to the Sandbox
If a new tool requires installation at the OS level:
1.  Open `Dockerfile`.
2.  If it is an `apt` package, append it to the `apt-get install` block.
3.  If it is a Go/Python package, add a `RUN go install ...` or `RUN pip install ...` block.
4.  Execute `python hercules_setup.py` on the host to rebuild the `hercules-kali` image.

### 3.2. Adding New MCP Tools
To expose a new capability to the LLM agent:
1.  Create or modify a tool wrapper in the appropriate directory (e.g., `hercules/tools/web/new_tool.py`).
2.  Use the `@mcp.tool()` decorator from FastMCP.
3.  **Crucial**: Always extract `docker` and `concurrency` from `ctx.lifespan_context`.
4.  **Crucial**: Always include an `extra_args: str = ""` parameter to maintain feature parity.
5.  Use `async with concurrency.acquire_light(...)` (or `acquire_heavy` for intense scans) to manage thread limits.
6.  Import and register the module in `hercules/main.py`.

### 3.3. Troubleshooting the Environment
*   **Container hangs or fails to start**: Run `docker ps -a` to find the `hercules-sandbox` container and check `docker logs hercules-sandbox`.
*   **Wordlists missing**: Run `python hercules_setup.py` to automatically download SecLists and RockYou.
*   **Zombie processes**: If a background scan hangs indefinitely, the agent can use `shell_kill_job` to terminate it, or the user can restart the server (which cleanly destroys the container).

---

## 4. Comprehensive Tool Registry

The Hercules Server exposes exactly **49 specialized tools** to the LLM. 

### System & Scripting
1.  **`shell_exec`**: Execute arbitrary bash commands (synchronous).
2.  **`shell_exec_background`**: Launch commands asynchronously using `nohup`.
3.  **`shell_check_job`**: Poll a background job's status and output.
4.  **`shell_kill_job`**: Send SIGKILL to a background process.
5.  **`system_start_new_session`**: Atomically restart the environment with a clean, isolated workspace for a new target.
6.  **`system_list_sessions`**: Audit historical and active session workspaces on the host.
7.  **`system_stop_container`**: High-privilege command to permanently terminate the Docker environment.
8.  **`workspace_scripts`**: Upload and execute Python/Bash payload files (with automatic `py_compile` syntax validation).
9.  **`workspace_read_file`**: Read file contents granularly.
10. **`workspace_write_file`**: Write content safely to the workspace.
11. **`workspace_edit_file`**: Perform `sed`-style find-and-replace text edits.

### Network & Nmap
10. **`nmap_quick_scan`**: Rapid top 1000 ports scan.
11. **`nmap_aggressive_scan`**: OS detection, version detection, script scanning.
12. **`nmap_port_scan`**: Specific port targeting.
13. **`nmap_script_scan`**: Run specific NSE scripts.
14. **`nmap_custom_scan`**: Complete raw argument access to Nmap.
15. **`network_curl`**: Arbitrary HTTP requests.
16. **`network_ncat`**: Reverse shells, brokering, and bind listeners.
17. **`network_hping3`**: Custom packet crafting and firewall testing.

### Exploitation
18. **`metasploit_search`**: Search for exploits/auxiliary modules.
19. **`metasploit_run_module`**: Execute modules with an arbitrary options dictionary.
20. **`metasploit_list_sessions`**: View active reverse shells/meterpreter sessions.
21. **`metasploit_interact_session`**: Send commands through an active session.
22. **`metasploit_close_session`**: Clean up idle sessions.
23. **`metasploit_generate_payload`**: Generate raw payloads via `msfvenom`.
24. **`searchsploit`**: Search and mirror exploits from Exploit-DB.
25. **`sqlmap_run`**: Automated SQL injection (includes automatic form-scanning capabilities).

### Web Vulnerability Scanning
26. **`nuclei_run`**: Template-based vulnerability scanner.
27. **`nuclei_write_template`**: Upload custom YAML templates.
28. **`web_httpx`**: HTTP probing and technology fingerprinting.
29. **`web_whatweb`**: Detailed CMS fingerprinting.
30. **`web_wafw00f`**: Web Application Firewall detection.
31. **`web_nikto`**: Classic web server misconfiguration scanner.
32. **`web_wpscan`**: WordPress-specific vulnerability scanner.
33. **`web_arjun`**: Hidden HTTP parameter discovery.
34. **`fuzz_dirs`**: Directory brute-forcing via Gobuster/FFUF.
35. **`web_xss_scan`**: High-speed XSS parameter scanning via Dalfox.
36. **`web_cmdi_scan`**: Automated OS command injection exploitation via Commix.

### Reconnaissance & DNS
37. **`recon_whois`**: Domain registrar and ownership data.
38. **`recon_dig`**: Granular DNS queries and zone transfers.
39. **`recon_amass`**: Deep subdomain enumeration.
40. **`recon_dnsx`**: High-speed, multi-threaded DNS resolution.

### Cracking & Wordlists
41. **`bruteforce_hydra`**: Parallelized online protocol brute-forcing.
42. **`crack_john`**: Offline hash cracking using John the Ripper.
43. **`creds_wordlists_manage`**: Inspect, search, and list dictionaries located in `/usr/share/wordlists` (e.g., SecLists, RockYou).

### CTF & Forensics
44. **`ctf_binwalk`**: Firmware extraction and file signature carving.
45. **`ctf_strings`**: Printable string extraction with grep filtering.
46. **`ctf_steghide`**: Steganography embedding/extraction for image/audio files.
47. **`ctf_base64`**: Arbitrary base64 encoding/decoding.
48. **`ctf_xxd`**: Hex dumping and binary reconstruction.

### On-Demand MCP Resources
49. **Post-Exploitation Resource Delivery**: Instead of pre-seeding the workspace, Hercules serves critical post-exploitation files (`linpeas.sh`, `winpeas.bat`, `powerup.ps1`) and API datasets (GTFOBins, LOLBAS) dynamically as **MCP Resources**. The agent can read these directly from `resource://post_exploitation/...` whenever needed, keeping the workspace completely clean until these tools are explicitly required.
