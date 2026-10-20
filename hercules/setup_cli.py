"""The host setup CLI is never imported or run by an MCP connection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hercules.setup.clients import CLIENTS
from hercules.setup.documents import ConfigError
from hercules.setup.engine import Engine
from hercules.setup.transaction import SetupError


def parser():
    result = argparse.ArgumentParser(
        prog="hercules-setup",
        description="Install or repair only the selected local MCP client. Runtime downloads and tests are separate explicit phases.",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--client", required=True, choices=CLIENTS)
    common.add_argument("--scope", choices=("user", "project"))
    common.add_argument("--project", type=Path, default=Path.cwd())
    common.add_argument(
        "--root", type=Path, help="Managed data root (also isolates setup state)"
    )
    common.add_argument("--state", type=Path)
    common.add_argument("--config-path", type=Path)
    common.add_argument("--skill-path", type=Path)
    common.add_argument("--capabilities")
    common.add_argument("--platform", choices=("linux/amd64", "linux/arm64"))
    common.add_argument("--docker-network", help="Selected client's isolated Docker bridge network (default bridge for new browser installations)")
    common.add_argument("--build-ca-bundle", type=Path)
    common.add_argument(
        "--source",
        type=Path,
        help="Explicit local Git source for offline/development installs",
    )
    common.add_argument(
        "--yes",
        action="store_true",
        help="Confirm this setup operation; never changes harness permissions",
    )
    common.add_argument(
        "--json", action="store_true", help="Emit one non-secret JSON report on stdout"
    )
    common.set_defaults(reinstall=False, runtime=False, pending=False)
    commands = result.add_subparsers(dest="command", required=True)
    for command in ("status", "install", "repair", "resume", "verify"):
        child = commands.add_parser(command, parents=[common])
        if command == "install":
            child.add_argument("--reinstall", action="store_true")
        if command == "verify":
            child.add_argument("--pending", action="store_true", help="Verify the staged candidate without replacing the working client registration")
            child.add_argument(
                "--runtime",
                action="store_true",
                help="Explicitly start/stop a disposable local container and run harmless local tools",
            )
    runtime = commands.add_parser("runtime")
    prepare = runtime.add_subparsers(dest="runtime_command", required=True).add_parser(
        "prepare", parents=[common]
    )
    prepare.add_argument("--image-source", choices=("auto", "prebuilt", "build"), default="auto",
                         help="Reuse a verified cache, pull a locked release digest, or explicitly build the full image")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    engine = None
    exit_code = 0
    try:
        engine = Engine(args)
        report = engine.execute(args.command)
        exit_code = 1 if report.get("status") == "error" else 0
    except KeyboardInterrupt:
        report = {
            **(engine.result if engine else {}),
            "status": "interrupted",
            "next_action": "Run status, then resume after resolving the interruption.",
        }
        exit_code = 130
    except ConfigError as exc:
        report = {
            **(engine.result if engine else {}),
            "status": "error",
            "error_type": "client_configuration_invalid",
            "message": str(exc),
            "next_action": "Select the effective --config-path or use --client generic for a manual STDIO export.",
        }
        exit_code = 1
    except Exception as exc:
        report = {
            **(engine.result if engine else {}),
            "status": "error",
            "error_type": exc.code if isinstance(exc, SetupError) else "setup_failed",
            "message": str(exc)
            if isinstance(exc, SetupError)
            else f"Setup stopped safely ({type(exc).__name__}).",
            "next_action": exc.next_action
            if isinstance(exc, SetupError)
            else "Run status and inspect the failed phase before resuming.",
        }
        exit_code = 1
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for key in (
            "status",
            "phase",
            "host",
            "registration",
            "runtime_preparation",
            "verification",
            "cleanup",
            "message",
            "next_action",
        ):
            if key in report:
                print(f"{key.replace('_', ' ').capitalize()}: {report[key]}")
        if "export" in report:
            print(json.dumps(report["export"], indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
