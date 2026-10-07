# Native recording provenance

The site plays unmodified terminal output from pinned agents running in disposable
Docker containers. The interfaces, menus, logos, progress indicators, task updates,
tool cards, streaming and timestamps are emitted by the clients themselves.

| Client | Native version | Renderer |
| --- | --- | --- |
| Claude Code | 2.1.292 | Standard conversation; alternate screen disabled |
| Codex | 0.160.1 | Native default TUI |
| OpenCode | 1.18.35 | Native default TUI |
| Hermes | 0.21.5; `f97608f178d1ffeca59860195ab7da295f7c8e5f` | Recommended modern `--tui` |

Model responses, authored investigation decisions, response delays and usage
counters are scripted. **Tool results are real.** No paid model calls or personal
accounts are used. Claude uses its Foundry configuration against a loopback
Messages endpoint with credential lookup disabled; the other clients use local
Responses or OpenAI-compatible endpoints.

Each of ten investigations has captures at 120×36, 80×28 and 48×28 for every
client: 120 recordings. They cover network inventory, service assessment,
website assessment, TLS and redirects, a browser login workflow, layered
forensics, a web CTF, evidence reconciliation, background-job recovery and
remediation rechecks. Each requires 8–16 meaningful Hercules calls and a verified
Markdown/HTML report. The CTF derives its password from PCAP clues, inspects an
appended archive, rejects an incorrect key and a decoy, and verifies the flag
digest. No solver is planted in the workspace.

Agents receive fresh configuration and an allowlisted environment. A private
relay connects their STDIO bridges to separate host-side Hercules processes.
Agents receive no host Docker socket or personal configuration. Hercules starts
actual Kali runtimes on transaction-owned internal Docker networks. The only
targets are local fixtures; no public target is contacted. Networking, privileges
and selected capabilities are controlled by the operator. Docker containment is
not an unconditional security boundary.

The player preserves original ANSI, CR, LF, grid dimensions and 1× timing. It
reconstructs the first native frame before replacing the previous display, scales
uniformly and serializes writes. Geometry changes map between corresponding
milestones. Completed reports remain for six seconds. Cases use a shuffle bag;
agent switching keeps the case. There is no keyboard takeover or live-agent claim.

Fallback PNG/JPEG images are actual Chromium screenshots of the captured ANSI rendered in
xterm 6 with IBM Plex Mono and Unicode 11. They contain no authored terminal UI.
Reduced motion starts still; visitors can explicitly play. Hidden and offscreen
players pause. Transcripts, evidence files and actual reports remain downloadable.

`assets/recordings/manifest.json` records versions, native commands, capture
configuration, image identity, source commit, actual MCP schema snapshot, SHA-256
hashes, milestones, result excerpts, artifact availability and measured output
counts. Approximate token counts are `ceil(characters / 4)` and are not tokenizer
measurements. Character comparisons include the whole structured inline response,
including metadata. Bounding and semantic filtering are identified separately;
some small outputs become larger after metadata is added.

Validation rejects missing evidence, unexpected branches, tool sequences, artifact
hash mismatches and incomplete transaction cleanup. A blocked client is unavailable;
its interface is never replaced by a replica. Docker is required for capture only.
Visitors receive static assets.

See [capture reproduction](capture/README.md) and [lab programs](capture/labs/cases.py).
