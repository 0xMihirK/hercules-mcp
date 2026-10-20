"""Verified workspace copies and narrowly scoped, journaled client cutover."""

from __future__ import annotations

import json
import os
from contextlib import ExitStack
from pathlib import Path

from hercules.core.config_io import (
    atomic_write_private_bytes,
    dotenv_path,
    load_setup_state,
    read_dotenv_value,
    render_dotenv,
)
from hercules.core.instance_lock import workspace_lock, workspace_state_path
from hercules.core.setup_info import setup_state_locations
from hercules.core.workspace import WorkspaceManager, utc_now
from hercules.setup.clients import resolve
from hercules.setup.documents import edit, lookup, parse
from hercules.setup.transaction import (
    InstallLock,
    SetupError,
    digest,
    new_transaction,
    read,
    recover,
)


def _same(value, root):
    return bool(value) and Path(value).expanduser().resolve() == root


def _installation_root(path, state, association):
    supplied = state.get("installation_root") or association.get("installation_root")
    checkout = Path(association.get("checkout", path.parent))
    root = (
        Path(supplied)
        if supplied
        else (
            checkout.parent.parent
            if checkout.parent.name == "releases"
            else path.parent
        )
    )
    if not root.is_absolute():
        raise ValueError(
            "setup installation root must be absolute; repair its explicit state before migration"
        )
    return root


def _discover(config, source, states, clients, project):
    selected_states = {Path(path).resolve() for path in states}
    paths = set(selected_states)
    paths.update(Path(path) for path in setup_state_locations(project).values())
    discovered = []
    matched = set()
    occurrences = {}
    for path in sorted(paths):
        state, errors = load_setup_state(path)
        if errors:
            raise ValueError(f"invalid setup state {path}: {'; '.join(errors)}")
        if not state:
            continue
        associations = state.get("registrations", {}) or {
            client: dict(state) for client in state.get("clients", [])
        }
        entries = []
        for client, association in associations.items():
            configured = association.get("config_path")
            if not configured and len(association.get("config_paths", [])) == 1:
                configured = association["config_paths"][0]
            if not configured:
                if _same(association.get("workspace_root"), source):
                    raise ValueError(
                        f"{client} has no inspectable registration; update its explicit export/config before migration"
                    )
                continue
            adapter = resolve(
                client,
                association.get("scope", state.get("scope", "user")),
                project,
                Path(configured),
            )
            entry = adapter.entry()
            if not isinstance(entry, dict):
                raise ValueError(  # noqa: TRY004 -- migration reports invalid configuration through ValueError
                    f"{client} registration cannot be verified: {configured}"
                )
            env_key = "environment" if client == "opencode" else "env"
            environment = entry.get(env_key, {})
            if not isinstance(environment, dict):
                raise ValueError(f"{client} environment is not an object")  # noqa: TRY004
            env_file = environment.get("HERCULES_ENV_FILE") or association.get(
                "env_file"
            )
            env_file = (
                Path(env_file) if env_file else Path(association["checkout"]) / ".env"
            )
            effective = (
                environment.get("HERCULES_WORKSPACE_ROOT")
                or read_dotenv_value(env_file, "HERCULES_WORKSPACE_ROOT")
                or association.get("workspace_root")
            )
            if not _same(effective, source):
                continue
            if client not in clients:
                raise ValueError(
                    f"{client} still references the source; include it with --client or leave the source/configuration unchanged"
                )
            if selected_states and path not in selected_states:
                raise ValueError(
                    f"{client} source registration in {path} was not selected; include its --state explicitly"
                )
            occurrences[client] = occurrences.get(client, 0) + 1
            if not selected_states and occurrences[client] > 1:
                raise ValueError(
                    f"{client} has multiple affected scopes/profiles; select their --state paths explicitly"
                )
            matched.add(client)
            entries.append((client, association, adapter, entry, env_key, env_file))
        if entries:
            discovered.append((path, state, associations, entries))
    missing = set(clients) - matched
    if missing:
        raise ValueError(
            f"selected registrations not found for {', '.join(sorted(missing))}; supply their --state paths"
        )
    return discovered


