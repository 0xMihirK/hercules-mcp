---
name: hercules-install
description: Adaptively install or upgrade Hercules MCP, a selected Kali capability image, the portable skill, and an STDIO client adapter.
---

# Hercules MCP installation

Use this document as an outcome contract, not as a platform-specific command
script. Inspect the real host and adapt native commands to its operating system,
shell, CPU architecture, package manager, Docker context, and current
terminal-capable AI agent. Never assume apt, systemd, or a POSIX shell on
Windows.

## Required outcomes

- Git, `uv`, Python 3.12 through `uv`, and a working Docker-compatible CLI and
  daemon are available.
- Hercules lives in its durable platform data directory and is installed as an
  editable `uv tool` from the managed checkout with the frozen requirements
  export.
- The confirmed capability profile is built and validated before `.env`,
  installer state, skills, or client registration are committed.
- The provider-neutral `hercules-mcp` skill is installed independently from the
  appropriate MCP-only client adapter. Native plugins do not declare skills,
  and the `hercules` STDIO server is registered without secrets or a
  checkout-relative working directory.
- Verification is local and non-destructive. Installation never scans,
  navigates to, exploits, or checks public egress against an external target.

Do not silently install privileged packages, start or alter system services,
change group membership, or weaken Docker security. If the host needs one of
those actions, explain the smallest exact user/admin step and pause.

## First installation

Before running the install, ask what the user intends to use Hercules for and
whether they want every capability or a smaller installation. Inspect the live
catalog rather than relying on a copied list:

```text
uvx --python 3.12 --from git+https://github.com/0xMihirK/hercules-mcp.git hercules-install catalog --json
```

Use judgment to recommend the smallest useful bundle set. Mention important
omissions briefly—for example, browser workflows require `browser`, NSE work is
included with `nmap`, and Metasploit tools require `metasploit`. Core shell,
workspace, and lifecycle capabilities are mandatory. Obtain confirmation.

Also ask whether configuration is user-wide or project-local (default:
user-wide). Ask about a browser proxy only when `browser` is selected. Read proxy
credentials through hidden input and keep them only in the protected `.env`.

Then run one adapted equivalent of:

```text
uvx --python 3.12 --from git+https://github.com/0xMihirK/hercules-mcp.git hercules-install install --client auto --scope user --capabilities nmap,nuclei,browser
```

Use `--capabilities all` for a full installation or `core` for only mandatory
services. `--exclude-capabilities key,key` may refine an explicit/all base.
Fresh unattended installs intentionally fail unless a capability selection is
explicit. Interactive `hercules-install install` can instead ask all/custom.

The compatibility `--metasploit enabled|disabled` switch is accepted for one
release and is translated into the capability selection.

## Success checkpoint

Run:

```text
hercules-install check --json
hercules-install check --runtime-only --json
```

Success reports the installed and omitted capabilities, immutable image tag and
fingerprint, required wordlists (or `not_required`), actual and expected MCP
tool counts, and seven resources. Full profiles remain 45 tools with Metasploit
or 40 without it; custom profiles correctly expose fewer. Restart the AI agent
after client registration so it reloads the MCP server and skill.

## Upgrades and reconfiguration

Use:

```text
hercules-install upgrade --client auto
```

Upgrades preserve the confirmed capabilities, `.env`, generated RPC secret,
proxy preference, independently disabled tools, workspace evidence, downloaded
assets, unknown non-secret installer state, and client settings. They do not
repeat first-run questions. Supply `--capabilities ...` only when the user
explicitly wants to reconfigure; add `--rebuild` to force a clean image build.

The managed checkout updates only by a clean fast-forward. If nonignored tracked
or untracked changes or divergent history exist, do not overwrite them: report
the checkout and let the user preserve, commit, move, or intentionally ignore
the changes. Ignored `.env`, wordlists, and workspaces do not make it dirty.
Older capability images are retained and are never deleted automatically.

## Adaptive prerequisite handling

Prefer the host's native, supported installation path and official prerequisite
documentation:

- `uv`: <https://docs.astral.sh/uv/getting-started/installation/>
- Git: <https://git-scm.com/downloads>
- Docker: <https://docs.docker.com/get-started/get-docker/>

On Windows use native PowerShell and support paths with spaces and Docker
Desktop/compatible contexts. On macOS account for Intel or Apple Silicon. On
Linux inspect `/etc/os-release`, architecture, WSL, package-manager availability,
PID 1/init system, Docker context, and rootless mode; do not infer systemd merely
because `systemctl` is installed. Unknown distributions receive official/manual
guidance rather than guessed commands. Podman-only support is not claimed unless
its Docker API/CLI compatibility has been separately validated.

## Diagnostics

Run `hercules-install doctor --json`. Use its sanitized platform and component
codes directly:

- missing Git, uv, or Docker: provide the official host-appropriate prerequisite;
- unreachable Docker daemon: identify the current context/rootless/init setup
  and request the necessary user action;
- missing/stale image: rerun `hercules-install install --rebuild` with the saved
  capability selection;
- missing required wordlists: rerun `hercules-install install`;
- MCP count/startup, skill, manifest, or adapter failure: repair only the
  reported component, then repeat both checks.

Never print configuration snapshots, proxy URLs, passwords, tokens, or cookies.
The Metasploit secret is generated and preserved inside `.env`; it does not
belong in installer state or MCP client configuration.

## State locations

The installer discovers native paths and reports them in `doctor --json`:

- Windows: `%LOCALAPPDATA%\hercules-mcp` data and `%APPDATA%\hercules-mcp`
  configuration;
- macOS: `~/Library/Application Support/hercules-mcp` data and
  `~/Library/Preferences/hercules-mcp` configuration;
- Linux: `${XDG_DATA_HOME:-~/.local/share}/hercules-mcp` data and
  `${XDG_CONFIG_HOME:-~/.config}/hercules-mcp` configuration.

New managed workspaces live under the platform data root. Existing checkout
workspaces are not moved automatically. Use `hercules-workspace list --json`,
dry-run pruning, and explicit migration when the operator chooses to manage old
evidence.
