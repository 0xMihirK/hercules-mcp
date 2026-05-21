# =============================================================================
# Hercules – Pre-built Kali Linux Image for Offensive Security MCP Server
#
# This Dockerfile bakes ALL tools into a single image so that the MCP server
# starts in seconds instead of minutes. Build once, run instantly.
#
# Build:  docker build -t hercules-kali .
# =============================================================================

FROM kalilinux/kali-rolling

LABEL maintainer="Hercules MCP Server"
LABEL description="Pre-built Kali tooling image for the Hercules offensive security MCP server"

# Prevent interactive prompts during apt-get
ENV DEBIAN_FRONTEND=noninteractive

# ── 1. System packages ──────────────────────────────────────────────────────
RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
        # Core offensive tools
        nmap metasploit-framework sqlmap hydra exploitdb gobuster \
        # Language runtimes & utilities
        python3 python3-pip curl wget git unzip jq \
        # DNS / Recon / Networking utilities
        dnsutils whois iputils-ping telnet iproute2 net-tools \
        # Web scanning
        whatweb wafw00f nikto wpscan \
        # Cracking & networking
        john ncat hping3 \
        # CTF & Advanced Web Scanners
        commix binwalk steghide libimage-exiftool-perl xxd binutils \
        # Misc utilities (rev for searchsploit, wordlists for cracking)
        bsdmainutils wordlists \
        # Go (needed for some binaries)
        golang-go && \
    # Clean apt cache to reduce image size
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# ── 2. ProjectDiscovery tools (nuclei, dnsx, httpx) ─────────────────────────
RUN for tool in nuclei dnsx httpx; do \
        URL=$(curl -s "https://api.github.com/repos/projectdiscovery/${tool}/releases/latest" \
              | grep -oP '"browser_download_url":\s*"\K[^"]*linux_amd64\.zip' | head -1); \
        if [ -n "$URL" ]; then \
            curl -sSL "$URL" -o "/tmp/${tool}.zip" && \
            unzip -o "/tmp/${tool}.zip" -d /usr/local/bin/ 2>/dev/null || true && \
            chmod +x "/usr/local/bin/${tool}" 2>/dev/null || true; \
        fi; \
    done && \
    rm -f /tmp/*.zip && \
    nuclei -update-templates 2>/dev/null || true

# ── 3. OWASP Amass ──────────────────────────────────────────────────────────
RUN AMASS_URL=$(curl -s "https://api.github.com/repos/owasp-amass/amass/releases/latest" \
        | grep -oP '"browser_download_url":\s*"\K[^"]*linux_amd64\.zip' | head -1) && \
    if [ -n "$AMASS_URL" ]; then \
        curl -sSL "$AMASS_URL" -o /tmp/amass.zip && \
        unzip -o /tmp/amass.zip -d /tmp/ 2>/dev/null || true && \
        find /tmp -name amass -type f -executable -exec mv {} /usr/local/bin/ \; && \
        chmod +x /usr/local/bin/amass 2>/dev/null || true; \
    fi && \
    rm -f /tmp/amass.zip

# ── 4. Arjun (Python-based parameter discovery) ─────────────────────────────
RUN python3 -m pip install arjun --break-system-packages -q || true

# ── 5. Dalfox (XSS Scanner) ─────────────────────────────────────────────────
RUN env GOPATH=/root/go go install github.com/hahwul/dalfox/v2@latest && \
    mv /root/go/bin/dalfox /usr/local/bin/ && \
    rm -rf /root/go

# ── 6. Create workspace directories ─────────────────────────────────────────
RUN mkdir -p /opt/workspace/{py,sh,nuclei-templates,sqlmap-results,nmap-scripts,logs} \
    /usr/share/nmap/scripts/custom \
    /usr/share/wordlists && \
    # Decompress rockyou so tools (john, gobuster, hydra) can read it directly
    if [ -f /usr/share/wordlists/rockyou.txt.gz ]; then \
        gunzip /usr/share/wordlists/rockyou.txt.gz; \
    fi

# ── 6. Entrypoint script ────────────────────────────────────────────────────
# This script handles:
#   - Extracting wordlists from the mounted volume (if present)
#   - Starting PostgreSQL + msfrpcd (if SKIP_METASPLOIT != true)
#   - Keeping the container alive
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 55553

ENTRYPOINT ["/entrypoint.sh"]
