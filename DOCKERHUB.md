<img src="https://raw.githubusercontent.com/0xMihirK/hercules-mcp/main/assets/logo.svg" alt="Hercules MCP" width="160">

# Hercules MCP — Kali / Obscura runtime image

[![GitHub](https://img.shields.io/badge/GitHub-0xMihirK%2Fhercules--mcp-181717?logo=github)](https://github.com/0xMihirK/hercules-mcp)
![platforms](https://img.shields.io/badge/platforms-amd64%20%7C%20arm64-2496ED?logo=docker&logoColor=white)
![base](https://img.shields.io/badge/base-Kali%20Linux-557C94?logo=kalilinux&logoColor=white)
![license](https://img.shields.io/badge/license-MIT-F57C00)

This is the container **runtime image** for **[Hercules MCP](https://github.com/0xMihirK/hercules-mcp)** — a Python FastMCP server that gives terminal-capable AI agents a structured [Model Context Protocol](https://modelcontextprotocol.io) interface to security tooling running inside an owned Kali Linux container.

The image bundles a full Kali Linux security toolkit plus the **Obscura** headless browser backend. The Hercules MCP server (installed on your host) drives this container over `docker exec`, keeps evidence in managed host workspaces, and returns bounded, filtered results to the agent.

> **This image is not a standalone app — do not `docker run` it directly.** It is pulled automatically by the Hercules MCP installer and driven by the MCP server. Start here: **https://github.com/0xMihirK/hercules-mcp**

## Install (recommended)

Give this prompt to any terminal-capable AI agent (e.g. Claude Code):

```text
Install or update Hercules MCP using https://github.com/0xMihirK/hercules-mcp/blob/main/install.md. Configure only this agent. Host install needs no container; if a container step is denied, stop and tell me how to approve it. Report the result.
```

The installer prepares the host, registers the MCP server, and pulls this image for you via `hercules-setup runtime prepare` — **GHCR first, Docker Hub as the identical-digest fallback**. Full guide: **[install.md](https://github.com/0xMihirK/hercules-mcp/blob/main/install.md)**.

## Images

| Registry | Reference |
| --- | --- |
| GitHub Container Registry (primary) | `ghcr.io/0xmihirk/hercules-mcp` |
| Docker Hub (mirror) | `0xmihirk/hercules-mcp` |

- **Platforms:** `linux/amd64`, `linux/arm64`
- Pulls are **pinned to an immutable digest** and revalidated after tagging — a mutable tag is never treated as trust.
- Each published digest carries **Sigstore build-provenance attestation**.

```bash
# The installer pulls the verified digest for you. For reference (amd64):
docker pull ghcr.io/0xmihirk/hercules-mcp@sha256:05d6c0b9243f59fccf3dbe126708bea76fc5da6e21c5fcdddf4010971fceb99e
```

## What's inside

A full Kali toolkit exposed through typed MCP tools, grouped into capability bundles:

- **Recon** — dns (dig/dnsx), whois, amass
- **Network** — nmap (+ NSE authoring), curl, ncat, hping3
- **Web** — httpx/whatweb/wafw00f/nikto/wpscan/arjun, ffuf/gobuster, dalfox/commix, nuclei, sqlmap
- **Exploitation** — searchsploit, Metasploit Framework
- **Cracking** — hydra, john (with SecLists / rockyou)
- **CTF / forensics** — binwalk, steghide, exiftool
- **Browser** — the Obscura headless browser behind a scope-enforcing, container-local SOCKS gateway and firewall

Capability selection controls which MCP tools are *exposed*; the image itself always contains the full inventory.

## Architecture

![Hercules MCP architecture](https://raw.githubusercontent.com/0xMihirK/hercules-mcp/main/assets/architecture.png)

## Security and licensing

- For **authorized** security testing, CTFs, and research only — you are responsible for scope and authorization.
- The image redistributes Kali packages, Metasploit, nuclei, SecLists, Obscura / agent-browser, and other tools under their respective licenses.
- Hercules MCP source is **MIT**-licensed. See the **[repository](https://github.com/0xMihirK/hercules-mcp)** for the install guide, the runtime/security model, and details.
