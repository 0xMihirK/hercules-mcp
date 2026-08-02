<p align="center">
  <img src="assets/logo.svg" alt="Hercules MCP" width="220" style="margin-bottom: 20px;"/>
</p>

<h1 align="center">Hercules MCP</h1>

<p align="center">
  <em>Containerized offensive-security workflows for AI agents through the Model Context Protocol</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://badge.mcpx.dev?status=on" alt="MCP enabled" />
  <img src="https://img.shields.io/badge/Docker-Kali_Linux-2496ED?logo=docker&logoColor=white" alt="Docker and Kali Linux" />
  <img src="https://img.shields.io/badge/license-MIT-F57C00" alt="MIT license" />
</p>

Hercules MCP is a Python FastMCP server that gives terminal-capable AI agents a
structured interface to security tools running in an owned Kali Docker
container. It keeps session evidence in managed host workspaces and returns
bounded, agent-friendly results without hiding whether output was filtered,
truncated, or interrupted.

> **Authorized use only.** Run Hercules only against systems for which you have
> explicit permission. Installation and verification are local and
> non-destructive; they must not scan, exploit, navigate to, or check public
> egress against an external target.

<p align="center">
  <img src="assets/architecture.png" alt="Hercules MCP architecture" width="720" />
</p>

## Contents

