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
RUN set -eux; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's|http://http.kali.org/kali|http://kali.download/kali|g' /etc/apt/sources.list; \
    fi; \
    if [ -f /etc/apt/sources.list.d/kali.sources ]; then \
        sed -i 's|http://http.kali.org/kali/|http://kali.download/kali/|g' /etc/apt/sources.list.d/kali.sources; \
    fi; \
    printf '%s\n' \
        'Acquire::Retries "5";' \
        'Acquire::http::Timeout "60";' \
        'Acquire::https::Timeout "60";' \
        'Acquire::http::No-Cache "true";' \
        > /etc/apt/apt.conf.d/80-hercules-retries; \
    packages="\
        nmap metasploit-framework sqlmap hydra exploitdb gobuster ffuf amass \
        python3 python3-pip curl wget git unzip jq \
        dnsutils whois iputils-ping telnet iproute2 net-tools \
        whatweb wafw00f nikto wpscan \
        john ncat hping3 \
        commix binwalk steghide libimage-exiftool-perl xxd binutils \
        bsdmainutils wordlists \
        golang-go \
    "; \
    for attempt in 1 2 3; do \
        apt-get clean; \
        rm -rf /var/lib/apt/lists/*; \
        apt-get update -qq --allow-releaseinfo-change; \
        if apt-get install -y -qq --fix-missing --no-install-recommends $packages; then \
            break; \
        fi; \
        if [ "$attempt" = "3" ]; then \
            echo "apt package installation failed after 3 attempts" >&2; \
            exit 1; \
        fi; \
        echo "apt package installation failed, retrying after mirror refresh..." >&2; \
        sleep $((attempt * 20)); \
    done; \
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
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 55553

ENTRYPOINT ["/entrypoint.sh"]
