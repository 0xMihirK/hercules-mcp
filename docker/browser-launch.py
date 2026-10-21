#!/usr/bin/python3
"""Minimal Obscura launcher for host networking — NO SSRF boundary.

The container runs on the host network, so there is no isolated bridge for a
firewall/SOCKS gateway. This launcher does the ONE thing that still matters:
drop privileges to the unprivileged engine UID before exec'ing the real Obscura
binary. It installs no gateway, no nftables, and no target policy — the browser
can reach host-local, LAN, and cloud-metadata services. The MCP server's agent
instructions warn the agent to only browse authorized targets.

agent-browser invokes this as:  serve --host 127.0.0.1 --port <N> [--proxy <url>]
Any --proxy is the operator's own upstream (set by the host-side browser tool).
Obscura (Chromium) cannot authenticate a proxy from the CLI, so an upstream is
routed through the local auth-forwarder (browser-forwarder.py): this launcher
rewrites --proxy to an unauthenticated loopback SOCKS5 hop that injects the
upstream's credentials. This forwarder is NOT an SSRF boundary; it filters
nothing.
"""

import os
import subprocess
import sys

ENGINE = "/opt/hercules/browser/obscura"
FORWARDER = "/opt/hercules/browser-forwarder.py"
ENGINE_UID = 19731


def start_forwarder(upstream):
    """Start the loopback auth-forwarder and return its socks5h:// URL.

    Obscura (Chromium) cannot authenticate a proxy from the command line, so it
    speaks an unauthenticated SOCKS5 hop to this forwarder, which injects the
    operator's upstream credentials. The forwarder outlives this launcher (which
    execs Obscura) and lives until the container stops.
    shortcut: no readline timeout; the forwarder prints its port immediately or
    exits (EOF) on a bad upstream. Revisit if a real hang is ever observed.
    """
    proc = subprocess.Popen(
        [sys.executable, FORWARDER, "serve"],
        # Upstream (with credentials) goes via env, never argv, so it stays out
        # of the process list.
        env={"HERCULES_FORWARD_UPSTREAM": upstream, "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        start_new_session=True, close_fds=True,
    )
    line = proc.stdout.readline()
    port = int(line.strip()) if line.strip().isdigit() else 0
    if not port:
        proc.kill()
        raise ValueError("browser proxy forwarder failed to start")
    return f"socks5h://127.0.0.1:{port}"


def launch(args):
    # Allow only the agent-browser --version probe and the loopback serve form.
    # Both still go through setpriv below so the engine never runs as root.
    if args != ["--version"] and (
        len(args) < 5 or args[:3] != ["serve", "--host", "127.0.0.1"]
    ):
        raise ValueError("unsupported engine launch")
    # An operator upstream proxy is routed through the local auth-forwarder;
    # Obscura only ever sees an unauthenticated loopback SOCKS5 hop.
    if "--proxy" in args:
        index = args.index("--proxy") + 1
        args[index] = start_forwarder(args[index])
    env = dict(
        os.environ,
        OBSCURA_ALLOW_PRIVATE_NETWORK="1",
        OBSCURA_BLOCK_TRACKERS="0",
        HOME="/tmp/hercules-browser-home",
    )
    # Obscura must use only the explicit --proxy arg, never ambient proxy env.
    for key in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
        "http_proxy", "https_proxy", "all_proxy", "no_proxy",
        "HERCULES_BROWSER_UPSTREAM",
    ):
        env.pop(key, None)
    os.execve(
        "/usr/bin/setpriv",
        ["setpriv", f"--reuid={ENGINE_UID}", f"--regid={ENGINE_UID}",
         "--clear-groups", "--bounding-set=-all", "--inh-caps=-all",
         "--ambient-caps=-all", "--no-new-privs", ENGINE, *args],
        env,
    )


def main():
    # Must start as root so the setpriv drop is meaningful; never run Obscura as
    # root by falling through.
    if os.geteuid() != 0:
        raise SystemExit("browser launcher must start as root to drop privileges")
    launch(sys.argv[1:])


if __name__ == "__main__":
    main()
