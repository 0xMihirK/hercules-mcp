# CTF continuity and custom tools

Read the supplied objective, handouts, prior notes, and scope first. Clarify
whether a part needs one flag or several before exploring infrastructure.
Use a challenge folder in the event workspace, or choose isolation when a clean
engagement genuinely needs it. One writer owns each challenge's notes; parallel
workers must not rotate or stop their shared runtime.

## Small progress record

Keep a private `challenge/notes.md` and update it at meaningful transitions:

```markdown
# Challenge
Objective / permitted target and techniques:
Current session / previous session references:
Endpoint and supplied handouts:
Artifact paths / commands or script paths:
Authentication state / expiry (reference private material; do not echo secrets):
Candidate ID -> retrieved | rejected/decoy | accepted; evidence/submission reference:
Dependencies / install command and version:
Next unresolved hypothesis / stop condition:
Workers and managed job IDs:
Final cleanup status / retained evidence:
```

Read prior evidence before guessing credentials, reinstalling dependencies, or
repeating a scan. A retrieved flag-shaped string, root access, or an environment
variable is not scoring acceptance. Propagate user rejection into notes and
writeups; never label the same rejected candidate verified without new evidence.
Preserve observation versus inference, and explain incomplete verification.

## Trust coverage, not an empty screen

Before trusting fuzzing, check a known positive route and a negative control
with the same authentication and matching conditions. FFUF accepts a base URL
or one existing `FUZZ`; use verified local wordlists. Check deadlines, stderr,
coverage and authentication expiry. Timeout, missing tools, HTTP 429, and
discarded stderr are not evidence of absence. Use one active rate-controlled
worker per target; back off and checkpoint rather than skipping throttled
candidates or competing with another worker.

Save complete output before `head`, `grep`, slices, or redirects. Hercules can
retain only what the command emits; it cannot recover evidence your pipeline
discarded. Use `set -o pipefail` when pipeline failure matters and distinguish
local SSH/client status from the remote command's exit code. Capture diagnostics
instead of masking errors with a final `echo DONE` or `2>/dev/null`.

## Install and use your own tools

After explicit startup, authorized `shell_exec` commands can install packages,
run custom clients, and download verified tools. It is a noninteractive root
shell, not a new host installer. Capability selections describe preinstalled
packages, not a security sandbox against root. Do not silently expand the
operator's chosen setup or weaken target/approval controls.

The baseline includes SSH, unzip, and Python virtual-environment support.
Check availability first. For additional system packages use a deliberate
noninteractive install with a suitable timeout (or one background job), retain
stderr, and record versions. Prefer workspace-local Python environments:

```sh
python3 -m venv /opt/workspace/challenge/.venv
/opt/workspace/challenge/.venv/bin/python -m pip install '<required-package>'
/opt/workspace/challenge/.venv/bin/python /opt/workspace/challenge/client.py
```

Verify downloaded sources/checksums, avoid piping unreviewed downloads into a
shell, and keep dependency records and scripts in the workspace. Container-layer
apt/pip installs disappear when the container is replaced; never assume they
survived stop/resume. Workspace environments remain as files but may need
rebuilding when the image's Python/runtime changes. Do not replay installs or
downloads automatically during startup. Host installation never uses this path.

Foreground `shell_exec` defaults to 60 seconds and accepts 1-3600; it is not a
fixed 60-second cap. Use background jobs for long listeners/observers, namespace
IDs by challenge, back off unchanged polls, and confirm termination. Save progress
before final shutdown; inspect retained files offline rather than starting a
container only to read notes.
