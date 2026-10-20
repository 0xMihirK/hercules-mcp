---
name: hercules-mcp
description: Route authorized penetration testing, security research, CTF, forensics, browser testing, vulnerability validation, and lab work through the Hercules MCP server. Use when choosing or sequencing Hercules reconnaissance, Nmap/NSE, web scanning, Nuclei, browser, Metasploit, password, CTF, shell, workspace, job, artifact, or session tools.
---

# Hercules MCP

Use Hercules as a staged security workflow, not as a bag of unrelated commands.

## Install, update, or recover

Use the repository's `install.md` and absolute `hercules-setup` launcher.
Identify the current client explicitly; never infer it from installed executables.
Run `status` first, then the authorized `install`, `repair`, or `resume` operation
for only that client. Preserve existing capabilities, configuration, and evidence.
New installs default to full capabilities. Do not move a live virtual environment.

Host setup and cold `verify` never start a container or call `shell_exec`.
Ask separately before `runtime prepare` downloads/builds or `verify --runtime`.
The runtime is one full Kali image; selections hide tools, not packages.
`auto` pulls the published digest (GHCR, then the Docker Hub mirror) or reuses a
validated cache, and never hides a pull failure. Offer `--image-source build`
(slower, builds from source) for an unpublished revision, custom trust, or offline.
If a harness denies an operation, stop that action and name the blocked phase;
do not change permission modes, add blanket allow rules, or retry another tool.
Resume only after the user resolves the denial through the harness's own controls.

Report host revision, selected-client registration/reload, runtime preparation,
host/runtime verification, and cleanup separately. A registered server may still
need a client reload; a cold connection does not establish runtime readiness.

## Establish authorization and scope

1. Confirm the target, permitted techniques, and stopping conditions before active work.
2. Treat an unconfigured target policy as permissive compatibility behavior, not authorization.
3. Start with passive or low-impact discovery. Escalate only when the request and evidence justify it.
4. Never use installation checks to scan, exploit, navigate to, or verify egress through an external target.
5. Keep secrets out of narration and tool-call summaries. Hercules redacts common secrets, but avoid echoing them.

## Select the smallest effective tool

- Call `system_start_container` only immediately before the first Docker-backed
  operation. Reuse the active container, and stop it when the work is complete.
- Inspect current or retained files with `workspace_inspect` before startup.
  Keep related challenge folders together; coordinate workers before rotation or shutdown.
- Prefer a structured Hercules tool. Use `shell_exec` only when the typed surface cannot express the operation.
- Check the tools currently exposed before planning. Optional tools may be hidden; do not invent a missing tool. The full image's inventory is separate from MCP visibility. Check the actual backend before using an authorized shell escape hatch.
- Use `network_curl` for deterministic HTTP requests. Use browser tools when JavaScript, authentication state, DOM interaction, or visual evidence matters.
- The browser is Obscura: **CSP is not enforced** and native downloads are
  unsupported (limits in [browser.md](references/browser.md)). Browsing needs the
  container's bridge/firewall/gateway and explicit IP/CIDR authorization for private
  targets; if enforcement is unavailable, stop and report it — never remove scope
  settings to proceed.
- Use installed Nmap scripts or Nuclei templates before authoring custom content.
- Use foreground calls for bounded work. Use `shell_exec_background` plus `shell_check_job` for long-running commands.
- Preserve useful evidence. Follow `raw_artifact`, `stdout_artifact`, or `stderr_artifact` paths when output is filtered or truncated.
- Treat `shell_exec`, `browser_cmd`, and raw `extra_args` as administrator escape hatches outside structured-target guarantees.

Read [tool-routing.md](references/tool-routing.md) before choosing among unfamiliar tools or selectors.
Read [parameter-reference.md](references/parameter-reference.md) before repairing a rejected call or using an unfamiliar parameter.

## Follow the operating loop

1. Discover: identify hosts, DNS, services, technologies, and reachable HTTP surfaces.
2. Focus: choose the narrowest relevant scanner, script, template, or browser path.
3. Verify: corroborate findings with a second signal and retain raw evidence when needed.
4. Escalate: exploit, brute-force, generate payloads, or start listeners only when explicitly authorized.
5. Recover: inspect timeout and partial-output fields, manage jobs or sessions, and explicitly restart the current container or create a clean stopped session when needed.
6. Report: separate observed evidence from inference, note incomplete output, and state what was not tested.

Parallelize independent passive or light probes within advertised concurrency limits. Serialize dependent scans, browser mutations in one session, credential testing, exploitation, and interactive session work. Normalize targets and reuse existing results or artifacts instead of repeating a scan.

## Use advanced workflows deliberately

- For Nmap mode choice, stock NSE selection, or custom Lua, read [nmap-nse.md](references/nmap-nse.md). Before complex custom authoring, also read `resource://agent_skills/nse`.
- For Nuclei tags/templates or custom YAML, read [nuclei.md](references/nuclei.md). Before complex custom authoring, also read `resource://agent_skills/nuclei`.
- For interactive or visual web work, read [browser.md](references/browser.md).
- For Metasploit, payloads, listeners, background jobs, and recovery, read [exploitation-and-sessions.md](references/exploitation-and-sessions.md).
- For workspace selection, paged evidence reads, retention, jobs, artifacts, and recovery, read [workspace-and-evidence.md](references/workspace-and-evidence.md).
- For CTF objectives, continuity notes, candidate validation, rate coordination, or custom tools, read [ctf-workflow.md](references/ctf-workflow.md).
- For LinPEAS, WinPEAS, PowerUp, GTFOBins, or LOLBAS selection and handling, read [post-exploitation-resources.md](references/post-exploitation-resources.md).
- For token-efficient execution, output completeness, `include_raw`, artifacts, polling, and result interpretation, read [efficiency-and-output.md](references/efficiency-and-output.md).

## Handle failures truthfully

- Treat `timed_out=true` as a timeout even when partial output exists.
- Check `terminated` before assuming the timed-out process stopped.
- Read artifacts when `output_complete=false`, `output_filtered=true`, filtering occurred, or truncation is reported. `exit_code=0` means the process completed; it does not prove a vulnerability or complete assessment.
- After container recovery or `system_start_new_session`, assume browser daemons, Metasploit clients/channels, and background processes were reset; workspace files persist.
- `runtime_not_started` means no container was created; call `system_start_container`, then retry the Docker-backed tool.
- After `system_stop_container`, call `system_start_container` to resume the same workspace. Use `system_start_new_session` only for a clean workspace.
- Before completing or abandoning work, save notes and artifacts, resolve owned jobs,
  and stop the container when no parallel worker needs it. Check `cleanup` confirmation;
  report failed/unverified cleanup, preserved stopped containers, and retained evidence separately.
