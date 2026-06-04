<p align="center">
  <img src="assets/logo.svg" alt="Hercules MCP" width="220" style="margin-bottom: 20px;"/>
</p>

<h1 align="center">Hercules MCP</h1>

<p align="center">
  <em>Containerized offensive-security tooling for AI agents through the Model Context Protocol</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://badge.mcpx.dev?status=on" title="MCP Enabled" />
  <img src="https://img.shields.io/badge/Docker-Kali_Linux-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/license-MIT-F57C00" alt="License" />
</p>

---

Hercules MCP is a [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes offensive-security workflows as structured MCP tools. It starts a per-session Kali Linux Docker container, routes scanner and exploitation commands through that container, stores evidence in a local workspace, and returns compact, agent-friendly results.

<p align="center">
  <img src="assets/architecture.png" alt="Architecture" width="720" />
</p>

## Contents

- [Why Hercules?](#why-hercules)
- [Tools Available](#tools-available)
- [Stealth Browser](#stealth-browser)
- [Output, Artifacts, And Timeouts](#output-artifacts-and-timeouts)
- [MCP Resources](#mcp-resources)
- [Quick Start](#quick-start)
- [Connect To An MCP Client](#connect-to-an-mcp-client)
- [Troubleshooting Setup](#troubleshooting-setup)
- [Design Principles](#design-principles)
- [Project Structure](#project-structure)
- [Acknowledgements](#acknowledgements)
- [Security](#security)
- [License](#license)

---

## Why Hercules?

### Sandbox-first execution

Tool commands run inside a Docker container based on `kalilinux/kali-rolling`. The project workspace is mounted into the container at `/opt/workspace`, and session files, logs, custom scripts, templates, payloads, and artifacts are persisted under `workspace/<session-id>/` on the host.

Hercules uses one MCP server instance per project checkout. A startup lock prevents multiple live Hercules servers in the same checkout from removing or racing each other's containers. Containers are removed on shutdown by default; set `PRESERVE_CONTAINER=true` when you want to keep a session for debugging.

### Agent-focused output

Hercules is built for LLM use. It strips ANSI/OSC escape codes, color sequences, carriage-return progress rewrites, and explicit known scanner banners. High-noise tools use native quiet or structured output where practical, and the shared executor records completeness metadata so agents can tell whether output was complete, filtered, or truncated.

### MCP-native workflow mapping

Every public capability is exposed as a typed MCP tool or resource. The server includes rich instructions and tool descriptions so clients can map tasks to reconnaissance, web scanning, exploitation, post-exploitation, CTF, shell, file, and session workflows.

### Stealth browser automation

Drive a bot-evading Chromium to manually test JavaScript-heavy or anti-bot-protected sites — navigate, snapshot, interact, screenshot, and run page JavaScript through structured `browser_*` tools. See [Stealth Browser](#stealth-browser) for how it works.

### Interactive setup and token budgeting

`python hercules_setup.py` launches a clean terminal UI (built with [Textual](https://textual.textualize.io/)) for first-time setup. Beyond building the image, it lets you opt out of whole tool families you don't need — Metasploit, the browser, SQLMap, and so on — and shows the context-token cost of the tool surface updating live as you toggle. Opted-out tools are simply **not registered**, so their names, descriptions, and schemas never enter the model's context window (that is the token saving), while the underlying binaries stay baked into the image and remain reachable through `shell_exec`. Selections persist to `.env` as `HERCULES_DISABLED_TOOLS`; a headless `--tokens` report and a `--classic` non-interactive flow are also available.

### Resilient sessions

A single tool failure never takes down the session: uncaught tool exceptions are converted into structured, agent-repairable errors by a middleware firewall. If the container crashes mid-session, Hercules recovers it while preserving the same session id and workspace — files, background jobs, and the browser daemon survive — and a background watchdog repairs a dead container before the next tool call. One server runs per checkout, guarded by a startup lock.

---

## Tools Available

Expected registered tool count:

| Mode | Tool count |
|------|------------|
| Metasploit enabled, default `SKIP_METASPLOIT=false` | 45 |
| Lightweight mode, `SKIP_METASPLOIT=true` | 40 |

Counts are the full surface; the interactive setup can opt out of tool families you don't need (see [Interactive setup and token budgeting](#interactive-setup-and-token-budgeting)).

Hercules exposes a compact MCP API over these Kali tools and workflow
capabilities. The MCP client sees structured tool calls, but the README keeps
the surface at the tool-family level so agents and operators can reason about
what is available without memorizing every selector or wrapper.

| Category | Available tools and capabilities |
|----------|-----------|
| Reconnaissance | Nmap, DNS lookups, dnsx, Whois, Amass |
| Web scanning | Nuclei, httpx, WhatWeb, Wafw00f, Nikto, WPScan, Arjun, ffuf, Gobuster |
| Web vulnerability testing | Dalfox, Commix, SQLMap |
| Exploitation | Metasploit Framework, SearchSploit, payload generation, listener management, session/job management |
| Password attacks | Hydra, John the Ripper |
| Networking | curl, Ncat, hping3 |
| CTF and forensics | Binwalk, Steghide |
| Stealth browser | Bot-evading Chromium (cloakbrowser) driven by agent-browser: navigate, accessibility snapshot, click/type/fill, wait, screenshot, eval JS, network/HAR capture, isolated sessions — see [Stealth Browser](#stealth-browser) |
| Shell and workspace | Direct Kali shell commands inside the container, background jobs, workspace file read/write, binary-safe file transfer |
| System/session control | Container session lifecycle, active session listing, network information |

Agents can write their own custom Nmap NSE scripts and Nuclei templates through
the MCP workflow, save them into the container workspace, validate them, and run
them against authorized targets. Agents also have direct shell-command access to
the Kali container, so they can use installed tools manually when a structured
tool call is not the right fit.

The server keeps redundant thin wrappers out of the public MCP surface. Related
operations are grouped behind structured parameters, while specialized workflows
such as Nmap NSE authoring, Nuclei template authoring, SQLMap, curl, hping3, and
directory fuzzing remain directly accessible where dedicated controls are useful.

The exact MCP function names, parameters, and selector values are advertised by
the MCP server itself through tool metadata.

---

## Stealth Browser

Hercules ships a bot-evading browser so agents can manually test JavaScript-heavy or anti-bot-protected sites, reproduce web bugs interactively, and capture visual evidence. Through structured `browser_*` MCP tools, agents can navigate, capture an accessibility-tree snapshot with stable element refs, click/type/fill, wait for dynamic content, screenshot, run page JavaScript, and capture network/HAR traffic — all within isolated browser sessions. `browser_cmd` is an escape hatch to every other agent-browser subcommand, and `browser_skill` loads agent-browser's own version-matched command reference. The browser starts lazily on first use, runs headless by default (or headed under Xvfb via `BROWSER_HEADLESS=false`), and keeps page and session state across separate MCP calls.

### How agent-browser and cloakbrowser combine to evade bot detection

Hercules joins two open-source projects, each used for its strength:

- **[agent-browser](https://github.com/vercel-labs/agent-browser)** is the *controller* — a Rust CLI with a persistent daemon that exposes an agent-friendly accessibility snapshot (with `@ref` element handles) plus the full click / type / wait / eval command surface.
- **[cloakbrowser](https://github.com/CloakHQ/cloakbrowser)** is the *engine* — a Chromium built with compile-time C++ patches that remove the tell-tale signals of automation.

Instead of running a remote-debugging (CDP) server, agent-browser launches the cloakbrowser stealth Chromium **directly** through the `AGENT_BROWSER_EXECUTABLE_PATH` environment variable (the binary path reported by `python3 -m cloakbrowser info`) and manages its lifecycle; its daemon then holds that browser open across MCP tool calls. Because the engine is cloakbrowser, the page presents a realistic, human-like fingerprint rather than an automated one — `navigator.webdriver` reads `false`, plugins and languages are populated, and canvas / WebGL / audio / font signals are spoofed — so it passes checks that flag a vanilla headless Chromium (verified all-green against `bot.sannysoft.com`). The patched Chromium is downloaded into your locally built image at setup time and is never repackaged or redistributed.

> Special thanks to the **agent-browser** and **cloakbrowser** projects for making this possible — see [Acknowledgements](#acknowledgements).

---

## Output, Artifacts, And Timeouts

Hercules returns tool output in a way that is easier for agents to reason about:

- Clean output by default: terminal colors, escape codes, progress rewrites, and
  known scanner banners are removed before output is sent back to the agent.
- Clear completeness signals: results tell the agent whether stdout or stderr was
  truncated, how large each stream was, and whether the returned output is
  complete.
- Evidence is preserved: when output is filtered or shortened, Hercules saves the
  fuller stdout, stderr, or raw command stream as workspace artifacts.
- Artifact paths are returned in the result: agents can open those saved files
  through the workspace file tools when they need full logs, generated payloads,
  raw scanner output, or command evidence.
- Useful metadata stays visible: command results can include fields such as
  output-complete status, truncation status, artifact paths, and filter notes.
- Timeouts are explicit: long-running commands return a timeout status, timeout
  duration, command metadata, exit code, and any stdout or stderr captured before
  the timeout.
- Long tasks have safer paths: agents can increase a timeout when the tool allows
  it, run a background job, or use a listener/session workflow instead of waiting
  on one foreground command.

---

## MCP Resources

Hercules also exposes resources that help agents decide what to write or run:

| Resource group | What it provides |
|----------------|------------------|
| Nmap NSE skills | A detailed agent handbook for designing, writing, validating, debugging, and running complex custom NSE scripts. |
| Nuclei skills | A detailed agent handbook for designing, writing, validating, debugging, and running custom Nuclei templates. |
| Linux post-exploitation | linPEAS-style enumeration content and GTFOBins knowledge for Linux privilege-escalation decisions. |
| Windows post-exploitation | winPEAS-style checks, PowerUp-style PowerShell checks, and LOLBAS knowledge for Windows privilege-escalation and living-off-the-land decisions. |

Agents should read the NSE or Nuclei skill resource before creating custom
detection logic. After getting a shell or Metasploit session, agents should use
the post-exploitation resources to choose the right enumeration scripts,
privilege-escalation checks, and living-off-the-land techniques.

---

## Quick Start

### Prerequisites

- Docker Engine or Docker Desktop with the Docker daemon running
- Python 3.11+
- `uv` is recommended for local dependency management

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/hercules-mcp.git
cd hercules-mcp
uv sync
```

### 2. Build the Kali image and wordlists

```bash
python hercules_setup.py
```

Run in a terminal, this opens a clean interactive UI where you can opt out of tool families you don't need and watch the context-token cost of the tool surface update live, then build. It checks Docker, builds the `hercules-kali` image from `Dockerfile` (including the stealth browser stack), and downloads local wordlist archives for SecLists and `rockyou.txt`. With no TTY (for example in CI) it runs non-interactively.

Useful flags:

```bash
python hercules_setup.py --check     # verify an existing setup
python hercules_setup.py --tokens    # print the per-capability context-token report
python hercules_setup.py --classic   # skip the UI; build non-interactively
python hercules_setup.py --rebuild   # force a no-cache image rebuild
```

### 3. Configure environment

```bash
cp .env.example .env
```

Common settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `MSF_PASSWORD` | `hercules` | Password used by `msfrpcd` and the Metasploit RPC client. |
| `SKIP_METASPLOIT` | `false` | Set to `true` to omit Metasploit tools and skip RPC startup. |
| `PRESERVE_CONTAINER` | `false` | Keep the Docker container after MCP shutdown for debugging. |
| `USE_PRIVILEGED` | `false` | Use Docker `--privileged` instead of minimal network capabilities. |
| `TOOL_INSTALL_MODE` | `minimal` | Tool install mode value passed through configuration. |
| `MAX_CONCURRENT_HEAVY` | `3` | Semaphore limit for heavy operations. |
| `MAX_CONCURRENT_LIGHT` | `10` | Semaphore limit for light operations. |
| `ALLOWED_TARGETS` | empty | Comma-separated allow-list. Empty means no allow-list restriction. |
| `BLOCKED_TARGETS` | empty | Comma-separated block-list. Block rules take priority. |
| `CONTAINER_CPU_LIMIT` | `0` | Docker CPU limit. `0` means unlimited. |
| `CONTAINER_MEM_LIMIT` | `0` | Docker memory limit. `0` means unlimited. |
| `DEFAULT_TIMEOUT` | `300` | Default command timeout in seconds. |
| `HERCULES_DISABLED_TOOLS` | empty | Comma-separated MCP tools to not register (managed by the setup UI). Trims their schema from the agent's context; the binary stays usable via `shell_exec`. Core tools cannot be disabled. |
| `BROWSER_HEADLESS` | `true` | Run the stealth browser headless, or headed under Xvfb when `false`. |
| `BROWSER_STREAM_PORT` | `0` | Forward a headed live-view port to the host (`0` = off, headed mode only). |
| `BROWSER_PROXY` | empty | Default upstream proxy for browser sessions. |
| `WATCHDOG_INTERVAL` | `20` | Seconds between container health checks; `0` disables the watchdog. |

### 4. Start the MCP server

```bash
uv run hercules
```

On Windows, you can start the server through `uv run hercules` from PowerShell,
or point an MCP client at the virtual-environment Python executable with
`-m hercules.main`.

---

## Connect To An MCP Client

For a generic MCP client:

```json
{
  "mcpServers": {
    "hercules": {
      "command": "uv",
      "args": ["run", "hercules"],
      "cwd": "/absolute/path/to/hercules-mcp",
      "env": {
        "SKIP_METASPLOIT": "false"
      }
    }
  }
}
```

For Codex GUI on Windows, use STDIO with either `uv` or the local virtual
environment:

| Field | Value |
|-------|-------|
| Command to launch | `uv` |
| Arguments | `run`, `hercules` |
| Working directory | Absolute path to this repository |

If you want lightweight mode in Codex, set environment variable `SKIP_METASPLOIT=true` in the client configuration. Otherwise leave it unset.

---

## Troubleshooting Setup

If `python hercules_setup.py` fails during the Docker build, first confirm Docker Desktop or the Docker daemon is running, then rerun:

```bash
python hercules_setup.py --check
python hercules_setup.py
```

Kali package mirror errors such as `Failed to fetch`, `temporary failure`, or `Hash Sum mismatch` are usually transient mirror, DNS, proxy, VPN, or Docker networking issues. The Dockerfile retries package installation, uses `--fix-missing`, and switches Kali mirror URLs to `kali.download`, but persistent network failures still need local networking fixes.

If the image exists but runtime checks fail, rebuild and verify:

```bash
docker build --no-cache -t hercules-kali .
python hercules_setup.py --check
```

If a client reports no Hercules tools, confirm that only one MCP server is running for this checkout and that the client command points at this repository. Multiple server processes for the same checkout are rejected by the instance lock; older processes from other checkouts should be stopped if they are not needed.

---

## Design Principles

| Principle | What it means |
|-----------|---------------|
| Sandboxed execution | Tools run inside Docker with a mounted workspace for evidence and generated files. |
| Stable tool API | Public tool names, selectors, signatures, target validation, concurrency class, timeout behavior, and success response fields are treated as compatibility-sensitive. |
| Structured output | Tools return parsed or compacted output where useful, while full evidence is preserved through artifacts when filtering or truncation occurs. |
| Concurrency control | Heavy operations and light operations use separate async semaphores. |
| Target controls | `ALLOWED_TARGETS` and `BLOCKED_TARGETS` constrain targetable tools and return structured usage errors when calls are out of scope. |
| Cross-platform operation | The server runs on Windows, macOS, and Linux as long as Python and Docker are available. |

---

## Project Structure

```text
hercules-mcp/
|-- hercules/
|   |-- main.py                  # FastMCP entrypoint and tool/resource registration
|   |-- core/                    # Config, Docker lifecycle, concurrency, guidance, tool catalog
|   |-- output/                  # Sanitizer, banner stripping, filters, truncation
|   |-- tools/                   # MCP tool implementations by category (incl. browser/)
|   `-- resources/               # Agent skill docs and post-exploitation resources
|-- docker/
|   `-- entrypoint.sh            # Container startup, wordlists, msfrpcd
|-- tests/                       # Unit tests and live-test evidence/checklists
|-- workspace/                   # Runtime session workspaces and artifacts
|-- wordlists/                   # Downloaded SecLists and rockyou archives
|-- Dockerfile                   # Kali container image definition
|-- hercules_setup.py            # Interactive setup, token budgeting, readiness check
|-- hercules-mcp.json            # Example MCP client manifest
|-- pyproject.toml               # Project metadata
`-- .env.example                 # Environment configuration template
```

---

## Acknowledgements

Hercules stands on the shoulders of excellent open-source work. The stealth
browser in particular would not exist without two projects, and we are grateful
to both:

- **[agent-browser](https://github.com/vercel-labs/agent-browser)** — the Rust
  browser-control CLI and persistent daemon that gives agents an
  accessibility-first way to drive a real browser. It powers every `browser_*`
  tool in Hercules.
- **[cloakbrowser](https://github.com/CloakHQ/cloakbrowser)** — the
  fingerprint-patched stealth Chromium that lets that automation pass as a real
  user and slip past common bot detection.

Thanks also to the wider ecosystem Hercules builds on:
[Kali Linux](https://www.kali.org/), the
[Metasploit Framework](https://www.metasploit.com/),
[ProjectDiscovery](https://projectdiscovery.io/) (nuclei, httpx, dnsx),
[SecLists](https://github.com/danielmiessler/SecLists),
[FastMCP](https://github.com/jlowin/fastmcp), and
[Textual](https://textual.textualize.io/).

---

## Security

Hercules is intended for authorized penetration testing, security research, CTF competitions, and lab environments. Use it only against systems where you have explicit permission.

---

## License

[MIT](LICENSE)
