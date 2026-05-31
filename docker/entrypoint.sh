#!/bin/bash
# =============================================================================
# Hercules Container Entrypoint
#
# Handles runtime setup that cannot be baked into the image:
#   1. Extract wordlists from mounted volume (if present)
#   2. Start PostgreSQL + msfrpcd (unless SKIP_METASPLOIT=true)
#   3. Keep container alive
# =============================================================================

echo "[hercules] Container starting..."

# ── 1. Prepare wordlists ────────────────────────────────────────────────────
# Always decompress rockyou.txt if it's still gzipped (Kali ships it compressed)
if [ -f /usr/share/wordlists/rockyou.txt.gz ] && [ ! -f /usr/share/wordlists/rockyou.txt ]; then
    echo "[hercules] Decompressing rockyou.txt..."
    gunzip -k /usr/share/wordlists/rockyou.txt.gz 2>/dev/null || true
fi

# Extract additional wordlists from host-mounted volume (if present)
if [ -d /opt/wordlists_host ]; then
    echo "[hercules] Extracting wordlists from host mount..."

    if [ -f /opt/wordlists_host/SecLists.zip ] && [ ! -d /usr/share/wordlists/seclists ]; then
        echo "[hercules] Extracting SecLists..."
        unzip -q -o /opt/wordlists_host/SecLists.zip -d /usr/share/wordlists/ 2>/dev/null || true
        mv /usr/share/wordlists/SecLists-master /usr/share/wordlists/seclists 2>/dev/null || true
    fi

    if [ -f /opt/wordlists_host/rockyou.txt.tar.gz ] && [ ! -f /usr/share/wordlists/rockyou.txt ]; then
        echo "[hercules] Extracting rockyou.txt from host mount..."
        tar -xzf /opt/wordlists_host/rockyou.txt.tar.gz -C /usr/share/wordlists/ 2>/dev/null || true
    fi
fi

echo "[hercules] Wordlists ready at /usr/share/wordlists/"

# ── 2. Start Metasploit services (unless skipped) ───────────────────────────
if [ "${SKIP_METASPLOIT}" != "true" ]; then
    echo "[hercules] Starting PostgreSQL for Metasploit..."

    PG_STARTED=0

    # Method 1: pg_ctlcluster
    if command -v pg_ctlcluster &>/dev/null; then
        PG_VER=$(pg_lsclusters -h 2>/dev/null | awk '{print $1}' | head -1)
        PG_CLUSTER=$(pg_lsclusters -h 2>/dev/null | awk '{print $2}' | head -1)
        if [ -n "$PG_VER" ] && [ -n "$PG_CLUSTER" ]; then
            pg_ctlcluster "$PG_VER" "$PG_CLUSTER" start 2>/dev/null && PG_STARTED=1
        fi
    fi

    # Method 2: init.d
    if [ "$PG_STARTED" -eq 0 ]; then
        /etc/init.d/postgresql start 2>/dev/null && PG_STARTED=1 || true
    fi

    # Method 3: direct pg_ctl
    if [ "$PG_STARTED" -eq 0 ]; then
        su - postgres -c "pg_ctl -D /var/lib/postgresql/*/main -l /var/log/postgresql/pg.log start" 2>/dev/null && PG_STARTED=1 || true
    fi

    if [ "$PG_STARTED" -eq 1 ]; then
        echo "[hercules] PostgreSQL started. Initializing msfdb..."
        msfdb init 2>/dev/null || echo "[hercules] msfdb init had warnings (non-fatal)."
    else
        echo "[hercules] WARNING: PostgreSQL could not be started. MSF will run without DB."
    fi

    MSF_PASSWORD="${MSF_PASSWORD:-hercules}"
    echo "[hercules] Starting msfrpcd (password=$MSF_PASSWORD)..."
    msfrpcd -P "$MSF_PASSWORD" -S -a 0.0.0.0 &

    sleep 3
    echo "[hercules] Metasploit services started."
else
    echo "[hercules] Metasploit skipped (SKIP_METASPLOIT=true)."
fi

touch /tmp/hercules-ready
echo "[hercules] Container ready. Sleeping..."
exec sleep infinity