def migrate(config, manager, destination, *, states=(), clients=(), project=None):
    source = manager.root
    destination = Path(destination).expanduser().resolve()
    project = Path(project or config.project_root).resolve()
    coordination = workspace_state_path(source, ".migration-state")
    with ExitStack() as locks:
        # Setup uses installation locks before workspace operations too.
        initial = _discover(config, source, states, clients, project)
        installations = {
            _installation_root(path, state, entries[0][1])
            for path, state, _, entries in initial
        }
        for root in sorted(installations | {coordination}):
            locks.enter_context(InstallLock(root / "setup.lock"))
            recover(root)
        for root in sorted(
            {source, destination}, key=lambda path: os.path.normcase(str(path))
        ):
            locks.enter_context(workspace_lock(root))
        discovered = _discover(config, source, states, clients, project)
        if [(str(path), state) for path, state, _, _ in initial] != [
            (str(path), state) for path, state, _, _ in discovered
        ]:
            raise ValueError(
                "setup associations changed during discovery; retry without moving evidence"
            )
        effective_env = dotenv_path(config.project_root)
        configured_root = read_dotenv_value(effective_env, "HERCULES_WORKSPACE_ROOT")
        if not discovered and (
            (configured_root and not _same(configured_root, source))
            or (not configured_root and config.resolved_workspace_root != source)
        ):
            raise ValueError(
                "effective dotenv/configuration belongs to another workspace; select the matching HERCULES_ENV_FILE or explicit --state"
            )
        env_updates = {}
        writes = {}
        for path, state, associations, entries in discovered:
            updated = json.loads(json.dumps(state))
            updated["registrations"] = json.loads(json.dumps(associations))
            for client, association, adapter, entry, env_key, env_file in entries:
                before = read(adapter.path)
                text = (before or b"").decode("utf-8-sig")
                if lookup(parse(text, adapter.format), adapter.keys) != entry:
                    raise ValueError(
                        f"{client} registration changed during discovery; retry"
                    )
                replacement = dict(entry)
                replacement[env_key] = {
                    **entry.get(env_key, {}),
                    "HERCULES_WORKSPACE_ROOT": str(destination),
                }
                if adapter.path in writes:
                    raise ValueError(
                        "multiple selected profiles share a registration file; select their explicit profiles separately"
                    )
                writes[adapter.path] = (
                    before,
                    edit(text, adapter.format, adapter.keys, replacement).encode(),
                    {"keys": adapter.keys, "format": adapter.format},
                )
                updated["registrations"][client] = {
                    **association,
                    "workspace_root": str(destination),
                }
                env_updates[env_file.resolve()] = str(destination)
            if _same(updated.get("workspace_root"), source):
                updated["workspace_root"] = str(destination)
            writes[path] = (read(path), json.dumps(updated, indent=2).encode(), None)
        if not discovered or _same(
            read_dotenv_value(effective_env, "HERCULES_WORKSPACE_ROOT"), source
        ):
            env_updates[effective_env.resolve()] = str(destination)
        # A shared dotenv must not redirect an unselected association implicitly.
        for state_path in {
            *[Path(path).resolve() for path in states],
            *[Path(path) for path in setup_state_locations(project).values()],
        }:
            state, _ = load_setup_state(state_path)
            for client, association in state.get("registrations", {}).items():
                if (
                    client not in clients
                    and association.get("env_file")
                    and Path(association["env_file"]).resolve() in env_updates
                ):
                    raise ValueError(
                        f"dotenv is shared with unselected {client}; include that registration explicitly"
                    )
        for path, target in env_updates.items():
            before = read(path)
            writes[path] = (
                before,
                render_dotenv(
                    (before or b"").decode(), {"HERCULES_WORKSPACE_ROOT": target}
                ).encode(),
                None,
            )
        tx = new_transaction(
            coordination,
            {
                "command": "workspace-migrate",
                "source": str(source),
                "destination": str(destination),
            },
        )
        tx.data["retained"] = [str(source), str(destination)]
        tx.save()

        def record_staging(path, *, created):
            details = path.stat(follow_symlinks=False) if created else None
            tx.data["workspace_staging"] = {
                "path": str(path),
                "device": details.st_dev if details else None,
                "inode": details.st_ino if details else None,
            }
            tx.save()

        try:
            result = manager.migrate(destination, staging_callback=record_staging)
            if not result.get("migrated"):
                tx.commit()
                return result
            tx.phase("activating")
            for path, (before, after, entry) in writes.items():
                tx.write(path, after, expected=before, entry=entry)
            for _, _, _, entries in discovered:
                for client, _, adapter, _, env_key, _ in entries:
                    if not _same(
                        adapter.entry().get(env_key, {}).get("HERCULES_WORKSPACE_ROOT"),
                        destination,
                    ):
                        raise ValueError(f"{client} cutover could not be verified")
            receipt = {
                "schema_version": 1,
                "source": str(source),
                "destination": str(destination),
                "states": [str(path) for path, _, _, _ in discovered],
                "clients": list(clients),
                "project": str(project),
                "completed_at": utc_now(),
                "configuration": {str(path): digest(read(path)) for path in writes},
            }
            receipt_path = workspace_state_path(source, ".migration.json")
            tx.write(
                receipt_path, json.dumps(receipt).encode(), expected=read(receipt_path)
            )
            tx.commit()
        except BaseException as exc:
            if tx.data["phase"] != "committed" and tx.rollback():
                raise SetupError(
                    "rollback_conflict",
                    "Migration rollback encountered concurrent edits; both workspaces and exact backups were retained",
                    f"Review {tx.directory} before retrying.",
                ) from exc
            raise
        finally:
            tx.cleanup_temporaries()
        result.update(
            configuration_updated=[str(path) for path in writes],
            selected_clients=list(clients),
            source_retained=True,
            transaction=str(tx.path),
            receipt=str(receipt_path),
            reload_instructions=[
                adapter.reload
                for _, _, _, entries in discovered
                for _, _, adapter, _, _, _ in entries
            ],
        )
        return result


