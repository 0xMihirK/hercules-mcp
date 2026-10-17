# Small bootstrap only. The Python setup CLI owns all installation decisions.
[CmdletBinding()]
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$SetupArgs)
$ErrorActionPreference = 'Stop'
if (-not $SetupArgs -or $SetupArgs -notcontains '--client') {
    throw 'Usage: .\scripts\setup.ps1 install --client claude-code --yes (or status/repair/resume/verify)'
}
$gitCommand = (Get-Command git -CommandType Application -ErrorAction Stop).Source
$uvCommand = (Get-Command uv -CommandType Application -ErrorAction Stop).Source
$managedBase = Join-Path $env:LOCALAPPDATA 'hercules-mcp'
$bootstrapPath = Join-Path $managedBase ('releases\bootstrap-' + [guid]::NewGuid().ToString('N'))
# A venv is created only at its final permanent path; it is never moved.
New-Item -ItemType Directory -Path (Split-Path -Parent $bootstrapPath) -Force | Out-Null
[Console]::Error.WriteLine("Preparing setup at $bootstrapPath (GitHub source and locked Python dependencies only).")
& $gitCommand clone --quiet 'https://github.com/0xMihirK/hercules-mcp.git' $bootstrapPath
if ($LASTEXITCODE -ne 0) { throw "Clone failed. Retained resumable bootstrap: $bootstrapPath" }
$sourceRevision = & $gitCommand -C $bootstrapPath rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Source revision could not be established.' }
[Console]::Error.WriteLine("Setup source revision: $sourceRevision")
& $uvCommand sync --locked --project $bootstrapPath
if ($LASTEXITCODE -ne 0) { throw "Locked setup failed. Retained bootstrap: $bootstrapPath" }
$setupCommand = Join-Path $bootstrapPath '.venv\Scripts\hercules-setup.exe'
& $setupCommand @SetupArgs
exit $LASTEXITCODE
