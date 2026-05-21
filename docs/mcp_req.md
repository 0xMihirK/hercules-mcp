# AI-Orchestrated Kali MCP Server for Offensive Security

## 1. Project Overview

This project specifies an MCP (Model Context Protocol) server that orchestrates a fully containerized offensive security environment based on the official `kalilinux/kali-rolling` Docker image, extended at runtime with a comprehensive penetration-testing toolchain.[1] The MCP server exposes these capabilities as structured tools that can be driven by an AI agent, enabling automated and parallelized security workflows while ensuring all execution happens inside ephemeral Docker containers instead of the host OS.[2]

A core design requirement is that the Kali container should behave *as if it were the host machine* from a networking perspective: when the host is connected to an OpenVPN (or similar) network, the container must transparently share that connectivity and routing.[3][4] This is achieved by running the container in host network mode and aligning with the host's network namespace.

Key goals:
- Provide an AI-controllable toolbox for nmap, Metasploit, nuclei, sqlmap, brute-force utilities, searchsploit, custom scripts, and more, all running inside a Kali container.[2][1]
- Ensure strict isolation by starting a fresh Kali container for each MCP server run and never executing tooling directly on the host OS.
- Make the container share the host network namespace (for example, using `--network host` / `network_mode="host"`), so VPN tunnels, routes, and firewall rules on the host automatically apply to tools running inside the container.[3][5]
- Support parallel tool execution so an AI agent can, for example, run port scans, HTTP fuzzing, and exploit searches concurrently against the same or different targets.
- Include curated post-exploitation resources (linPEAS, winPEAS, PowerUp) as MCP resources for quick retrieval during privilege escalation or CTFs.

## 2. High-Level Requirements

### Functional requirements

- Spin up a new `kalilinux/kali-rolling` container on each MCP server start; install tools via `apt` using one of the recommended metapackages or individual tools.[1]
- Run the Kali container with host networking (`--network host` / `network_mode="host"`) so that it shares the host network stack, including access to VPN interfaces such as `tun0`.[3][4]
- Provide MCP tools for:
  - Nmap: quick scans, aggressive scans, port-specific scans, script scans, and custom NSE script authoring and execution.
  - Metasploit: full access via `msfrpcd`, including module management and msfvenom-based payload generation.
  - Bruteforce: wrappers around tools like `hydra` or `medusa` (if installed) for protocol-level brute forcing.
  - Sqlmap: full parameterization (GET/POST, cookies, tamper scripts, level/risk, DB enumeration, dumping, OS-shell, file read/write).
  - Nuclei: running built-in templates and authoring/executing custom templates.
  - searchsploit: querying Exploit-DB for relevant exploits.
  - Generic script execution: run user-provided Python or shell scripts inside the container.
  - Direct interactive shell access: provide a pseudo-terminal tool to open an interactive shell session into the running Kali container.
- Expose MCP resources for post-exploitation helpers:
  - `linpeas.sh` (Linux privilege escalation enumeration).
  - `winPEAS.bat` (Windows privilege escalation enumeration).
  - `PowerUp.ps1` (PowerShell-based privilege escalation checks).
- Allow the AI agent to orchestrate these tools in parallel, with robust logging, structured outputs, and result streaming.

### Non-functional requirements

- Isolation: nothing executes on host; all tooling runs inside Docker.
- Network parity with host: the container shares the host network stack so any VPNs or advanced routing configured on the host are transparently used by tools in the container.[3][4]
- Ephemerality: containers are per-run; optional flag to preserve a container for debugging.
- Observability: logs for each tool invocation (command, parameters, exit code, stdout, stderr, timing).
- Safety controls: configurable whitelists/blacklists for target IPs, ports, and domains.
- Performance: parallel tool runs with sensible defaults to avoid resource starvation (e.g., limit concurrent heavy scans), including OS-level resource limits on the container.

## 3. Technology Stack

