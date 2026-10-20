#!/usr/bin/python3
"""Minimal Obscura launcher for host networking — NO SSRF boundary.

The container runs on the host network, so there is no isolated bridge for a
firewall/SOCKS gateway. This launcher does the ONE thing that still matters:
drop privileges to the unprivileged engine UID before exec'ing the real Obscura
binary. It installs no gateway, no nftables, and no target policy — the browser
can reach host-local, LAN, and cloud-metadata services. The MCP server's agent
instructions warn the agent to only browse authorized targets.

agent-browser invokes this as:  serve --host 127.0.0.1 --port <N> [--proxy <url>]
Any --proxy is the operator's own upstream (set by the host-side browser tool);
it is passed straight through.
"""

import os
import sys

ENGINE = "/opt/hercules/browser/obscura"
ENGINE_UID = 19731


def launch(args):
    # Allow only the agent-browser --version probe and the loopback serve form.
    # Both still go through setpriv below so the engine never runs as root.
    if args != ["--version"] and (
        len(args) < 5 or args[:3] != ["serve", "--host", "127.0.0.1"]
    ):
        raise ValueError("unsupported engine launch")
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