- [Install with your AI agent](#install-with-your-ai-agent)
- [Capabilities and MCP surface](#capabilities-and-mcp-surface)
- [How Hercules works](#how-hercules-works)
- [Headless browser automation](#headless-browser-automation)
- [Output, artifacts, sessions, and workspaces](#output-artifacts-sessions-and-workspaces)
- [MCP resources and agent guidance](#mcp-resources-and-agent-guidance)
- [Manual CLI and client reference](#manual-cli-and-client-reference)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Security model](#security-model)
- [Acknowledgements](#acknowledgements)
- [License](#license)

## Install with your AI agent

Paste this prompt unchanged into any terminal-capable coding agent. It is the
same prompt for Windows, macOS, and capable Linux distributions:

```text
Install or upgrade Hercules MCP from https://github.com/0xMihirK/hercules-mcp using https://github.com/0xMihirK/hercules-mcp/blob/main/install.md as guidance. Adapt the installation to my operating system, shell, available package manager, Docker environment, and current terminal-capable AI agent instead of assuming a particular platform. Before a first install, ask what I intend to use Hercules for and whether I want every capability or a smaller installation. If I choose a smaller installation, inspect Hercules’ capability catalog, use your judgment to recommend the minimum useful set, briefly explain important omissions, and get my confirmation before installing. Also ask whether configuration should be user-wide or project-local, and ask about a browser proxy only if browser capability is selected. Preserve my confirmed capability selection, `.env`, secrets, workspace evidence, downloaded assets, and client settings during upgrades unless I explicitly change them. Install the portable skill and an appropriate native adapter, register the secret-free Hercules STDIO MCP server, and run local non-destructive verification. Never print secrets, scan or navigate to an external target during setup, or silently perform privileged system changes; clearly tell me when a prerequisite or manual action is required.
```

The detailed, authoritative installation contract is [install.md](install.md).
The agent should inspect the actual host instead of assuming a package manager,
shell, init system, CPU architecture, or Docker implementation. Hercules never
silently performs privileged package, daemon, service, or group-membership
changes.

### What the installer asks

On a first installation, the agent and installer:

- detect the operating system, Docker context, architecture, and supported MCP
  client;
- ask what Hercules will be used for, inspect the capability catalog, and
  recommend the smallest useful profile;
- ask whether configuration is user-wide or project-local, defaulting to
  user-wide;
- ask about a browser proxy only when the browser bundle is selected;
- build and validate the selected image before committing configuration; and
- install the provider-neutral portable skill independently from an MCP-only
  native adapter for Codex, Claude Code, or Cursor when supported.

Native plugin manifests do not embed or declare skills. Other Agent Skills or
STDIO MCP clients receive the same portable skill and a secret-free manual MCP
configuration. Upgrades preserve the selected capabilities, `.env`, generated
secrets, workspace evidence, downloaded assets, scope, proxy preference, and
client settings unless the operator explicitly changes them.

### Prerequisites

- Git
- [`uv`](https://docs.astral.sh/uv/)
- a working Docker Engine, Docker Desktop, or compatible Docker context

The installer uses Python 3.12 through `uv`. It may explain a missing
prerequisite, but it will not silently perform an administrator-level system
change.

## Capabilities and MCP surface

Hercules installs capability bundles, not a single all-or-nothing image. The
confirmed selection controls both the binaries placed in the Kali image and the
MCP schemas registered with the client. Core shell, session, and workspace
services are always present.

| Profile | Registered tools | Resources |
| --- | ---: | ---: |
| Full, including Metasploit | 45 | 7 |
| Full, with `SKIP_METASPLOIT=true` | 40 | 7 |
| Custom selection | Fewer, based on installed bundles and hidden tools | 7 |

The live catalog is the source of truth:

```text
hercules-install catalog --json
```

| Group | Capability keys | Primary functionality |
| --- | --- | --- |
| Core | `shell`, `session`, `workspace` | Foreground/background commands, lifecycle, network information, and binary-safe files |
| Reconnaissance | `dns`, `whois`, `amass` | DNS and WHOIS queries, subdomain and ASN enumeration |
| Network | `nmap`, `curl`, `ncat`, `hping3` | Port/service/NSE scanning, HTTP requests, sockets/listeners, and packet crafting |
| Web | `whatweb`, `fuzz`, `webvuln`, `nuclei`, `sqlmap` | Fingerprinting, content discovery, injection checks, templates, and SQL injection workflows |
| Exploitation | `searchsploit`, `metasploit` | Exploit-DB lookup, modules, sessions, listeners, and payload generation |
| Passwords | `hydra`, `john` | Authorized online credential testing and offline hash cracking |
| Forensics and CTF | `binwalk`, `steghide` | Firmware/file carving, metadata, and steganography workflows |
| Browser | `browser` | All ten structured `browser_*` tools, screenshots, sessions, and loopback streaming |

Bundles keep consolidated APIs intact: Nmap includes its NSE authoring tools,
Nuclei includes template authoring, and browser support includes every browser
tool. SecLists and rockyou are provisioned only when selected capabilities need
them. `HERCULES_DISABLED_TOOLS` can independently hide installed tools, but it
does not install an omitted binary.

## How Hercules works

1. The MCP client starts the global `hercules` STDIO executable.
2. Hercules loads the protected managed `.env`, selected capability catalog,
   target policy, and active workspace.
3. A typed MCP call is validated and routed to a generation-bound service.
4. The command runs inside the owned capability-specific Kali container.
5. Output is sanitized and bounded while complete evidence is retained in the
   managed workspace when necessary.

Each session uses an eight-character hexadecimal ID and an owned manifest.
Container replacement resets browser daemons, Metasploit clients, channels,
background processes, and other generation-bound state while preserving host
workspace evidence. An operator-requested stop remains terminal until an
explicit new session is started.

Target policies apply to structured DNS, WHOIS, HTTP, scanner, redirect,
browser, and Metasploit routes. Hostnames are normalized and resolved while
scoping is active, every returned address is checked, and deny rules win. The
default remains permissive until `ALLOWED_TARGETS` or `BLOCKED_TARGETS` is
configured.

## Headless browser automation

The optional browser bundle combines
[agent-browser](https://github.com/vercel-labs/agent-browser) with
[cloakbrowser](https://github.com/CloakHQ/cloakbrowser). Agents can open pages,
read accessibility snapshots, interact with controls, wait for dynamic state,
run page JavaScript, manage sessions, and capture screenshots through structured
tools.

- Browser sessions always run headlessly. Screenshots and loopback-only live
  streaming remain available.
- `browser_screenshot` validates the PNG and returns native MCP `ImageContent`;
  annotation and legacy base64 metadata are optional.
- Proxy precedence is `browser_open(proxy=...)`, then `BROWSER_PROXY_URL`, then
  direct host egress. HTTP, HTTPS, SOCKS5, and SOCKS5H are supported, and proxy
  credentials are redacted from responses and logs.
- When a proxy is active, non-proxied WebRTC UDP is blocked by default.
- Launch-affecting proxy, locale, or timezone changes relaunch the selected
  session instead of silently reusing an incompatible daemon.

Docker does not provide residential or ISP egress; direct container traffic
normally shares the host's public IP. Operators who require different egress
must supply an authorized proxy. Fingerprint reduction, profile consistency,
and proxying can reduce obvious automation signals, but Hercules cannot
guarantee CAPTCHA or bot-detection avoidance.

Use structured browser tools first. `browser_cmd` is an administrator escape
hatch for supported advanced controller operations and is outside structured
target guarantees. Load `browser_skill` before using it.

## Output, artifacts, sessions, and workspaces

Hercules optimizes output for agents without treating discarded text as
evidence:

- terminal controls and exact known banners are removed conservatively;
- scanner-specific compaction applies only to characterized stdout noise;
- stderr warnings, errors, tracebacks, and completeness diagnostics are kept;
- each stream is bounded to 8,000 inline characters by default, with a 12,000
  character combined response budget;
- timeout results report `timed_out`, `terminated`, and partial-output state;
- `output_complete` describes the inline response, while `evidence_complete`
  says whether complete raw evidence remains inline or in a verified artifact;
  and
- structured Nmap, Nuclei, ffuf, httpx, and browser data replaces duplicated
  raw text when parsing succeeds.

Workspace paths reject traversal, alternate drives, device paths, and symlink
or reparse-point escapes. Large reads support `offset` and `max_bytes` paging.
Evidence retention is disabled by default; non-empty evidence is not silently
deleted.

```text
hercules-workspace list --json
hercules-workspace pin <session-id>
hercules-workspace unpin <session-id>
hercules-workspace prune --older-than 30 --max-sessions 20
hercules-workspace prune --older-than 30 --max-sessions 20 --apply
hercules-workspace migrate --destination <durable-path>
```

Pruning is report-only without `--apply` and always protects active, pinned,
unowned, and running-job sessions. Migration stages and verifies copied files;
the source is retained unless `--delete-source` is explicitly supplied.

## MCP resources and agent guidance

The independently installed [`hercules-mcp` skill](skills/hercules-mcp/SKILL.md)
teaches agents how to choose structured tools, stage work, use bounded
parallelism, recover artifacts, and avoid unnecessary calls. Detailed references
are loaded only when needed to reduce always-on context cost.

Hercules exposes seven MCP resources:

| Resource | Use it when |
| --- | --- |
| `resource://agent_skills/nse` | Installed NSE scripts cannot express an authorized protocol or check; read it before custom Lua authoring |
| `resource://agent_skills/nuclei` | Installed Nuclei templates or tags cannot express the required detection; read it before custom YAML authoring |
| `resource://post_exploitation/linpeas` | An authorized Linux shell needs broad local enumeration; this is an embedded lite variant |
| `resource://post_exploitation/winpeas` | An authorized Windows command shell needs broad local enumeration |
| `resource://post_exploitation/powerup` | An authorized PowerShell shell needs focused service or registry follow-up |
| `resource://post_exploitation/gtfobins` | Linux evidence identifies an exact sudo, SUID, or capability-enabled binary |
| `resource://post_exploitation/lolbas` | Windows evidence identifies an exact signed binary, script, library, or component |

Prefer installed NSE scripts and Nuclei templates before writing custom content.
Do not load large post-exploitation resources speculatively. Enumeration output
is evidence to verify, not permission to exploit a finding.

## Manual CLI and client reference

The universal prompt is the recommended installation path. These commands are
useful for explicit or automated operation:

```text
# Inspect bundles before a first install
uvx --python 3.12 --from git+https://github.com/0xMihirK/hercules-mcp.git hercules-install catalog --json

# Interactive first install; the installer asks for a confirmed profile
uvx --python 3.12 --from git+https://github.com/0xMihirK/hercules-mcp.git hercules-install install --client auto

# Fresh unattended installation requires an explicit selection
uvx --python 3.12 --from git+https://github.com/0xMihirK/hercules-mcp.git hercules-install install --client auto --scope user --capabilities all --non-interactive

# Installed-checkout operations
hercules-install upgrade --client auto
hercules-install check --json
hercules-install check --runtime-only --json
hercules-install doctor --json
```

Use `--capabilities core` or confirmed comma-separated catalog keys for a
smaller profile. `--exclude-capabilities key,key` removes optional bundles from
the selected base, and `--rebuild` forces a clean image build. Upgrades preserve
the installed selection unless new capability flags are explicitly supplied.

The generated generic STDIO MCP configuration is path-independent and contains
no secrets:

```json
{
  "mcpServers": {
    "hercules": {
      "command": "hercules",
      "args": []
    }
  }
}
```

Runtime preferences and secrets remain in the managed checkout's protected
`.env`. See the complete [configuration template](.env.example); commonly
operated settings are:

| Variable | Purpose |
| --- | --- |
| `HERCULES_INSTALLED_CAPABILITIES` | Installer-managed capability selection |
| `HERCULES_DISABLED_TOOLS` | Independently hide an installed MCP tool |
| `ALLOWED_TARGETS` / `BLOCKED_TARGETS` | Structured target policy; deny rules win |
| `HERCULES_WORKSPACE_ROOT` | Override the managed evidence root |
| `HERCULES_LISTENER_PORTS` | Explicit reverse-listener ports exposed by bridge networking |
| `BROWSER_PROXY_URL` | Default browser proxy; credentials stay outside client configuration |
| `BROWSER_STREAM_PORT` | Optional loopback-only browser stream port |
| `SKIP_METASPLOIT` | Omit the five Metasploit tools from an installed full profile |

## Troubleshooting

Start with structured diagnostics rather than deleting state or rebuilding
blindly:

```text
hercules-install check --json
hercules-install check --runtime-only --json
hercules-install doctor --json
```

`doctor` distinguishes missing Git, `uv`, or Docker; a stopped daemon; an image
or capability mismatch; failed readiness; missing skills; MCP registration
failure; and tool/resource count mismatches. If repair requires administrator
access, follow the smallest host-specific action it reports and rerun the check.

For a confirmed stale or failed image build:

```text
hercules-install install --rebuild --capabilities all
```

The installer builds through a private minimal context and labels the image with
its exact source and capability fingerprint. A raw `docker build` does not
produce the same readiness metadata. Persistent Kali download failures usually
indicate the host's DNS, proxy, VPN, certificate, or Docker-network path rather
than an MCP registration problem.

## Development

The compatibility-sensitive implementation is organized around these areas:

```text
hercules/
|-- main.py                  # FastMCP entrypoint and declarative registration
|-- core/                    # Configuration, workspaces, lifecycle, execution, jobs
|-- installer_support/       # Platform, image, asset, and atomic-state services
|-- output/                  # Terminal rendering, filters, redaction, truncation
|-- tools/                   # Structured MCP tools, including browser operations
`-- resources/               # MCP resource registration and embedded lite scripts
skills/hercules-mcp/         # Canonical provider-neutral portable skill
docker/entrypoint.sh         # Container readiness and loopback-only services
Dockerfile                   # Selective Kali capability image
install.md                   # Authoritative adaptive installation contract
```

Useful local checks are:

```text
uv sync
uv run python -m compileall hercules
uv build --offline
git diff --check
```

Maintainers who have the separate local-only suite also run
`uv run python -m unittest discover -s tests`. Local tests, vulnerable fixtures,
acceptance evidence, `.env`, workspaces, wordlists, and distributions are
ignored or excluded as appropriate. The `tests/` directory remains untracked
and neither the wheel nor source distribution contains it.

## Security model

- The Kali container runs powerful root-level security tooling. Docker is a
  containment boundary, not a substitute for host hardening or authorization.
- Metasploit RPC and browser-stream ports bind to host loopback. Explicitly
  configured reverse-listener ports remain externally reachable so callbacks
  can work.
- Secrets, cookies, tokens, form values, and proxy credentials are redacted from
  display metadata while the invoked process still receives the original value.
- `shell_exec`, `browser_cmd`, and documented raw `extra_args` fields are trusted
  administrator escape hatches outside structured target guarantees.
- Empty target policy is intentionally permissive for backward compatibility;
  configure allow and deny scopes before using Hercules in controlled
  environments.
- `pymetasploit3` remains pinned despite
  [GHSA-qpc3-8vqg-8g6w](https://osv.dev/vulnerability/GHSA-qpc3-8vqg-8g6w)
  because no fixed release exists. Hercules does not call the affected API and
  rejects CR/LF in Metasploit option keys and values.

## Acknowledgements

Hercules builds on
[Kali Linux](https://www.kali.org/),
[FastMCP](https://github.com/jlowin/fastmcp),
[Metasploit Framework](https://www.metasploit.com/),
[ProjectDiscovery](https://projectdiscovery.io/),
[SecLists](https://github.com/danielmiessler/SecLists),
[agent-browser](https://github.com/vercel-labs/agent-browser), and
[cloakbrowser](https://github.com/CloakHQ/cloakbrowser). Thank you to their
maintainers and contributors.

## License

Hercules MCP is distributed under the [MIT License](LICENSE).
