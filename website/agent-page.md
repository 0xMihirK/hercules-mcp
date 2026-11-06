# Hercules MCP

A Kali workspace for your AI agent. Hercules exposes structured security tools and Obscura browser automation through a local STDIO MCP server. A client explicitly starts its own Kali Docker runtime, and evidence is retained in a host workspace.

Website: https://0xmihirk.github.io/hercules-mcp/

## How it works

1. Connect a compatible MCP client. Connection exposes tools and resources without creating a container.
2. Call `system_start_container` when a Docker-backed task is needed. Repeated starts reuse the current session's runtime.
3. Use the relevant structured tool or `shell_exec`, save complete evidence in the owned workspace, and verify findings against controls.
4. Coordinate with other workers, then call `system_stop_container` when the runtime is no longer needed. A new session has a new workspace; earlier evidence remains inspectable.

## What agents can do

- Map hosts and services with DNS, Amass, Nmap, Ncat, and protocol checks.
- Investigate web applications and APIs with HTTP, browser, fuzzing, Nuclei, and SQL injection tools.
- Research exploit leads with SearchSploit and optional Metasploit tools; verify affected versions and prerequisites.
- Examine files, firmware, and binaries with workspace tools, Binwalk, metadata utilities, and shell-accessible binutils.
- Test authorized credentials and inspect hashes with Hydra and John the Ripper.
- Use the packaged agent skills for tool choice, evidence handling, and focused testing workflows.

## Install or update

Read the [canonical installation guide](https://github.com/0xMihirK/hercules-mcp/blob/main/install.md). Identify the current client, run the setup CLI's read-only status check, and configure only that client. Host installation, runtime image preparation, and container verification are separate steps. Before runtime preparation, ask interactively whether to use the pinned prebuilt image (recommended) or build locally from source; use chat if the harness has no question UI. Run `runtime prepare --client <client> --image-source prebuilt --yes` or `--image-source build --yes` only after the choice. A verified cached image is reused; a failed prebuilt pull never triggers a build. The [copyable agent prompt](./install.txt) gives the short entry point; [llms.txt](./llms.txt) gives concise agent instructions.

## Boundaries

Use Hercules only on authorized targets. Docker networking and privileges are operator controlled. Obscura does not enforce CSP or support browser-native downloads; use verified HTTP or workspace file transfers when a download is needed. A scanner hit or broad version match is a lead, not proof of vulnerability. Cold STDIO verification does not prove the container has run.

Source: https://github.com/0xMihirK/hercules-mcp