def retire(config, manager, *, references_reviewed=False):
    if not references_reviewed:
        raise ValueError(
            "retirement requires --references-reviewed: verify custom/unlisted clients and old launchers no longer reference the source"
        )
    receipt_path = workspace_state_path(manager.root, ".migration.json")
    receipt = json.loads(receipt_path.read_text())
    if receipt.get("schema_version") != 1 or receipt.get("source") != str(manager.root):
        raise ValueError("retirement requires an exact verified migration receipt")
    destination = Path(receipt["destination"]).resolve()
    with ExitStack() as locks:
        coordination = workspace_state_path(manager.root, ".migration-state")
        installations = {coordination}
        for path in receipt["states"]:
            state, errors = load_setup_state(Path(path))
            if errors:
                raise ValueError("setup state is no longer valid; source retained")
            associations = state.get("registrations", {})
            for association in associations.values():
                installations.add(_installation_root(Path(path), state, association))
        for root in sorted(installations):
            locks.enter_context(InstallLock(root / "setup.lock"))
            recover(root)
        for root in sorted(
            {manager.root, destination}, key=lambda path: os.path.normcase(str(path))
        ):
            locks.enter_context(workspace_lock(root))
        if (
            not manager.root.exists()
            and workspace_state_path(manager.root, ".retired.json").exists()
        ):
            return {
                "source": str(manager.root),
                "destination": str(destination),
                "source_deleted": True,
                "already_retired": True,
                "destination_verification": "last_recorded",
            }
        for path, expected in receipt["configuration"].items():
            if digest(read(Path(path))) != expected:
                raise ValueError(
                    "configuration changed after migration; revalidate cutover before retirement"
                )
        # No registration in the known states may still point at the source.
        _discover(config, manager.root, receipt["states"], (), Path(receipt["project"]))
        manager.assert_quiescent()
        if any(session["pinned"] for session in manager.list_sessions()):
            raise ValueError(
                "pinned source evidence cannot be retired; preserve it or unpin explicitly"
            )
        owned_names = {
            session["session_id"]
            for session in manager.list_sessions()
            if session["owned"]
        }
        for item in manager.root.iterdir():
            if item.name not in owned_names and not (
                item.is_file()
                and (
                    item.name == "hercules.log" or item.name.startswith("hercules.log.")
                )
            ):
                raise ValueError(
                    f"unowned root entry {item.name!r} prevents retirement; original retained"
                )
        target = WorkspaceManager(destination)
        target.assert_quiescent()
        source_anchor = manager._open_root_anchor()
        target_anchor = target._open_root_anchor()
        try:
            source_inventory = manager._inventory_anchor(source_anchor)[2]
            target_inventory = target._inventory_anchor(target_anchor)[2]
            if any(
                target_inventory.get(path) != checksum
                for path, checksum in source_inventory.items()
            ):
                raise ValueError(
                    "destination no longer contains every source file unchanged; source retained"
                )
            atomic_write_private_bytes(
                workspace_state_path(manager.root, ".retired.json"),
                json.dumps(receipt).encode(),
            )
        finally:
            manager._close_anchor(source_anchor)
            target._close_anchor(target_anchor)
        parent, name = WorkspaceManager._external_parent(manager.root)
        try:
            manager._remove_tree_at(parent, name)
        except OSError as exc:
            raise SetupError(
                "retirement_incomplete",
                "Source cleanup was interrupted; the old root is fenced and remaining evidence is retained. The verified destination was not removed.",
                "Resolve the exact source file lock, then rerun retire --references-reviewed; do not broadly delete files.",
            ) from exc
        finally:
            manager._close_anchor(parent)
        return {
            "source": str(manager.root),
            "destination": str(destination),
            "source_deleted": True,
            "recoverable_from": str(destination),
        }
