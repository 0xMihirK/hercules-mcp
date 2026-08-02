# Capability-specific Kali runtime for Hercules MCP.
FROM kalilinux/kali-rolling@sha256:dea2bdf0e8c0ca1deb51b7a6253f481acae3ca9c2f1e2371077e6af55e5b2721

LABEL maintainer="Hercules MCP Server"
LABEL description="Selective tooling image for the Hercules offensive security MCP server"
ENV DEBIAN_FRONTEND=noninteractive

ARG HERCULES_CAPABILITIES=all

# Core is mandatory. Optional apt packages are added only for selected bundles.
RUN set -eux; \
    has_cap() { [ "$HERCULES_CAPABILITIES" = all ] || case ",$HERCULES_CAPABILITIES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }; \
    if [ -f /etc/apt/sources.list ]; then sed -i -E 's|https?://(http\.)?kali[^ /]*/kali|https://kali.download/kali|g' /etc/apt/sources.list; fi; \
    if [ -f /etc/apt/sources.list.d/kali.sources ]; then sed -i -E 's|https?://(http\.)?kali[^ /]*/kali/?|https://kali.download/kali/|g' /etc/apt/sources.list.d/kali.sources; fi; \
    printf '%s\n' 'Acquire::Retries "5";' 'Acquire::http::Timeout "60";' 'Acquire::https::Timeout "60";' > /etc/apt/apt.conf.d/80-hercules-retries; \
    packages="python3 python3-pip ca-certificates curl wget git unzip jq iproute2 net-tools procps"; \
    has_cap dns && packages="$packages dnsutils" || true; \
    has_cap whois && packages="$packages whois" || true; \
    has_cap nmap && packages="$packages nmap" || true; \
    has_cap ncat && packages="$packages ncat" || true; \
    has_cap hping3 && packages="$packages hping3" || true; \
    has_cap whatweb && packages="$packages whatweb wafw00f nikto wpscan" || true; \
    has_cap fuzz && packages="$packages gobuster ffuf" || true; \
    has_cap webvuln && packages="$packages commix" || true; \
    has_cap sqlmap && packages="$packages sqlmap" || true; \
    has_cap searchsploit && packages="$packages exploitdb" || true; \
    has_cap metasploit && packages="$packages metasploit-framework" || true; \
    has_cap hydra && packages="$packages hydra" || true; \
    has_cap john && packages="$packages john" || true; \
    has_cap binwalk && packages="$packages binwalk binutils" || true; \
    has_cap steghide && packages="$packages steghide libimage-exiftool-perl xxd" || true; \
    has_cap browser && packages="$packages nodejs npm chromium fonts-liberation ncat" || true; \
    for attempt in 1 2 3; do \
      rm -rf /var/lib/apt/lists/*; \
      if apt-get update -qq --allow-releaseinfo-change && \
         apt-get install -y -qq --fix-missing --no-install-recommends $packages; then break; fi; \
      [ "$attempt" != 3 ] || exit 1; sleep $((attempt * 20)); \
    done; \
    apt-get clean; rm -rf /var/lib/apt/lists/*

ARG NUCLEI_VERSION=3.11.0
ARG DNSX_VERSION=1.3.0
ARG HTTPX_VERSION=1.10.0
RUN set -eux; \
    has_cap() { [ "$HERCULES_CAPABILITIES" = all ] || case ",$HERCULES_CAPABILITIES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }; \
    case "$(dpkg --print-architecture)" in amd64) asset_arch=amd64 ;; arm64) asset_arch=arm64 ;; *) exit 1 ;; esac; \
    install_pd() { tool="$1"; version="$2"; archive="${tool}_${version}_linux_${asset_arch}.zip"; base="https://github.com/projectdiscovery/${tool}/releases/download/v${version}"; curl -fL --retry 4 "${base}/${archive}" -o "/tmp/${archive}"; curl -fL --retry 4 "${base}/${tool}_${version}_checksums.txt" -o "/tmp/${tool}.checksums"; (cd /tmp && grep " ${archive}$" "${tool}.checksums" | sha256sum -c -); unzip -q "/tmp/${archive}" "$tool" -d /usr/local/bin; chmod 0755 "/usr/local/bin/$tool"; rm -f "/tmp/${archive}" "/tmp/${tool}.checksums"; }; \
    has_cap nuclei && install_pd nuclei "$NUCLEI_VERSION" || true; \
    has_cap dns && install_pd dnsx "$DNSX_VERSION" || true; \
    has_cap whatweb && install_pd httpx "$HTTPX_VERSION" || true

ARG AMASS_VERSION=5.1.1
RUN set -eux; \
    has_cap() { [ "$HERCULES_CAPABILITIES" = all ] || case ",$HERCULES_CAPABILITIES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }; \
    if has_cap amass; then \
      case "$(dpkg --print-architecture)" in amd64) asset_arch=amd64 ;; arm64) asset_arch=arm64 ;; *) exit 1 ;; esac; \
      archive="amass_linux_${asset_arch}.tar.gz"; base="https://github.com/owasp-amass/amass/releases/download/v${AMASS_VERSION}"; \
      curl -fL --retry 4 "${base}/${archive}" -o "/tmp/${archive}"; curl -fL --retry 4 "${base}/amass_checksums.txt" -o /tmp/amass_checksums.txt; \
      (cd /tmp && grep " ${archive}$" amass_checksums.txt | sha256sum -c -); tar -xzf "/tmp/${archive}" -C /tmp; \
      find /tmp -path '*/amass' -type f -exec install -m 0755 {} /usr/local/bin/amass \; -quit; command -v amass >/dev/null; rm -rf "/tmp/${archive}" /tmp/amass_checksums.txt /tmp/amass_*; \
    fi

ARG ARJUN_VERSION=2.2.7
ARG ARJUN_SHA256=b193cdaf97bf7b0e8cd91a41da778639e01fd9738d5f666a8161377f475ce72e
RUN set -eux; \
    has_cap() { [ "$HERCULES_CAPABILITIES" = all ] || case ",$HERCULES_CAPABILITIES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }; \
    if has_cap whatweb; then archive="/tmp/arjun-${ARJUN_VERSION}.tar.gz"; curl -fL --retry 4 "https://files.pythonhosted.org/packages/04/22/c5b969720d2802de2248c2aac0414ee5ae234887cfe150564d591c73fb23/arjun-${ARJUN_VERSION}.tar.gz" -o "$archive"; printf '%s  %s\n' "$ARJUN_SHA256" "$archive" | sha256sum -c -; python3 -m pip install --no-cache-dir "$archive" --break-system-packages; rm -f "$archive"; fi

ARG DALFOX_VERSION=v3.1.2
RUN set -eux; \
    has_cap() { [ "$HERCULES_CAPABILITIES" = all ] || case ",$HERCULES_CAPABILITIES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }; \
    if has_cap webvuln; then case "$(dpkg --print-architecture)" in amd64) asset_arch=x86_64 ;; arm64) asset_arch=aarch64 ;; *) exit 1 ;; esac; archive="dalfox-${DALFOX_VERSION}-linux-${asset_arch}.tar.gz"; base="https://github.com/hahwul/dalfox/releases/download/${DALFOX_VERSION}"; curl -fL --retry 4 "${base}/${archive}" -o "/tmp/${archive}"; curl -fL --retry 4 "${base}/${archive}.sha256" -o "/tmp/${archive}.sha256"; (cd /tmp && sha256sum -c "${archive}.sha256"); tar -xzf "/tmp/${archive}" -C /tmp; binary="$(find /tmp -type f -name dalfox -print -quit)"; test -n "$binary"; install -m 0755 "$binary" /usr/local/bin/dalfox; rm -rf /tmp/dalfox-*; fi

# Browser support is headless-only. Chromium still supplies the shared-library
# closure required by the pinned cloakbrowser binary; no X server is installed.
ARG AGENT_BROWSER_VERSION=0.33.1
ARG AGENT_BROWSER_SHA512=952d0a6d4f507640f42369febb3ae635728d1918ec77a19c07b6d1e969b57b22dc6b14c249fdb3bb16d6cdfefa7c70ab0c0e18a18dd38a4a0e31203ca80fb014
ARG CLOAKBROWSER_PY_VERSION=0.5.2
ARG CLOAKBROWSER_WHEEL_SHA256=7e9088fa38e56d4f31c630e42c47204619d39974518bb44f9dfce8401e7b50cb
ENV CLOAKBROWSER_AUTO_UPDATE=false
RUN set -eux; \
    has_cap() { [ "$HERCULES_CAPABILITIES" = all ] || case ",$HERCULES_CAPABILITIES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }; \
    if has_cap browser; then \
      archive="/tmp/agent-browser-${AGENT_BROWSER_VERSION}.tgz"; curl -fL --retry 4 "https://registry.npmjs.org/agent-browser/-/agent-browser-${AGENT_BROWSER_VERSION}.tgz" -o "$archive"; printf '%s  %s\n' "$AGENT_BROWSER_SHA512" "$archive" | sha512sum -c -; npm install -g "$archive"; rm -f "$archive"; \
      wheel="/tmp/cloakbrowser-${CLOAKBROWSER_PY_VERSION}-py3-none-any.whl"; curl -fL --retry 4 "https://files.pythonhosted.org/packages/3d/c0/a7d81fd6a49d1470f919f35726ddd11c1ad7efa683cf444f75ab2e8fd75d/cloakbrowser-${CLOAKBROWSER_PY_VERSION}-py3-none-any.whl" -o "$wheel"; printf '%s  %s\n' "$CLOAKBROWSER_WHEEL_SHA256" "$wheel" | sha256sum -c -; pip3 install --no-cache-dir "$wheel" --break-system-packages; rm -f "$wheel"; python3 -m cloakbrowser install; \
    fi

# Remove download-only build helpers. Keep curl only when its structured
# capability was selected; generic core shell utilities remain in the image.
RUN set -eux; \
    has_cap() { [ "$HERCULES_CAPABILITIES" = all ] || case ",$HERCULES_CAPABILITIES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }; \
    purge="wget git unzip"; has_cap curl || purge="$purge curl"; \
    apt-get purge -y -qq $purge; apt-get autoremove -y -qq; rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/workspace/{py,sh,nuclei-templates,sqlmap-results,nmap-scripts,logs,browser} /usr/share/nmap/scripts/custom /usr/share/wordlists

# Validate exactly the backends selected by the catalog and persist evidence.
RUN set -eux; \
    has_cap() { [ "$HERCULES_CAPABILITIES" = all ] || case ",$HERCULES_CAPABILITIES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }; \
    required="bash python3 ip ps base64 sha256sum"; \
    has_cap dns && required="$required dig dnsx" || true; has_cap whois && required="$required whois" || true; has_cap amass && required="$required amass" || true; \
    has_cap nmap && required="$required nmap" || true; has_cap curl && required="$required curl" || true; has_cap ncat && required="$required ncat" || true; has_cap hping3 && required="$required hping3" || true; \
    has_cap whatweb && required="$required httpx whatweb wafw00f nikto wpscan arjun" || true; has_cap fuzz && required="$required ffuf gobuster" || true; has_cap webvuln && required="$required dalfox commix" || true; has_cap nuclei && required="$required nuclei" || true; has_cap sqlmap && required="$required sqlmap" || true; \
    has_cap searchsploit && required="$required searchsploit" || true; has_cap metasploit && required="$required msfconsole msfrpcd msfvenom" || true; has_cap hydra && required="$required hydra" || true; has_cap john && required="$required john" || true; has_cap binwalk && required="$required binwalk" || true; has_cap steghide && required="$required steghide exiftool xxd" || true; has_cap browser && required="$required agent-browser ncat" || true; \
    printf 'capabilities=%s\n' "$HERCULES_CAPABILITIES" > /opt/hercules-capabilities.txt; for tool in $required; do path="$(command -v "$tool")"; printf '%s=%s\n' "$tool" "$path" >> /opt/hercules-capabilities.txt; done

COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

ARG HERCULES_BUILD_FINGERPRINT=unknown
LABEL hercules.build_fingerprint="${HERCULES_BUILD_FINGERPRINT}"
LABEL hercules.capabilities="${HERCULES_CAPABILITIES}"
ENTRYPOINT ["/entrypoint.sh"]
