# Native capture harness

The Docker image installs Claude Code 2.1.291, Codex 0.147.0, OpenCode 1.18.34,
and Hermes classic revision `3f524a2459efe4ab32061c418e309e5da1a931fd`.
`record.py` records their unmodified interactive interfaces through a real PTY.
It records output bytes and monotonic timestamps; it does not draw terminal UI.
The PTY driver uses a VT screen reader to wait through native onboarding. Codex
and Hermes get an additional startup wait before their MCP inspection command.
Codex uses `/mcp`; Hermes uses `/tools list` to show its loaded Hercules tools.

Export the current Hercules tool/resource schemas using a Python environment
with the repository dependencies installed, then build the capture image:

```sh
python website/capture/export_surface.py
docker build -t hercules-showcase-capture:20261007 website/capture
python website/capture/run.py --smoke --cols 120
python website/capture/run.py
python website/capture/publish.py
```

`run.py` accepts `--client`, `--scenario`, and `--cols` for individual recordings.
Each run creates a fresh home directory inside a disposable container. It mounts
only the read-only harness and an output directory. No host agent configuration,
credentials, Docker socket, or workspace is mounted. Capture containers use
`--network none`, drop Linux capabilities, and prohibit privilege escalation.
Network access is needed to build the image, then only loopback is available.

`fixtures.py` serves the actual exported Hercules schemas over STDIO MCP and
scripted model responses over a local HTTP endpoint. Model/tool delays and
findings are authored examples. The native clients produce their own progress
indicators, task lists, tool cards, menus, and animation frames at normal speed.
The scan example never contacts `scanme.nmap.org`; the web example uses the
fictional `shop.lab.test`. Container startup is also a scripted tool result.

Claude uses its documented credential-free Foundry gateway configuration:
`CLAUDE_CODE_USE_FOUNDRY`, `ANTHROPIC_FOUNDRY_BASE_URL`, and
`CLAUDE_CODE_SKIP_FOUNDRY_AUTH`. Codex uses a Responses provider with
`requires_openai_auth = false`. OpenCode uses an OpenAI-compatible provider;
Hermes uses its custom provider. All provider URLs point to loopback.
Codex's native code-mode executor receives scripted JavaScript that calls the
actual discovered MCP tools and its built-in planning tool.

References: [Claude Foundry](https://code.claude.com/docs/en/microsoft-foundry),
[Codex provider source](https://github.com/openai/codex/blob/be6e8eac029b183056b7e4402879f15d2c85f61b/codex-rs/model-provider-info/src/lib.rs),
[OpenCode providers](https://opencode.ai/docs/providers/#ollama),
[Hermes custom providers](https://hermes-agent.nousresearch.com/docs/integrations/providers#custom--self-hosted-llm-providers).

Raw casts, diagnostic text, and model requests stay under ignored
`website/test-results/`. `publish.py` requires all 24 sessions to complete their
Hercules lifecycle, operation, evidence read, and report write. It copies only
validated `.cast` files and a provenance manifest into `assets/recordings/`.
Startup/login failures are diagnostic captures, never substitute demonstrations.
Docker is needed only to capture; visitors receive static files.

The manifest's `reproductionImage` identifies the final reproducible image.
Some initial captures used the same pinned client binaries before adding the
driver-only `pyte` dependency: image
`sha256:517e4a41bca9e8f96a80b53995731781a064aa051f771af007a4e06b52de3e83`.
The final image is
`sha256:809f361c6dc3f36ec2324074cc100d76cd8fe16b52ef0648ba4bdec2c5ab632d`.
Neither image modifies client source. Per-recording hashes cover every raw cast.
Hermes's native banner says `vunknown` because the pinned shallow checkout has
no release tags; the manifest records its exact Git revision.
