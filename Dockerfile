# syntax=docker/dockerfile:1.7
# Capability-specific Kali runtime for Hercules MCP.
#
# The pinned Kali layer does not currently contain a CA bundle. Bootstrap the
# public trust store from a second pinned, multi-architecture image before the
# first HTTPS APT request. Kali's ca-certificates package subsequently owns and
# refreshes this file; certificate verification is never disabled.
FROM curlimages/curl:8.16.0@sha256:463eaf6072688fe96ac64fa623fe73e1dbe25d8ad6c34404a669ad3ce1f104b6 AS trust-bootstrap

FROM kalilinux/kali-last-release@sha256:01a402ec78a2b3bd86394f34f8c3d6adefe3c593ae259ac0779c4d1f971c8ff5

# curlimages ships a newer pinned Mozilla bundle at /cacert.pem than its Alpine
# compatibility path; curl itself verifies with this bundle.
COPY --from=trust-bootstrap /cacert.pem /etc/ssl/certs/ca-certificates.crt

LABEL maintainer="Hercules MCP Server"
LABEL description="Selective tooling image for the Hercules offensive security MCP server"
ENV DEBIAN_FRONTEND=noninteractive

ARG HERCULES_CAPABILITIES=shell,session,workspace,dns,whois,amass,nmap,curl,ncat,hping3,whatweb,fuzz,webvuln,nuclei,sqlmap,searchsploit,metasploit,hydra,john,binwalk,steghide,browser
ARG HERCULES_BUILD_FINGERPRINT=unknown
ARG HERCULES_BUILD_CA_SHA256=
ARG HERCULES_CAPABILITY_MANIFEST_SHA256=b6b85ee48c40298e79e2d42568a34d28cdbec6392df7be10cd16f2e5daaddbfb
ARG TARGETPLATFORM
ARG HERCULES_TARGET_PLATFORM=${TARGETPLATFORM}

