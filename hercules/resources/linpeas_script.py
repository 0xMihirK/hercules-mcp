"""Embedded linpeas-lite.sh — compact Linux privilege escalation enumeration."""

LINPEAS_SH = r"""#!/bin/bash
# linpeas-lite.sh — Linux Privilege Escalation Enumeration
# Compact, feature-complete privesc checker for Hercules MCP Server
# Covers: sysinfo, users, SUID/SGID, capabilities, cron, network,
#         processes, writable paths, sensitive files, containers, sudo

C_RED='\033[0;31m'
C_GREEN='\033[0;32m'
C_YELLOW='\033[1;33m'
C_BLUE='\033[0;34m'
C_CYAN='\033[0;36m'
C_RESET='\033[0m'

banner() { echo -e "\n${C_CYAN}═══════════════════════════════════════${C_RESET}"; echo -e "${C_YELLOW}[*] $1${C_RESET}"; echo -e "${C_CYAN}═══════════════════════════════════════${C_RESET}"; }
warn()   { echo -e "${C_RED}[!] $1${C_RESET}"; }
info()   { echo -e "${C_GREEN}[+] $1${C_RESET}"; }
sub()    { echo -e "${C_BLUE}  [-] $1${C_RESET}"; }

echo -e "${C_RED}"
echo "╦  ╦╔╗╔╔═╗╔═╗╔═╗╔═╗   ╦  ╦╔╦╗╔═╗"
echo "║  ║║║║╠═╝║╣ ╠═╣╚═╗───║  ║ ║ ║╣ "
echo "╩═╝╩╝╚╝╩  ╚═╝╩ ╩╚═╝   ╩═╝╩ ╩ ╚═╝"
echo -e "${C_RESET}"
echo "Linux Privilege Escalation Enumeration"
echo "Hercules MCP Server Edition"
echo ""

# ── SYSTEM INFO ──
banner "SYSTEM INFORMATION"
info "Hostname: $(hostname)"
info "OS: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')"
info "Kernel: $(uname -r)"
info "Arch: $(uname -m)"
info "Uptime: $(uptime -p 2>/dev/null || uptime)"
info "Date: $(date)"

# Kernel exploit suggestions
KERN=$(uname -r)
info "Kernel version: $KERN"
if echo "$KERN" | grep -qE "^[23]\." ; then
    warn "OLD KERNEL — likely vulnerable to multiple privilege escalation exploits"
fi
if echo "$KERN" | grep -qE "^4\.[0-9]\." ; then
    warn "Kernel 4.x — check for DirtyCow (CVE-2016-5195), DirtyPipe may apply"
fi
if echo "$KERN" | grep -qE "^5\.[0-7]\." ; then
    warn "Kernel 5.x — check for DirtyPipe (CVE-2022-0847) if < 5.8"
fi

# ── CURRENT USER ──
banner "CURRENT USER & GROUPS"
info "User: $(whoami) (uid=$(id -u))"
info "Groups: $(id)"
if [ "$(id -u)" -eq 0 ]; then
    warn "RUNNING AS ROOT — already privileged!"
fi

# ── SUDO PERMISSIONS ──
banner "SUDO PERMISSIONS"
if command -v sudo &>/dev/null; then
    SUDO_OUT=$(sudo -l 2>/dev/null)
    if [ -n "$SUDO_OUT" ]; then
        echo "$SUDO_OUT"
        echo "$SUDO_OUT" | grep -i "NOPASSWD" && warn "NOPASSWD entries found!"
        echo "$SUDO_OUT" | grep -iE "(ALL|env_keep|LD_PRELOAD|LD_LIBRARY)" && warn "Potential sudo escalation vectors!"
        for bin in vim vi nano less more awk perl python python3 ruby lua find nmap bash sh dash zsh env ftp scp wget curl tar zip git docker lxc; do
            echo "$SUDO_OUT" | grep -qw "$bin" && warn "GTFOBins sudo candidate: $bin"
        done
    else
        sub "Cannot check sudo (no password or not allowed)"
    fi
else
    sub "sudo not installed"
fi

# ── SUID/SGID BINARIES ──
banner "SUID/SGID BINARIES"
info "SUID files:"
find / -perm -4000 -type f 2>/dev/null | while read -r f; do
    sub "$f ($(ls -la "$f" 2>/dev/null | awk '{print $3":"$4}'))"
    bn=$(basename "$f")
    case "$bn" in
        nmap|vim|vi|find|bash|sh|dash|zsh|env|awk|perl|python*|ruby|lua|less|more|cp|mv|wget|curl|tar|zip|docker|pkexec|su|passwd|chsh|newgrp)
            warn "  → GTFOBins SUID candidate: $bn" ;;
    esac
done
info "SGID files:"
find / -perm -2000 -type f 2>/dev/null | head -30 | while read -r f; do
    sub "$f"
done

# ── CAPABILITIES ──
banner "FILE CAPABILITIES"
if command -v getcap &>/dev/null; then
    getcap -r / 2>/dev/null | while read -r line; do
        sub "$line"
        echo "$line" | grep -qiE "(cap_setuid|cap_setgid|cap_dac_override|cap_sys_admin|cap_sys_ptrace|cap_net_raw)" && warn "  → Dangerous capability!"
    done
else
    sub "getcap not available"
fi

# ── USERS & PASSWORDS ──
banner "USERS & PASSWORD FILES"
info "Users with shells:"
grep -vE "(nologin|false|sync|halt|shutdown)" /etc/passwd 2>/dev/null | while read -r line; do
    sub "$line"
done
info "/etc/shadow readable?"
if [ -r /etc/shadow ]; then
    warn "YES — /etc/shadow is readable!"
    cat /etc/shadow 2>/dev/null
else
    sub "No (normal)"
fi
info "Users with empty passwords:"
awk -F: '($2 == "" || $2 == "!") {print $1}' /etc/shadow 2>/dev/null | while read -r u; do
    warn "Empty/no password: $u"
done

# ── CRON JOBS ──
banner "CRON JOBS & SCHEDULED TASKS"
info "System crontabs:"
for f in /etc/crontab /etc/cron.d/* /var/spool/cron/crontabs/*; do
    if [ -r "$f" ] 2>/dev/null; then
        sub "=== $f ==="
        cat "$f" 2>/dev/null | grep -v "^#" | grep -v "^$"
    fi
done
info "Writable cron directories:"
for d in /etc/cron.d /etc/cron.daily /etc/cron.hourly /etc/cron.weekly /etc/cron.monthly; do
    [ -w "$d" ] && warn "Writable: $d"
done
info "Systemd timers:"
systemctl list-timers --all 2>/dev/null | head -20

# ── NETWORK ──
banner "NETWORK INFORMATION"
info "Interfaces:"
ip addr 2>/dev/null || ifconfig 2>/dev/null
info "Routes:"
ip route 2>/dev/null || route -n 2>/dev/null
info "Listening services:"
ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null
info "ARP table:"
ip neigh 2>/dev/null || arp -a 2>/dev/null
info "DNS config:"
cat /etc/resolv.conf 2>/dev/null
info "Iptables rules:"
iptables -L -n 2>/dev/null | head -30

# ── PROCESSES ──
banner "RUNNING PROCESSES"
ps auxf 2>/dev/null | head -50
info "Processes running as root:"
ps aux 2>/dev/null | awk '$1=="root"' | head -20

# ── INTERESTING FILES ──
banner "INTERESTING FILES"
info "SSH keys:"
find / -name "id_rsa" -o -name "id_dsa" -o -name "id_ecdsa" -o -name "id_ed25519" -o -name "authorized_keys" 2>/dev/null | while read -r f; do
    warn "Found: $f"
    [ -r "$f" ] && warn "  → READABLE!"
done
info "Config files with passwords:"
grep -rlI "password\|passwd\|pwd\|secret\|api_key\|token\|credential" /etc/ /opt/ /var/www/ /home/ 2>/dev/null | head -20 | while read -r f; do
    sub "$f"
done
info ".bash_history files:"
find /home/ /root/ -name ".bash_history" -readable 2>/dev/null | while read -r f; do
    warn "Readable history: $f"
done
info "Writable /etc/passwd?"
[ -w /etc/passwd ] && warn "YES — /etc/passwd is writable! Add a root user!"
info "World-writable directories in PATH:"
echo "$PATH" | tr ':' '\n' | while read -r d; do
    [ -w "$d" ] && warn "Writable PATH dir: $d"
done
info "Backup files:"
find / -name "*.bak" -o -name "*.old" -o -name "*.backup" -o -name "*.save" 2>/dev/null | head -15 | while read -r f; do
    sub "$f"
done
info "Database files:"
find / -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" 2>/dev/null | head -15 | while read -r f; do
    sub "$f"
done

# ── CONTAINER / VIRTUALIZATION ──
banner "CONTAINER & VIRTUALIZATION"
if [ -f /.dockerenv ]; then
    warn "Running inside Docker!"
elif grep -q docker /proc/1/cgroup 2>/dev/null; then
    warn "Running inside Docker (cgroup detected)!"
fi
if grep -q lxc /proc/1/cgroup 2>/dev/null; then
    warn "Running inside LXC!"
fi
if command -v docker &>/dev/null; then
    info "Docker binary available"
    docker ps 2>/dev/null && warn "Current user can run docker commands!"
fi
if command -v lxc &>/dev/null; then
    info "LXC available"
fi

# ── NFS / MOUNTS ──
banner "MOUNTS & NFS"
info "Mounted filesystems:"
mount 2>/dev/null | grep -vE "(proc|sys|cgroup|tmpfs)"
info "NFS exports:"
cat /etc/exports 2>/dev/null
showmount -e 127.0.0.1 2>/dev/null
info "Fstab:"
cat /etc/fstab 2>/dev/null | grep -v "^#"

# ── INSTALLED TOOLS ──
banner "USEFUL TOOLS AVAILABLE"
for t in gcc cc make wget curl python python3 perl ruby nc ncat socat gdb strace ltrace tcpdump nmap; do
    command -v "$t" &>/dev/null && info "$t: $(which $t)"
done

echo ""
echo -e "${C_CYAN}═══════════════════════════════════════${C_RESET}"
echo -e "${C_YELLOW}[*] linpeas-lite enumeration complete${C_RESET}"
echo -e "${C_CYAN}═══════════════════════════════════════${C_RESET}"
"""