- **Base OS image:** `kalilinux/kali-rolling` from Docker Hub.[1]
- **Tooling installation:**
  - Minimal: `apt update && apt -y install <tool1> <tool2> ...`.
  - Broad: `apt update && apt -y install kali-linux-headless` for a headless, non-GUI toolset, or `kali-linux-large` for a near-full Kali experience.[1][2]
- **Orchestration runtime:** Python 3.
- **MCP implementation:** `fastmcp` library for defining tools, resources, and server lifecycle.
- **Container control:** Docker Engine API via Python SDK (`docker` library) using `network_mode="host"` and appropriate capabilities.[5][6]
- **Metasploit RPC:** `msfrpcd` running inside the container, communicated with using its JSON-RPC API.

## 4. System Architecture

### 4.1 Components

- **MCP Server (Host process):**
  - Runs the FastMCP-based server process.
  - On startup, creates a new Kali container in host network mode, installs tools, and keeps the container running.
  - Exposes MCP tools that map to commands executed inside the container.

- **Kali Docker Container:**
  - Based on `kalilinux/kali-rolling`.
  - On first boot, runs `apt update` and installs required packages (`kali-linux-headless` or specific tools).
  - Runs supporting daemons as needed (e.g., `postgresql` for Metasploit DB, `msfrpcd`).
  - Shares host network namespace via `--network host`, meaning it uses the host's routing table, DNS, and VPN interfaces directly.[3]

- **Tools Layer:**
  - Python wrappers for calling security tools inside the container (via `docker exec` or Docker SDK `exec_run`).
  - Normalizes parameters, handles command construction, timeout, and parsing of key output.

- **AI Agent / Client:**
  - Connects to MCP server and uses tools in structured fashion.
  - Can coordinate multi-step workflows (recon → enumeration → exploitation → post-exploitation).

### 4.2 Networking Model and VPN Integration

- The container is started with host network mode:
  - CLI: `docker run --rm -it --network host kalilinux/kali-rolling /bin/bash`.
  - Python SDK: `client.containers.run(image, network_mode="host", ...)`.[5]
- With host networking, the container does not get its own IP; instead, it shares the host's network stack and can access services reachable from the host, including VPN-protected networks.[3]
- If the host is connected to an OpenVPN network using a TUN/TAP interface (e.g., `tun0`), tools inside the container will route over that VPN exactly as processes on the host do, as long as Docker itself uses the same network namespace.[3][4]
- On some setups, Docker may need to be restarted after establishing the VPN to ensure the new routes are visible to containers using host networking.[4]
- No Docker port mappings (`-p`/`--publish`) are used or needed, because host networking exposes container-bound ports directly on the host.[3]

### 4.3 Architecture Flow (Conceptual)

1. AI agent sends an MCP tool invocation (e.g., `nmap.scan`) with parameters.
2. MCP server translates this into a command executed inside the Kali container via Docker exec.
3. Docker runs the command in the shared host network namespace; stdout/stderr are streamed back.
4. MCP server parses/normalizes results and returns them to the AI agent.
5. The AI agent decides next steps (e.g., run sqlmap on discovered HTTP services, searchsploit on banner versions).

## 5. Container Lifecycle and Isolation

### 5.1 Startup Sequence

1. MCP server process starts.
2. Docker client is initialized.
3. The server ensures the `kalilinux/kali-rolling` image is present, pulling it if needed.[1]
4. A new container is created with:
   - `network_mode="host"` to share host networking.[5][3]
   - `tty=True`, `stdin_open=True` for interactive shell support.
   - Optional capabilities or `--privileged` if advanced networking tools require access to `/dev/net/tun` or raw sockets, depending on the deployment model.[7][8]
5. An initialization script runs inside the container to:
   - Update package lists: `apt update`.
   - Install required tools via metapackages or individual packages (e.g., `kali-linux-headless`, `nmap`, `metasploit-framework`, `sqlmap`, `nuclei`, `hydra`, `seclists`, `exploitdb`).[1][2]
   - Initialize Metasploit (database setup, `msfdb init`, and starting `msfrpcd`).

### 5.2 Execution Model

