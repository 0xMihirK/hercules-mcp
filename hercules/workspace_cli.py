"""Host-side workspace inspection, retention, and migration commands."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from hercules.core.config import HerculesConfig
from hercules.core.workspace import WorkspaceManager


def _manager(args: argparse.Namespace) -> tuple[HerculesConfig, WorkspaceManager]:
    config = HerculesConfig.from_env()
    root = (
        Path(args.root).expanduser().resolve()
        if getattr(args, "root", "")
        else config.resolved_workspace_root
    )
    return config, WorkspaceManager(
        root,
        max_inline_bytes=config.max_inline_file_bytes,
    )


def _running_job_sessions(manager: WorkspaceManager) -> set[str]:
    running: set[str] = set()
    for session in manager.list_sessions():
        jobs = manager.session_path(session["session_id"]) / "jobs"
        if not jobs.is_dir():
            continue
        try:
            metadata_files = list(jobs.glob("*.json"))
        except OSError:
            continue
        for path in metadata_files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                continue
            if isinstance(payload, dict) and payload.get("state") in {
                "starting",
                "running",
                "terminating",
            }:
                running.add(session["session_id"])
                break
    return running


def _emit(payload: dict[str, Any] | list[dict[str, Any]], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if isinstance(payload, list):
        if not payload:
            print("No Hercules workspace sessions found.")
            return
        for item in payload:
            flags = []
            if item.get("is_active") or item.get("state") == "active":
                flags.append("active")
            if item.get("pinned"):
                flags.append("pinned")
            if not item.get("owned"):
                flags.append("legacy/unowned")
            suffix = f" ({', '.join(flags)})" if flags else ""
            print(
                f"{item['session_id']}: {item['file_count']} files, "
                f"{item['total_bytes']} bytes{suffix}"
            )
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hercules-workspace",
        description="Inspect and safely manage Hercules workspace sessions.",
    )
    parser.add_argument(
        "--root",
        default="",
        help="Override the configured workspace root for this invocation.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List session usage and ownership.")
    list_parser.add_argument("--json", action="store_true")

    for action in ("pin", "unpin"):
        action_parser = subparsers.add_parser(action, help=f"{action.title()} a session.")
        action_parser.add_argument("session_id")
        action_parser.add_argument("--json", action="store_true")

    prune = subparsers.add_parser(
        "prune",
        help="Preview or apply retention to inactive, owned, unpinned sessions.",
    )
    prune.add_argument("--older-than", type=int, default=0, metavar="DAYS")
    prune.add_argument("--max-sessions", type=int, default=0)
    prune.add_argument("--max-bytes", type=int, default=0)
    prune.add_argument(
        "--apply",
        action="store_true",
        help="Actually remove selected sessions. Without this flag the command is a dry run.",
    )
    prune.add_argument("--json", action="store_true")

    migrate = subparsers.add_parser(
        "migrate",
        help="Copy and verify the workspace root, then update the checkout .env.",
    )
    migrate.add_argument("--destination", required=True)
    migrate.add_argument("--delete-source", action="store_true")
    migrate.add_argument("--json", action="store_true")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any] | list[dict[str, Any]]:
    config, manager = _manager(args)
    if args.command == "list":
        return manager.list_sessions(running_jobs=_running_job_sessions(manager))
    if args.command in {"pin", "unpin"}:
        manifest = manager.pin(args.session_id, args.command == "pin")
        return {
            "session_id": args.session_id,
            "pinned": bool(manifest["pinned"]),
            "workspace_root": str(manager.root),
        }
    if args.command == "prune":
        if args.older_than < 0 or args.max_sessions < 0 or args.max_bytes < 0:
            raise ValueError("retention values must be zero or greater")
        return manager.prune(
            older_than_days=args.older_than,
            max_sessions=args.max_sessions,
            max_bytes=args.max_bytes,
            apply=args.apply,
            running_jobs=_running_job_sessions(manager),
        )
    if args.command == "migrate":
        destination = Path(args.destination).expanduser().resolve()
        result = manager.migrate(
            destination,
            delete_source=bool(args.delete_source),
        )
        if result.get("migrated"):
            from hercules.installer import upsert_env

            upsert_env(
                config.project_root / ".env",
                {"HERCULES_WORKSPACE_ROOT": os.fspath(destination)},
            )
            result["configuration_updated"] = str(config.project_root / ".env")
        return result
    raise ValueError(f"unsupported workspace command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = run(args)
    except Exception as exc:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1
    _emit(payload, as_json=bool(getattr(args, "json", False)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