# Core is mandatory. Optional apt packages are added only for selected bundles.
RUN --mount=type=secret,id=hercules_build_ca \
    set -eux; \
    has_cap() { [ "$HERCULES_CAPABILITIES" = all ] || case ",$HERCULES_CAPABILITIES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }; \
    case "$HERCULES_TARGET_PLATFORM" in linux/amd64|linux/arm64) ;; *) echo "unsupported Hercules image platform: $HERCULES_TARGET_PLATFORM" >&2; exit 1 ;; esac; \
    test -z "$TARGETPLATFORM" || test "$TARGETPLATFORM" = "$HERCULES_TARGET_PLATFORM"; \
    case "$(dpkg --print-architecture)" in amd64) test "$HERCULES_TARGET_PLATFORM" = linux/amd64 ;; arm64) test "$HERCULES_TARGET_PLATFORM" = linux/arm64 ;; *) exit 1 ;; esac; \
    ca_bundle=/run/secrets/hercules_build_ca; \
    if [ -n "$HERCULES_BUILD_CA_SHA256" ]; then test -f "$ca_bundle"; fi; \
    if [ -f "$ca_bundle" ]; then \
        test -n "$HERCULES_BUILD_CA_SHA256"; \
        test "$(wc -c < "$ca_bundle")" -le 1048576; \
        ! grep -Eq -- '-----BEGIN ([^-]*PRIVATE KEY|OPENSSH PRIVATE KEY)-----' "$ca_bundle"; \
        mkdir -p /usr/local/share/ca-certificates/hercules; \
        awk 'BEGIN { inside=0; count=0; invalid=0 } /-----BEGIN CERTIFICATE-----/ { if (inside) invalid=1; inside=1; count++; file=sprintf("/usr/local/share/ca-certificates/hercules/build-ca-%03d.crt", count) } inside && $0 !~ /-----BEGIN CERTIFICATE-----/ && $0 !~ /-----END CERTIFICATE-----/ && $0 !~ /^[A-Za-z0-9+\/=[:space:]]+$/ { invalid=1 } inside { print > file } /-----END CERTIFICATE-----/ { if (!inside) invalid=1; close(file); file=""; inside=0; next } !inside && $0 !~ /^[[:space:]]*$/ && $0 !~ /^[[:space:]]*#/ { invalid=1 } END { if (inside || count == 0 || invalid) exit 1 }' "$ca_bundle"; \
        normalized_ca=/tmp/hercules-build-ca.pem; : > "$normalized_ca"; \
        for certificate in /usr/local/share/ca-certificates/hercules/build-ca-*.crt; do cat "$certificate" >> "$normalized_ca"; done; \
        printf '%s  %s\n' "$HERCULES_BUILD_CA_SHA256" "$normalized_ca" | sha256sum -c -; \
        cat "$normalized_ca" >> /etc/ssl/certs/ca-certificates.crt; rm -f "$normalized_ca"; \
    fi; \
    rm -f /etc/apt/sources.list; mkdir -p /etc/apt/sources.list.d; \
    printf '%s\n' 'Types: deb' 'URIs: https://kali.download/kali/' 'Suites: kali-last-snapshot' 'Components: main contrib non-free non-free-firmware' 'Signed-By: /usr/share/keyrings/kali-archive-keyring.gpg' > /etc/apt/sources.list.d/kali.sources; \
    grep -qx 'Suites: kali-last-snapshot' /etc/apt/sources.list.d/kali.sources; \
    ! grep -RqsE 'Suites:[[:space:]]+kali-rolling|[[:space:]]kali-rolling[[:space:]]' /etc/apt/sources.list.d; \
    printf '%s\n' 'Acquire::https::CaInfo "/etc/ssl/certs/ca-certificates.crt";' > /etc/apt/apt.conf.d/79-hercules-ca; \
    printf '%s\n' 'Acquire::Retries "5";' 'Acquire::http::Timeout "60";' 'Acquire::https::Timeout "60";' > /etc/apt/apt.conf.d/80-hercules-retries; \
    packages="python3 python3-pip ca-certificates curl unzip jq iproute2 net-tools procps"; \
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
ARG CLOAKBROWSER_PY_VERSION=0.5.3
ARG CLOAKBROWSER_WHEEL_URL=https://files.pythonhosted.org/packages/93/e8/f0d86ca18b3a1e132ffd965268f621897f60c47ea8c61b1ee9a786fffb36/cloakbrowser-0.5.3-py3-none-any.whl
ARG CLOAKBROWSER_WHEEL_SHA256=9082cfd2f104342fd718d9882984da7674ef6616308dd7932bff4b8bd5cf3cfe
ENV CLOAKBROWSER_AUTO_UPDATE=false
RUN set -eux; \
    has_cap() { [ "$HERCULES_CAPABILITIES" = all ] || case ",$HERCULES_CAPABILITIES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }; \
    if has_cap browser; then \
      archive="/tmp/agent-browser-${AGENT_BROWSER_VERSION}.tgz"; curl -fL --retry 4 "https://registry.npmjs.org/agent-browser/-/agent-browser-${AGENT_BROWSER_VERSION}.tgz" -o "$archive"; printf '%s  %s\n' "$AGENT_BROWSER_SHA512" "$archive" | sha512sum -c -; npm install -g "$archive"; rm -f "$archive"; \
      wheel="/tmp/cloakbrowser-${CLOAKBROWSER_PY_VERSION}-py3-none-any.whl"; test "$(basename "$CLOAKBROWSER_WHEEL_URL")" = "cloakbrowser-${CLOAKBROWSER_PY_VERSION}-py3-none-any.whl"; curl -fL --retry 4 "$CLOAKBROWSER_WHEEL_URL" -o "$wheel"; printf '%s  %s\n' "$CLOAKBROWSER_WHEEL_SHA256" "$wheel" | sha256sum -c -; pip3 install --no-cache-dir "$wheel" --break-system-packages; rm -f "$wheel"; python3 -m cloakbrowser install; \
    fi

# Remove a download helper only when APT proves that doing so cannot remove any
# other package. Runtime dependencies such as git (required by commix and
# Metasploit) are left under APT's dependency ownership. Never autoremove after
# installing the selected capability packages.
RUN set -eux; \
    has_cap() { [ "$HERCULES_CAPABILITIES" = all ] || case ",$HERCULES_CAPABILITIES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }; \
    cleanup_manifest=/opt/hercules-build-helpers.txt; : > "$cleanup_manifest"; \
    safe_purge() { \
      helper="$1"; \
      if ! dpkg-query -W -f='${db:Status-Status}' "$helper" 2>/dev/null | grep -qx installed; then printf '%s=not-installed\n' "$helper" >> "$cleanup_manifest"; return; fi; \
      simulation="$(apt-get -s purge "$helper")"; \
      removals="$(printf '%s\n' "$simulation" | awk '$1 == "Remv" || $1 == "Purg" {print $2}')"; \
      unexpected="$(printf '%s\n' "$removals" | sed '/^$/d' | grep -vxF "$helper" || true)"; \
      if printf '%s\n' "$removals" | grep -qxF "$helper" && [ -z "$unexpected" ]; then apt-get purge -y -qq "$helper"; printf '%s=removed\n' "$helper" >> "$cleanup_manifest"; \
      else printf '%s=retained-required-by-installed-packages\n' "$helper" >> "$cleanup_manifest"; fi; \
    }; \
    safe_purge unzip; \
    has_cap curl || safe_purge curl; \
    apt-get clean; rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/workspace/{py,sh,nuclei-templates,sqlmap-results,nmap-scripts,logs,browser} /usr/share/nmap/scripts/custom /usr/share/wordlists

# Validate exactly the backends selected by the catalog and persist evidence.
RUN set -eux; \
    has_cap() { [ "$HERCULES_CAPABILITIES" = all ] || case ",$HERCULES_CAPABILITIES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }; \
    required="bash python3 ip ps base64 sha256sum"; \
    has_cap dns && required="$required dig dnsx" || true; has_cap whois && required="$required whois" || true; has_cap amass && required="$required amass" || true; \
    has_cap nmap && required="$required nmap" || true; has_cap curl && required="$required curl" || true; has_cap ncat && required="$required ncat" || true; has_cap hping3 && required="$required hping3" || true; \
    has_cap whatweb && required="$required httpx whatweb wafw00f nikto wpscan arjun" || true; has_cap fuzz && required="$required ffuf gobuster" || true; has_cap webvuln && required="$required dalfox commix" || true; has_cap nuclei && required="$required nuclei" || true; has_cap sqlmap && required="$required sqlmap" || true; \
    has_cap searchsploit && required="$required searchsploit" || true; has_cap metasploit && required="$required msfconsole msfrpcd msfvenom" || true; has_cap hydra && required="$required hydra" || true; has_cap john && required="$required john" || true; has_cap binwalk && required="$required binwalk" || true; has_cap steghide && required="$required steghide exiftool xxd" || true; \
    if has_cap browser; then required="$required agent-browser"; has_cap ncat || required="$required ncat"; fi; \
    test -n "$HERCULES_CAPABILITY_MANIFEST_SHA256"; \
    spec=/opt/hercules-capability-manifest.spec; printf 'capabilities=%s\n' "$HERCULES_CAPABILITIES" > "$spec"; for tool in $required; do printf 'binary=%s\n' "$tool" >> "$spec"; done; \
    printf '%s  %s\n' "$HERCULES_CAPABILITY_MANIFEST_SHA256" "$spec" | sha256sum -c -; \
    printf 'capabilities=%s\nplatform=%s\napt_suite=kali-last-snapshot\nmanifest_sha256=%s\n' "$HERCULES_CAPABILITIES" "$HERCULES_TARGET_PLATFORM" "$HERCULES_CAPABILITY_MANIFEST_SHA256" > /opt/hercules-capabilities.txt; \
    cat /opt/hercules-build-helpers.txt >> /opt/hercules-capabilities.txt; \
    for tool in $required; do path="$(command -v "$tool")"; printf '%s=%s\n' "$tool" "$path" >> /opt/hercules-capabilities.txt; done; \
    if has_cap browser; then \
      python3 -c "import importlib.metadata as m; assert m.version('cloakbrowser') == '$CLOAKBROWSER_PY_VERSION'"; \
      cloak_info="$(python3 -m cloakbrowser info 2>/dev/null)"; printf '%s\n' "$cloak_info" | grep -qi 'Installed: *True'; \
      cloak_binary="$(printf '%s\n' "$cloak_info" | sed -n 's/^[Bb]inary:[[:space:]]*//p' | head -n 1)"; test -n "$cloak_binary"; test -x "$cloak_binary"; \
      AGENT_BROWSER_EXECUTABLE_PATH="$cloak_binary" agent-browser --help >/dev/null; \
    fi

COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

LABEL hercules.build_fingerprint="${HERCULES_BUILD_FINGERPRINT}"
LABEL hercules.capabilities="${HERCULES_CAPABILITIES}"
LABEL hercules.build_ca_sha256="${HERCULES_BUILD_CA_SHA256}"
LABEL hercules.cloakbrowser.version="${CLOAKBROWSER_PY_VERSION}"
LABEL hercules.cloakbrowser.sha256="${CLOAKBROWSER_WHEEL_SHA256}"
LABEL hercules.base.repository="kalilinux/kali-last-release"
LABEL hercules.base.digest="sha256:01a402ec78a2b3bd86394f34f8c3d6adefe3c593ae259ac0779c4d1f971c8ff5"
LABEL hercules.apt.suite="kali-last-snapshot"
LABEL hercules.platform="${HERCULES_TARGET_PLATFORM}"
LABEL hercules.capability_manifest_sha256="${HERCULES_CAPABILITY_MANIFEST_SHA256}"
ENTRYPOINT ["/entrypoint.sh"]