- All MCP tools execute commands via Docker exec in the running container.
- No tool ever executes directly on the MCP host OS.
- The container runs as root by default, consistent with the official Kali image usage.[2]
- Tool invocation is abstracted through Python wrappers that:
  - Construct commands safely with explicit parameterization.
  - Apply timeouts and resource limits per command.
  - Capture stdout/stderr and exit codes.

### 5.3 Shutdown and Persistence

- When the MCP server stops, it stops and removes the Kali container by default:
  - `docker stop <container>`
  - `docker rm <container>`
- Configuration flag `preserve_container` can keep containers for debugging.
- Separate host volumes can be mounted for persistent artifacts (scan results, custom templates, scripts), without persisting the entire container filesystem.

## 6. MCP Tool Specifications

This section describes each logical tool group exposed through MCP, their main methods, and core parameters. All tools run inside the Kali container, sharing the host's network.

### 6.1 Nmap Tool

**Purpose:** Comprehensive port scanning and service enumeration.

**Core MCP methods:**
- `nmap.quick_scan(target)` → `nmap -T4 -F <target>`.
- `nmap.aggressive_scan(target)` → `nmap -T4 -A -v <target>`.
- `nmap.port_scan(target, ports)` → `nmap -p <ports> <target>`.
- `nmap.script_scan(target, scripts, extra_args)` → `nmap --script <scripts> <extra_args> <target>`.
- `nmap.custom_scan(raw_args)` → `nmap <raw_args>` for advanced operators.
- `nmap.write_nse_script(name, content)` → writes to `/usr/share/nmap/scripts/custom/<name>.nse`.
- `nmap.run_nse_script(target, script_name, extra_args)` → `nmap --script custom/<script_name>.nse <extra_args> <target>`.

**Implementation details:**
- Output may be requested in normal, greppable (`-oG -`), or XML (`-oX -`) form to facilitate parsing in the MCP server.
- The AI agent can request parsed JSON representations of host/port/service data derived from nmap XML output.
- Parallelism can be achieved by invoking multiple nmap commands concurrently across different targets or port ranges, respecting configured concurrency limits.

### 6.2 Metasploit / msfvenom Tool

**Purpose:** Exploitation and payload generation via msfrpcd.

**Core design:**
- Inside the container, `msfrpcd` runs with a configured username/password and port; it may rely on a Postgres DB started in the container.
- The MCP server includes a Python client that speaks the Metasploit RPC protocol over the host network (which is shared with the container).

**Core MCP methods (examples):**
- `metasploit.search(query)` → search modules by name, reference, or CVE.
- `metasploit.run_module(module_type, module_name, options)` → run exploit/auxiliary/post modules with dynamic options.
- `metasploit.list_sessions()` / `metasploit.interact_session(session_id, command)`.
- `metasploit.generate_payload(payload, options)` → uses msfvenom under the hood to generate payload binaries or shellcode.

**Implementation details:**
- RPC connection parameters (host, port, username, password, SSL) are configurable; by default, communication is local to the container namespace, but since network is shared, host-loopback access is trivial.
- Tool responses are normalized into structured JSON (e.g., modules, options, results) for the AI agent.

### 6.3 Bruteforce Tooling

**Purpose:** Credential brute forcing for common protocols.

**Backing tools:** `hydra`, `medusa`, or `patator` (configurable).

**Core MCP methods (hydra example):**
- `bruteforce.hydra(target, service, usernames, passwords, options)` → constructs hydra command, e.g.,
  - `hydra -L users.txt -P passwords.txt -s 22 ssh://10.10.10.10`.

**Implementation details:**
- Wordlists can be provided via mounted volumes (e.g., `SecLists`) or uploaded via MCP resources.
- Rate limiting, max attempts, and lockout-safety thresholds are configurable.

### 6.4 Sqlmap Tool

**Purpose:** Automated SQL injection detection and exploitation.

**Core MCP methods:**
- `sqlmap.scan_basic(target_url)`.
- `sqlmap.scan_custom(target_url, method, data, cookies, level, risk, techniques, tamper, proxy, extra_args)`.
- `sqlmap.enumerate(target_url, what)` (DBs, tables, columns, users, privileges).
- `sqlmap.dump(target_url, db, table)`.
- `sqlmap.os_shell(target_url)` and `sqlmap.os_cmd(target_url, command)` when supported.

