"""
Nuclei template-based vulnerability scanning tools for Hercules MCP server.

Supports running built-in and custom templates with JSON output,
and authoring custom YAML templates with path traversal protection.
"""

from __future__ import annotations

import logging
import os
import shlex
import uuid
import json
from typing import TYPE_CHECKING

from fastmcp import Context
from hercules.core.guidance import (
    TOOL_DESCRIPTIONS,
    missing_param_error,
    path_error,
    target_error,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.nuclei")


def _has_flag(extra_args: str, *flags: str) -> bool:
    try:
        tokens = shlex.split(extra_args or "")
    except ValueError:
        tokens = (extra_args or "").split()
    return any(token == flag or token.startswith(f"{flag}=") for token in tokens for flag in flags)


def _compact_nuclei_jsonl(stdout: str, include_raw: bool) -> tuple[str, list[dict]]:
    matches: list[dict] = []
    compact_lines: list[str] = []
    omit_fields = {"template-encoded", "request", "response", "curl-command"}

    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("{"):
            compact_lines.append(line)
            continue
        try:
            item = json.loads(stripped)
        except json.JSONDecodeError:
            compact_lines.append(line)
            continue

        if not include_raw:
            for field in omit_fields:
                item.pop(field, None)
        matches.append(item)
        compact_lines.append(json.dumps(item, separators=(",", ":"), sort_keys=True))

    return "\n".join(compact_lines), matches


def register_nuclei_tools(mcp: "FastMCP") -> None:

    @mcp.tool(description=TOOL_DESCRIPTIONS["nuclei_run"])
    async def nuclei_run(
        targets: str,
        templates: str = "",
        severity: str = "",
        tags: str = "",
        rate_limit: int = 150,
        extra_args: str = "",
        include_raw: bool = False,
        ctx: Context = None,
    ) -> dict:
        """Run nuclei vulnerability scanner against targets."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        # Validate each target
        target_values = [t.strip() for t in (targets or "").split(",") if t.strip()]
        if not target_values:
            return missing_param_error(
                "nuclei_run",
                "targets",
                examples="nuclei_run(targets='http://host', templates='/opt/workspace/nuclei-templates/check.yaml')",
            )
        for t in target_values:
            try:
                config.validate_target(t)
            except ValueError as exc:
                return target_error("nuclei_run", t, exc, config)

        parts = ["nuclei", "-jsonl", "-nc"]
        if not include_raw:
            for flag in ("-or", "-ot", "-silent", "-duc"):
                if not _has_flag(extra_args, flag):
                    parts.append(flag)
        if len(target_values) > 1:
            target_file = f"/opt/workspace/nuclei-targets/{uuid.uuid4().hex[:8]}.txt"
            await docker.write_file(target_file, "\n".join(target_values) + "\n")
            parts.append(f"-list {shlex.quote(target_file)}")
        else:
            parts.append(f"-target {shlex.quote(target_values[0])}")
        parts.append(f"-rate-limit {rate_limit}")
        if templates:
            parts.append(f"-t {shlex.quote(templates)}")
        if severity:
            parts.append(f"-severity {severity}")
        if tags:
            parts.append(f"-tags {tags}")
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("nuclei_run"):
            result = await docker.exec_command(
                cmd,
                timeout=600,
                tool_name="nuclei",
                compact_output=not include_raw,
                preserve_raw=not include_raw,
            )

        compact_stdout, matches = _compact_nuclei_jsonl(result.stdout, include_raw=include_raw)
        result.stdout = compact_stdout
        response = {"tool": "nuclei_run", "targets": targets, **result.to_dict()}
        if matches:
            response["matches"] = matches
            response["match_count"] = len(matches)
        return response

    @mcp.tool(description=TOOL_DESCRIPTIONS["nuclei_write_template"])
    async def nuclei_write_template(path: str, content: str, ctx: Context) -> dict:
        """Write custom nuclei YAML template to workspace."""
        docker = ctx.lifespan_context["docker"]

        # Path traversal sanitization
        safe_path = os.path.normpath(path).replace("\\", "/")
        # Remove leading slashes
        safe_path = safe_path.lstrip("/")
        if ".." in safe_path:
            return path_error(
                "nuclei_write_template",
                path,
                f"Path traversal detected in template path: {path}",
                examples="nuclei_write_template(path='custom/check.yaml', content='id: custom-check\\ninfo: ...')",
            )

        container_path = f"/opt/workspace/nuclei-templates/{safe_path}"
        await docker.write_file(container_path, content)

        return {
            "tool": "nuclei_write_template",
            "path": container_path,
            "message": f"Template written to {container_path}",
        }
