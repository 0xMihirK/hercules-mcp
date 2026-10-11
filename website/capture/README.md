# Native graphical capture harness

The harness runs pinned native clients inside XTerm 379 under Xvfb. It records lossless RGB video at a requested 60 fps and unchanged ANSI output with timestamps. PNG delta atlases are checked byte for byte against decoded native graphical master frames. Actual presentation timestamps, including any capture gaps, are retained.

`record.py` configures fresh local providers, drives native MCP inspection, prompts, planning, and detail interactions, and forwards real emulator responses. It draws no terminal interface. Claude uses the documented gateway, native full-screen conversation renderer, Opus 5.5 configuration, medium effort, and auto mode. Local project trust and onboarding preferences apply only to the disposable fixture directory. OpenCode's native tool-detail action is bound through its own tui.json. Hermes uses the recommended modern TUI. Claude uses the documented `CLAUDE_CODE_NO_FLICKER=1` setting to retain the docked composer selected by the user. Cascadia Mono uses pinned Noto Sans Symbols2 and Noto Color Emoji fallbacks. The emulator uses a black/white palette and measured cell dimensions; captured pixels are never recolored by the website.

`labs/run.py` owns each fixture network, capture container, relay, and isolated host Hercules process. Hercules starts real Kali with HERCULES_DOCKER_NETWORK. Agents have no Docker socket or personal configuration. Every result, report, evidence index, and cleanup is validated. Scripted provider decisions advance only from observed results.

## Reproduce

Use the repository Python environment and working Docker. Build all three capture dependencies before recording:

```sh
docker build -t hercules-showcase-capture:20261008-pixels -f website/capture/Dockerfile website/capture
docker build -t hercules-showcase-lab:20261007 website/capture/labs
python -m website.capture.labs.sandbox --build
python -m website.capture.labs.batch --cases network --workers 1 --index pixel-fidelity-pilot-matrix.json --subnet-base 95
```

Review the twelve pilots before expanding to all ten cases:

```sh
python -m website.capture.labs.publish --development --current-only
cd website
npm run dev
```

`frame-review.html` compares the player canvas with independently decoded graphical master PNGs at native size. Matching two ANSI reconstructions is not a fidelity check. Review startup, logos, MCP inventory, native detail/menu states, task changes, progress, and reports against the native captures and supplied reference.

After pilot acceptance, capture the full matrix, validate it, and stage production assets:

```sh
python -m website.capture.labs.batch --workers 1 --index pixel-native-matrix.json --subnet-base 95
python -m website.capture.labs.publish
```

The public publisher requires 120 complete, current-harness captures, real tool validation, report artifacts, and transaction-owned cleanup. It archives existing public assets recoverably and copies the manifest last. Development bundles remain separate. Failed or unsupported clients are never replaced by authored terminal UI.

`repack.py` can regenerate delta atlases and posters from retained native masters without modifying ANSI bytes. It preserves prior bundles and restores them if packing fails. Every profile retains original capture hashes and identifies the postprocessor separately.

Run capture regressions with `python -m unittest website.capture.test_pixels website.capture.test_readiness website.capture.test_clock_guard website.capture.labs.test_program website.capture.labs.test_publish website.capture.labs.test_batch`. Run website checks with `npm test`, `npx tsc --noEmit`, and `npm run build` after a validated matrix is staged.

The independent clock guard rejects discontinuities larger than one capture frame and records cumulative clock drift separately. Failed agent containers retain exit and OOM diagnostics before ownership-checked cleanup. Playback ends after the six-second report hold, before native process teardown can clear the terminal; the original master and raw ANSI retain that teardown unchanged.

FFmpeg’s first encoded frame gates native startup. An elapsed sleep is insufficient under load. Packing and publication require the unchanged master timestamps to cover the recorder interval. Browser screenshots and local Nuclei templates are downloadable, with screenshot metadata checked against the observed result.

The publisher shares byte-identical artifacts larger than 1 MiB by SHA-256 across recordings. Each recording still names its observed workspace path and original checksum. Downloads contain the unchanged artifact bytes; raw terminal recordings are never deduplicated or normalized.

Timestamped `.cast` downloads are losslessly ZIP-wrapped to keep the production site below the 1 GB Pages limit. Each archive contains exactly one unchanged recording. Schema 3 records archive SHA-256, original payload filename, payload SHA-256 and byte count. The publisher reopens each archive and checks byte equality; website regressions extract and validate the original payload independently. `.ansi` downloads remain direct and byte exact. Packaging does not change native PNG pixels, timestamps, CR/LF or artifact bytes.

The verified 120-session bundle occupies 914,646,930 bytes; the production site is approximately 920.7 MB. Thirty-two Node tests, thirty-eight Python tests, TypeScript, the production build and browser review passed on 2026-10-12. See [VERIFICATION.md](VERIFICATION.md) for comparisons, actual timing measurements, sampling gaps and explicit limitations.