**Implementation details:**
- Parameters are mapped 1:1 to sqlmap flags where possible.
- The MCP server can parse sqlmap logs to surface found injection points and DB metadata in structured form.

### 6.5 Nuclei Tool

**Purpose:** Template-based vulnerability scanning.

**Core MCP methods:**
- `nuclei.run(targets, templates, severity, tags, rate_limit, extra_args)`.
- `nuclei.write_template(path, content)` to add custom templates.

**Implementation details:**
- Templates are stored in a dedicated directory mounted as a volume so they can persist across container runs.
- Output can be JSON-normalized for AI processing.

### 6.6 searchsploit Tool

**Purpose:** Quickly look up public exploits by software name, version, or CVE.

**Core MCP methods:**
- `searchsploit.search(query)` → `searchsploit <query>`.
- `searchsploit.get_exploit(path_or_id)` → retrieve exploit code / PoC for inspection.

**Implementation details:**
- ExploitDB database is kept up to date via `searchsploit -u` during initialization when desired.

### 6.7 Script Execution Tools

**Purpose:** Allow the AI agent to write and run custom scripts in the container.

**Core MCP methods:**
- `scripts.write_python(name, content)` → saves to a workspace path inside container (e.g., `/opt/workspace/py/<name>.py`).
- `scripts.run_python(name, args, venv)` → executes Python scripts, optionally inside a virtual environment.
- `scripts.write_shell(name, content)` → saves to `/opt/workspace/sh/<name>.sh` with executable permissions.
- `scripts.run_shell(name, args)` → executes shell scripts.

**Implementation details:**
- Scripts are executed with inherited environment (e.g., proxy settings, DNS) that match the host network.
- Output is captured and can be truncated or streamed.

### 6.8 Interactive Shell Tool

**Purpose:** Provide direct shell access to the Kali container when needed.

**Core options:**
- Simple: `shell.exec(command)` tool that runs a one-off shell command and returns stdout/stderr.
- Advanced: interactive sessions using a pseudo-terminal (PTY) bridged through a streaming channel to the client.

**Implementation details:**
- PTY sessions can be tied to session IDs; server maintains mapping of PTY handles and enforces timeouts.

## 7. MCP Resources for Post-Exploitation

The MCP server exposes static resources that the AI agent can request and then deploy on target machines during post-exploitation.

Configured resources:
- `linpeas.sh` from PEASS-ng releases (Linux privilege escalation enumeration).
- `winPEAS.bat` from PEASS-ng releases (Windows privilege escalation enumeration).
- `PowerUp.ps1` from PowerSploit (PowerShell privilege escalation checks).

Server behavior:
- Downloads these files on startup or first request and caches them in a `resources/` directory on the host.
- Exposes them via MCP resource descriptors (name, description, filename, MIME type).
- Allows the AI agent to request the resource content for upload/execution on compromised hosts.

## 8. FastMCP Server Design

The MCP server is implemented using the `fastmcp` library, which simplifies defining tools, resources, and server lifecycle hooks.

### 8.1 Directory and Module Layout

- `main.py`:
  - Initializes Docker client and starts a new Kali container in host network mode.
  - Runs tool installation bootstrap in the container.
  - Registers tools (nmap, metasploit, sqlmap, nuclei, bruteforce, searchsploit, scripts, shell) with FastMCP.
  - Registers post-exploitation resources.
  - Starts the MCP server.

- `docker_manager.py`:
  - Wrapper for creating, starting, stopping, and exec-ing into the Kali container.
  - Provides methods like `exec(cmd, timeout, env)` used by tool implementations.
  - Encapsulates `network_mode="host"`, volume mounts, and capability flags.

- `tools/`:
  - `nmap_tool.py`, `metasploit_tool.py`, `sqlmap_tool.py`, `nuclei_tool.py`, `bruteforce_tool.py`, `searchsploit_tool.py`, `scripts_tool.py`, `shell_tool.py`.
  - Each exposes FastMCP tool definitions and uses `docker_manager` to execute commands.

