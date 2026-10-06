# Source analysis behind the showcase

Reviewed the 82 tracked source, documentation, configuration, and test files
(22,328 lines at revision `e0c3819`), excluding generated files, lockfiles,
binary assets, and SVG artwork. These conclusions drive the public copy.

| Area | Implementation and behavior |
| --- | --- |
| Transport | `hercules/server.py`: local FastMCP over STDIO; discovery does not start Docker. |
| Lifecycle | `hercules/core/docker_manager.py`: explicit start creates/reuses an owned runtime; intentional stop stays stopped. |
| Ownership | Docker manager, orphan guardian and cleanup: exact process/session ownership, per-client resources, guarded cleanup. |
| Evidence | Docker manager and output parser: bounded inline results, structured records for supported backends, overflow files, distinct output/evidence completeness. |
| Workspace | Host-backed session storage, bounded chunk reads, explicit writes, files retained beyond container stop. |
| Capabilities | Tool catalog, capability runtime, Docker build: one catalog controls MCP tools, selected binaries, verified manifests. |
| Surface | Full profile: 46 tools, 22 bundles, eight categories, seven resources. Without Metasploit: 41 tools. Three core bundles are mandatory. |
| Installation | `install.md`, bootstrap/configuration code and tests: inspect existing state, preserve configuration/evidence, use an absolute STDIO launcher, verify locally, clean transaction-owned resources. |
| Scope | Structured tools support checks. Permissive defaults and raw command escape hatches mean scope is not a universal boundary. |
| Browser | agent-browser with CloakBrowser Chromium, named sessions, snapshots, actions, screenshots. Fingerprint injection is rejected. No bot-detection/CAPTCHA guarantee. |
| Custom checks | NSE writing does not mutate the global script database. Writing Nuclei YAML does not validate it. |
| Tests | Substantiate lifecycle, ownership/concurrency, workspace contracts, validation, catalog and parsers. No benchmark evidence for performance or token-saving marketing claims. |

Counts and the complete install prompt are derived during every build.
Workflow, terminal and evidence examples are marked illustrative. The website
does not call Hercules from a browser or claim guaranteed isolation.
