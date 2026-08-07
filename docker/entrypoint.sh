#!/bin/bash
# =============================================================================
# Hercules Container Entrypoint
#
# Handles runtime setup that cannot be baked into the image:
#   1. Verify the host-prepared wordlist mounts
#   2. Start and verify PostgreSQL + msfrpcd (unless skipped)
#   3. Publish the readiness marker and keep the container alive
# =============================================================================

echo "[hercules] Container starting..."

# ── 1. Verify prebuilt or host-prepared wordlists ───────────────────────────
# Extraction happens once on the host. Only selected consumers require mounts.
HERCULES_INSTALLED_CAPABILITIES="${HERCULES_INSTALLED_CAPABILITIES:-all}"
has_capability() {
    [ "$HERCULES_INSTALLED_CAPABILITIES" = "all" ] ||
        case ",$HERCULES_INSTALLED_CAPABILITIES," in
            *",$1,"*) return 0 ;;
            *) return 1 ;;
        esac
}
if (has_capability hydra || has_capability john) &&
    [ ! -r /usr/share/wordlists/rockyou.txt ]; then
    echo "[hercules] ERROR: selected cracking capabilities require rockyou.txt."
    exit 1
fi
if has_capability fuzz && [ ! -d /usr/share/wordlists/seclists ]; then
    echo "[hercules] ERROR: selected fuzz capability requires SecLists."
    exit 1
fi
if has_capability hydra || has_capability john || has_capability fuzz; then
    echo "[hercules] Required wordlists are ready."
else
    echo "[hercules] Wordlists are not required by this capability profile."
fi

# ── 2. Start Metasploit services asynchronously (unless skipped) ────────────
# Core readiness is independent from PostgreSQL/msfrpcd. Hercules publishes its
# MCP schemas immediately and the Metasploit tools already expose an explicit
# initializing state while this function completes.
start_metasploit() {
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

    if [ -z "${MSF_PASSWORD:-}" ]; then
        echo "[hercules] ERROR: MSF_PASSWORD was not provided."
        return 1
    fi
    MSF_BIND_HOST="${MSF_BIND_HOST:-0.0.0.0}"
    MSF_RPC_PORT="${MSF_RPC_PORT:-15553}"
    echo "[hercules] Starting msfrpcd on ${MSF_BIND_HOST}:${MSF_RPC_PORT}..."
    msfrpcd -P "$MSF_PASSWORD" -S -a "$MSF_BIND_HOST" -p "$MSF_RPC_PORT" &

    MSFRPCD_READY=0
    for _attempt in $(seq 1 60); do
        # msfrpcd intentionally daemonizes, so its launcher PID exits after
        # printing the background service PID. The listener is authoritative.
        if nc -z 127.0.0.1 "$MSF_RPC_PORT" >/dev/null 2>&1; then
            MSFRPCD_READY=1
            break
        fi
        sleep 1
    done
    if [ "$MSFRPCD_READY" -ne 1 ]; then
        echo "[hercules] ERROR: msfrpcd did not listen on port ${MSF_RPC_PORT} within 60 seconds."
        return 1
    fi
    echo "[hercules] Metasploit services started."
}

if [ "${SKIP_METASPLOIT}" != "true" ]; then
    start_metasploit &
    echo "[hercules] Metasploit initialization continues in the background."
else
    echo "[hercules] Metasploit skipped (SKIP_METASPLOIT=true)."
fi

# ── Stealth browser (cloakbrowser + agent-browser) ──────────────────────────
# Intentionally NOT started here. The cloakserve stealth-Chromium backend is
# launched lazily on the first browser_* MCP tool call (see
# hercules/tools/browser/browser_tool.py::_resolve_cloak) so non-browser
# sessions never pay the Chromium spin-up cost. Browser sessions are always
# headless; screenshots and the loopback stream relay remain available.

touch /tmp/hercules-ready
echo "[hercules] Core container ready. Sleeping..."
exec sleep infinity