- `resources/`:
  - Cached copies of linPEAS, winPEAS, PowerUp scripts.

### 8.2 Parallel Execution and Concurrency Control

- FastMCP handlers are implemented using async/await or a thread pool to avoid blocking on long-running commands.
- A concurrency manager tracks active jobs per tool and globally:
  - Limits total concurrent heavy scans (e.g., nmap aggressive scans, large sqlmap runs).
  - Provides queueing and fair scheduling between tools.
- Long-running jobs can stream logs progressively to the AI agent.

## 9. Typical Flows and Use Cases

### 9.1 Vulnerability Assessment Flow

1. **Recon:**
   - AI calls `nmap.quick_scan` or `nmap.aggressive_scan` on target(s).
   - Parses open ports, services, and versions.

2. **Enumeration:**
   - For HTTP services: run `nuclei.run` and `sqlmap.scan_custom` on interesting endpoints.
   - For SSH/FTP/SMB/etc.: run `bruteforce.hydra` with appropriate wordlists.

3. **Exploit Research:**
   - Use `searchsploit.search` based on service banners and versions.

4. **Exploitation:**
   - Trigger Metasploit modules via `metasploit.run_module`.
   - Generate payloads with `metasploit.generate_payload` when needed.

5. **Post-Exploitation:**
   - Once a shell is obtained, download and run `linpeas.sh`, `winPEAS.bat`, or `PowerUp.ps1` via the MCP resources.

Because the container is in host network mode, all of these steps automatically respect the host's VPN connectivity and routing, making the behavior equivalent to running tools directly on a full Kali host connected to the same VPN.[3][4]

### 9.2 CTF / HackTheBox-Style Flow

1. AI launches nmap and HTTP enumeration in parallel against the CTF box.
2. Based on findings, AI runs targeted `sqlmap` or `nuclei` scans.
3. AI queries `searchsploit` and launches Metasploit modules.
4. After getting a shell, AI retrieves and uses PEAS or PowerUp scripts from MCP resources for privilege escalation enumeration.
5. AI writes small Python/shell scripts to automate repetitive tasks or decode artifacts using the script-execution tools.

## 10. Security and Safety Considerations

- **Legal/ethical use:** The project is intended for authorized testing, labs, and CTFs only.
- **Network scoping:** Provide configuration for allowed networks and domains; tools refuse to run outside these ranges.
- **Resource limits:** Use Docker resource constraints (CPU, memory) and concurrency limits in the MCP server.
- **Logging and audit trail:** Persist per-command logs (timestamp, tool, arguments, target, result) for later review.
- **Privilege management:** Avoid `--privileged` unless required; prefer minimal capabilities (e.g., `NET_ADMIN`) and host networking where appropriate.[7][8][4]

## 11. Expected Results and Outcomes

When implemented, the MCP Kali offensive security server will:
- Enable an AI agent to autonomously run end-to-end vulnerability assessments and CTF workflows using a Kali-like toolkit, without installing tools on the host.
- Provide network behavior that matches the host (including VPN and complex routing), since the container shares the host network stack via host networking.[3][4]
- Offer a consistent, reproducible environment, since each run starts from the same base image and deterministic provisioning steps.[1]
- Make it easy to extend functionality by adding new tools or MCP methods (e.g., gobuster, ffuf, dirsearch, crackmapexec) while keeping the isolation and orchestration model unchanged.
- Improve productivity for security researchers and students by combining a rich toolset with AI-driven orchestration and reasoning.

## 12. Future Enhancements

- Add more specialized tools (e.g., bloodhound, impacket suite, crackmapexec, responder) as MCP tools.
- Support multiple concurrent containers for large-scale scanning, potentially with different network profiles.
- Integrate with external knowledge bases (CVE feeds, exploit databases) for better context.
- Add higher-level AI primitives ("assess this web app", "enumerate this AD domain") that internally orchestrate multiple tools.
