"""Embedded winpeas-lite.bat — compact Windows privilege escalation enumeration."""

WINPEAS_BAT = r"""@echo off
REM winpeas-lite.bat — Windows Privilege Escalation Enumeration
REM Compact, feature-complete privesc checker for Hercules MCP Server
REM Covers: sysinfo, users, services, tasks, network, registry, files

echo.
echo ========================================
echo   winPEAS-lite — Windows PrivEsc Enum
echo   Hercules MCP Server Edition
echo ========================================
echo.

echo [*] SYSTEM INFORMATION
echo ═══════════════════════
systeminfo 2>nul
echo.
echo [+] Hostname: %COMPUTERNAME%
echo [+] Username: %USERNAME%
echo [+] Domain:   %USERDOMAIN%
echo [+] OS Arch:  %PROCESSOR_ARCHITECTURE%
echo.

echo [*] HOTFIXES / PATCHES
echo ═══════════════════════
wmic qfe list brief 2>nul
echo.

echo [*] USERS AND GROUPS
echo ═══════════════════════
echo [+] Local Users:
net user 2>nul
echo.
echo [+] Current User Privileges:
whoami /priv 2>nul
echo.
echo [+] Current User Groups:
whoami /groups 2>nul
echo.
echo [+] Administrators Group:
net localgroup Administrators 2>nul
echo.
echo [+] Remote Desktop Users:
net localgroup "Remote Desktop Users" 2>nul
echo.

echo [*] INTERESTING PRIVILEGES
echo ═══════════════════════
whoami /priv 2>nul | findstr /i "SeImpersonate SeAssignPrimaryToken SeBackup SeRestore SeDebug SeTakeOwnership SeLoadDriver"
if %errorlevel% equ 0 (
    echo [!] DANGEROUS PRIVILEGES FOUND — Potato/PrintSpoofer/Token attacks possible!
)
echo.

echo [*] SERVICES
echo ═══════════════════════
echo [+] All services:
wmic service get name,displayname,pathname,startmode,startname 2>nul | findstr /i /v "C:\Windows"
echo.
echo [+] Unquoted service paths:
for /f "tokens=*" %%s in ('wmic service get name,pathname,startmode 2^>nul ^| findstr /i /v /c:"C:\Windows\system32"') do echo %%s
echo.
echo [+] Services running as SYSTEM:
wmic service get name,startname 2>nul | findstr /i "LocalSystem"
echo.
echo [+] Modifiable service binaries:
for /f "tokens=2 delims='='" %%a in ('wmic service list full 2^>nul ^| findstr /i "pathname" ^| findstr /i /v "system32"') do (
    icacls "%%a" 2>nul | findstr /i "(F) (M) (W)" | findstr /i /v "SYSTEM Administrators TrustedInstaller" && echo [!] WRITABLE SERVICE BINARY: %%a
)
echo.

echo [*] SCHEDULED TASKS
echo ═══════════════════════
schtasks /query /fo LIST /v 2>nul | findstr /i "TaskName Run Author"
echo.

echo [*] NETWORK INFORMATION
echo ═══════════════════════
echo [+] IP Configuration:
ipconfig /all 2>nul
echo.
echo [+] Listening Ports:
netstat -ano 2>nul | findstr "LISTENING"
echo.
echo [+] ARP Table:
arp -a 2>nul
echo.
echo [+] Routes:
route print 2>nul | findstr /i "0.0.0.0"
echo.
echo [+] Firewall State:
netsh advfirewall show allprofiles state 2>nul
echo.
echo [+] WiFi Passwords:
for /f "tokens=2 delims=:" %%a in ('netsh wlan show profiles 2^>nul ^| findstr "Profile"') do (
    netsh wlan show profile name="%%a" key=clear 2>nul | findstr "Key Content"
)
echo.

echo [*] REGISTRY CHECKS
echo ═══════════════════════
echo [+] AlwaysInstallElevated:
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated 2>nul
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer /v AlwaysInstallElevated 2>nul
echo.
echo [+] AutoLogon Credentials:
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultUserName 2>nul
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultPassword 2>nul
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultDomainName 2>nul
echo.
echo [+] Stored Credentials:
cmdkey /list 2>nul
echo.
echo [+] UAC Configuration:
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System /v EnableLUA 2>nul
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System /v ConsentPromptBehaviorAdmin 2>nul
echo.
echo [+] LSASS Protection:
reg query HKLM\SYSTEM\CurrentControlSet\Control\Lsa /v RunAsPPL 2>nul
echo.
echo [+] WDigest (plaintext creds in memory):
reg query HKLM\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest /v UseLogonCredential 2>nul
echo.

echo [*] INSTALLED SOFTWARE
echo ═══════════════════════
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall /s 2>nul | findstr "DisplayName DisplayVersion"
echo.

echo [*] INTERESTING FILES
echo ═══════════════════════
echo [+] Searching for password files:
where /r C:\ *.config *.ini *.xml *.txt 2>nul | findstr /i "password pass cred web.config unattend"
echo.
echo [+] SAM/SYSTEM backup files:
dir /s /b C:\Windows\repair\SAM 2>nul
dir /s /b C:\Windows\repair\SYSTEM 2>nul
dir /s /b C:\Windows\System32\config\RegBack\SAM 2>nul
dir /s /b C:\Windows\System32\config\RegBack\SYSTEM 2>nul
echo.
echo [+] Unattend files:
dir /s /b C:\unattend.xml C:\Windows\Panther\unattend.xml C:\Windows\Panther\Unattend\Unattend.xml C:\Windows\system32\sysprep\unattend.xml 2>nul
echo.
echo [+] PowerShell history:
type %APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt 2>nul
echo.

echo [*] ANTIVIRUS / DEFENDER
echo ═══════════════════════
sc query WinDefend 2>nul | findstr "STATE"
echo [+] Defender Exclusions:
reg query "HKLM\SOFTWARE\Microsoft\Windows Defender\Exclusions\Paths" 2>nul
reg query "HKLM\SOFTWARE\Microsoft\Windows Defender\Exclusions\Extensions" 2>nul
echo.

echo ========================================
echo [*] winPEAS-lite enumeration complete
echo ========================================
"""
