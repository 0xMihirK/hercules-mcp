"""Embedded powerup-lite.ps1 — compact PowerShell privilege escalation checks."""

POWERUP_PS1 = r"""# PowerUp-lite.ps1 — Windows Privilege Escalation via PowerShell
# Compact, feature-complete privesc checker for Hercules MCP Server
# Covers: service misconfigs, unquoted paths, writable service binaries,
#         AlwaysInstallElevated, autologon, modifiable tasks, DLL hijacking

$ErrorActionPreference = "SilentlyContinue"

function Write-Banner($text) {
    Write-Host "`n===========================================" -ForegroundColor Cyan
    Write-Host "[*] $text" -ForegroundColor Yellow
    Write-Host "===========================================" -ForegroundColor Cyan
}

function Write-Finding($text) {
    Write-Host "[!] $text" -ForegroundColor Red
}

function Write-Info($text) {
    Write-Host "[+] $text" -ForegroundColor Green
}

Write-Host @"

 ____                       _   _            _     _ _
|  _ \ _____      _____ _ _| | | |_ __      | |   (_) |_ ___
| |_) / _ \ \ /\ / / _ \ '__| | | | '_ \ ___| |   | | __/ _ \
|  __/ (_) \ V  V /  __/ |  | |_| | |_) |___| |___| | ||  __/
|_|   \___/ \_/\_/ \___|_|   \___/| .__/    |_____|_|\__\___|
                                  |_|
"@ -ForegroundColor Red

Write-Host "PowerShell Privilege Escalation Checks" -ForegroundColor White
Write-Host "Hercules MCP Server Edition`n" -ForegroundColor DarkGray

# ── CURRENT CONTEXT ──
Write-Banner "CURRENT USER CONTEXT"
Write-Info "User: $env:USERNAME"
Write-Info "Domain: $env:USERDOMAIN"
Write-Info "Is Admin: $([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)"
Write-Host "`nPrivileges:" -ForegroundColor White
whoami /priv | Select-String "Se" | ForEach-Object {
    $line = $_.ToString()
    if ($line -match "Enabled") {
        $privName = ($line -split "\s+")[0]
        $dangerous = @("SeImpersonatePrivilege","SeAssignPrimaryTokenPrivilege","SeBackupPrivilege",
                       "SeRestorePrivilege","SeDebugPrivilege","SeTakeOwnershipPrivilege","SeLoadDriverPrivilege")
        if ($dangerous -contains $privName) {
            Write-Finding "DANGEROUS: $privName — Enabled"
        } else {
            Write-Info "$privName — Enabled"
        }
    }
}

# ── UNQUOTED SERVICE PATHS ──
Write-Banner "UNQUOTED SERVICE PATHS"
$services = Get-WmiObject -Class Win32_Service | Where-Object {
    $_.PathName -and
    $_.PathName -notmatch '^"' -and
    $_.PathName -match '\s' -and
    $_.PathName -notmatch 'C:\\Windows'
}
if ($services) {
    foreach ($svc in $services) {
        Write-Finding "Unquoted: $($svc.Name) → $($svc.PathName)"
        Write-Info "  StartMode: $($svc.StartMode), RunAs: $($svc.StartName)"
    }
} else {
    Write-Info "No unquoted service paths found."
}

# ── WRITABLE SERVICE BINARIES ──
Write-Banner "WRITABLE SERVICE BINARIES"
Get-WmiObject -Class Win32_Service | ForEach-Object {
    $path = $_.PathName
    if ($path) {
        # Extract executable path
        if ($path.StartsWith('"')) {
            $exePath = ($path -split '"')[1]
        } else {
            $exePath = ($path -split ' ')[0]
        }
        if (Test-Path $exePath) {
            $acl = Get-Acl $exePath
            $acl.Access | Where-Object {
                $_.FileSystemRights -match "FullControl|Modify|Write" -and
                $_.IdentityReference -notmatch "SYSTEM|Administrators|TrustedInstaller"
            } | ForEach-Object {
                Write-Finding "Writable service binary: $exePath"
                Write-Info "  Service: $($_.Name), Identity: $($_.IdentityReference)"
            }
        }
    }
}

# ── MODIFIABLE SERVICE CONFIGURATIONS ──
Write-Banner "MODIFIABLE SERVICE CONFIGS (sc.exe)"
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Get-WmiObject Win32_Service | ForEach-Object {
    $sdRes = sc.exe sdshow $_.Name 2>$null
    if ($sdRes -match "A;.*?(WD|WP|RP|CC|DC|LC).*?$($env:USERNAME)") {
        Write-Finding "Modifiable service config: $($_.Name)"
    }
}

# ── AlwaysInstallElevated ──
Write-Banner "AlwaysInstallElevated"
$hklm = Get-ItemProperty "HKLM:\SOFTWARE\Policies\Microsoft\Windows\Installer" -Name AlwaysInstallElevated 2>$null
$hkcu = Get-ItemProperty "HKCU:\SOFTWARE\Policies\Microsoft\Windows\Installer" -Name AlwaysInstallElevated 2>$null
if ($hklm.AlwaysInstallElevated -eq 1 -and $hkcu.AlwaysInstallElevated -eq 1) {
    Write-Finding "AlwaysInstallElevated is ENABLED in both HKLM and HKCU!"
    Write-Finding "  → Generate MSI payload with msfvenom for SYSTEM shell"
} else {
    Write-Info "AlwaysInstallElevated not exploitable."
}

# ── AUTOLOGON CREDENTIALS ──
Write-Banner "AUTOLOGON CREDENTIALS"
$winlogon = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
if ($winlogon.DefaultPassword) {
    Write-Finding "AutoLogon credentials found!"
    Write-Finding "  User: $($winlogon.DefaultUserName)"
    Write-Finding "  Pass: $($winlogon.DefaultPassword)"
    Write-Finding "  Domain: $($winlogon.DefaultDomainName)"
} else {
    Write-Info "No autologon credentials found."
}

# ── STORED CREDENTIALS ──
Write-Banner "STORED CREDENTIALS"
$creds = cmdkey /list 2>$null
if ($creds -match "Target:") {
    Write-Finding "Stored credentials found:"
    $creds | Select-String "Target:" | ForEach-Object { Write-Info "  $_" }
} else {
    Write-Info "No stored credentials."
}

# ── SCHEDULED TASKS ──
Write-Banner "MODIFIABLE SCHEDULED TASKS"
Get-ScheduledTask | Where-Object { $_.State -ne "Disabled" } | ForEach-Object {
    $task = $_
    $actions = $task.Actions
    foreach ($action in $actions) {
        $exePath = $action.Execute
        if ($exePath -and (Test-Path $exePath)) {
            $acl = Get-Acl $exePath
            $acl.Access | Where-Object {
                $_.FileSystemRights -match "FullControl|Modify|Write" -and
                $_.IdentityReference -notmatch "SYSTEM|Administrators|TrustedInstaller"
            } | ForEach-Object {
                Write-Finding "Writable task binary: $exePath"
                Write-Info "  Task: $($task.TaskName), RunAs: $($task.Principal.UserId)"
            }
        }
    }
}

# ── DLL HIJACKING OPPORTUNITIES ──
Write-Banner "POTENTIAL DLL HIJACKING"
$pathDirs = $env:PATH -split ";"
foreach ($dir in $pathDirs) {
    if ($dir -and (Test-Path $dir)) {
        $acl = Get-Acl $dir
        $acl.Access | Where-Object {
            $_.FileSystemRights -match "FullControl|Modify|Write" -and
            $_.IdentityReference -notmatch "SYSTEM|Administrators|TrustedInstaller"
        } | ForEach-Object {
            Write-Finding "Writable PATH directory: $dir → DLL hijacking possible"
        }
    }
}

# ── REGISTRY AUTORUN ──
Write-Banner "REGISTRY AUTORUN ENTRIES"
$autorunKeys = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
)
foreach ($key in $autorunKeys) {
    $entries = Get-ItemProperty $key 2>$null
    if ($entries) {
        Write-Info "Entries in $key :"
        $entries.PSObject.Properties | Where-Object { $_.Name -notmatch "^PS" } | ForEach-Object {
            Write-Info "  $($_.Name): $($_.Value)"
            $exePath = ($_.Value -split '"')[1]
            if (!$exePath) { $exePath = ($_.Value -split ' ')[0] }
            if ($exePath -and (Test-Path $exePath)) {
                $acl = Get-Acl $exePath
                $acl.Access | Where-Object {
                    $_.FileSystemRights -match "FullControl|Modify|Write" -and
                    $_.IdentityReference -notmatch "SYSTEM|Administrators|TrustedInstaller"
                } | ForEach-Object {
                    Write-Finding "  → WRITABLE autorun binary: $exePath"
                }
            }
        }
    }
}

# ── DEFENDER STATUS ──
Write-Banner "WINDOWS DEFENDER STATUS"
try {
    $defender = Get-MpComputerStatus
    Write-Info "Real-time protection: $($defender.RealTimeProtectionEnabled)"
    Write-Info "Anti-spyware: $($defender.AntispywareEnabled)"
    $exclusions = Get-MpPreference
    if ($exclusions.ExclusionPath) {
        Write-Finding "Defender path exclusions:"
        $exclusions.ExclusionPath | ForEach-Object { Write-Finding "  $_" }
    }
} catch {
    Write-Info "Cannot query Defender (may not be present)."
}

Write-Host "`n===========================================" -ForegroundColor Cyan
Write-Host "[*] PowerUp-lite enumeration complete" -ForegroundColor Yellow
Write-Host "===========================================" -ForegroundColor Cyan
"""
