"""
File management tools for Hercules MCP server.

Provides granular control over files inside the container workspace.
"""

from __future__ import annotations

import base64
import binascii
import logging
import posixpath
import re
from types import SimpleNamespace
from typing import TYPE_CHECKING, Literal

from fastmcp import Context

from hercules.core.guidance import TOOL_DESCRIPTIONS, usage_error

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.file")


def _resolve_path(path: str) -> str:
    """Resolve relative paths to the container's workspace directory."""
    if any(ch in path for ch in ("\r", "\n", "\x00")):
        raise ValueError("path contains forbidden control characters")
    if "\\" in path:
        raise ValueError("workspace paths must use forward slashes")
    if re.match(r"^[a-zA-Z]:", path) or path.startswith("//"):
        raise ValueError("host drive and network paths are not valid workspace paths")
    if any(part == ".." for part in path.split("/")):
        raise ValueError("workspace path traversal is not allowed")
    candidate = path if path.startswith("/") else f"/opt/workspace/{path}"
    normalized = posixpath.normpath(candidate)
    if normalized != "/opt/workspace" and not normalized.startswith("/opt/workspace/"):
        raise ValueError("workspace file paths must stay under /opt/workspace")
    return normalized


def _parse_mode(mode: int | str) -> int:
    """Accept JSON-friendly file mode values and normalize to an int."""
    if isinstance(mode, int):
        parsed = mode
    elif isinstance(mode, str):
        value = mode.strip().lower()
        if value.startswith("0") or (
            value.isdigit()
            and 3 <= len(value) <= 4
            and all(c in "01234567" for c in value)
        ):
            parsed = int(value, 8)
        elif value.isdigit():
            parsed = int(value, 10)
        else:
            raise ValueError("mode must be an integer or octal string such as '0644' or '0o755'")
    else:
        # Tool input validation consistently reports ValueError to MCP callers.
        raise ValueError(  # noqa: TRY004
            "mode must be an integer or octal string such as '0644' or '0o755'"
        )

    if parsed < 0 or parsed > 0o7777:
        raise ValueError("mode must be between 0 and 0o7777")
    return parsed


def _format_mode(mode: int) -> str:
    return format(mode, "04o")


def register_file_tools(mcp: FastMCP) -> None:

    @mcp.tool(description=TOOL_DESCRIPTIONS["workspace_read_file"])
    async def workspace_read_file(
        path: str,
        encoding: Literal["text", "base64"] = "text",
        offset: int = 0,
        max_bytes: int = 0,
        ctx: Context = None,
    ) -> dict:
        """Read the contents of a file inside the container workspace."""
        docker = ctx.lifespan_context["docker"]
        try:
            path = _resolve_path(path)
        except ValueError as exc:
            return usage_error(
                "workspace_read_file",
                "invalid_options",
                str(exc),
                received={"path": path},
                expected="A relative path or absolute path under /opt/workspace.",
            )

        if encoding not in {"text", "base64"}:
            return usage_error(
                "workspace_read_file",
                "invalid_options",
                "Invalid encoding for workspace_read_file.",
                received={"encoding": encoding},
                expected={"encoding": ["text", "base64"]},
                examples=[
                    "workspace_read_file(path='notes.txt')",
                    "workspace_read_file(path='payload.exe', encoding='base64')",
                ],
            )
        if offset < 0 or max_bytes < 0:
            return usage_error(
                "workspace_read_file",
                "invalid_options",
                "offset and max_bytes must be zero or greater.",
                received={"offset": offset, "max_bytes": max_bytes},
                expected={"offset": "integer >= 0", "max_bytes": "integer >= 0"},
            )

        try:
            if hasattr(docker, "read_file_chunk"):
                result = await docker.read_file_chunk(
                    path,
                    offset=offset,
                    max_bytes=max_bytes,
                )
            else:
                if offset or max_bytes:
                    raise ValueError(
                        "this compatibility runtime does not support paged reads"
                    )
                if encoding == "text":
                    data = (await docker.read_file(path)).encode("utf-8")
                else:
                    data = await docker.read_file_bytes(path)
                result = SimpleNamespace(
                    data=data,
                    total_bytes=len(data),
                    offset=0,
                    truncated=False,
                    next_offset=None,
                )
            response = {
                "tool": "workspace_read_file",
                "path": path,
                "encoding": encoding,
                "bytes": len(result.data),
                "total_bytes": result.total_bytes,
                "offset": result.offset,
                "truncated": result.truncated,
                "next_offset": result.next_offset,
            }
            if encoding == "text":
                response["content"] = result.data.decode("utf-8", errors="replace")
            else:
                response["content_base64"] = base64.b64encode(result.data).decode(
                    "ascii"
                )
            return response
        except Exception as exc:
            return {"tool": "workspace_read_file", "path": path, "error": str(exc)}

    @mcp.tool(description=TOOL_DESCRIPTIONS["workspace_write_file"])
    async def workspace_write_file(
        path: str,
        content: str = "",
        mode: int | str = 0o644,
        content_base64: str = "",
        ctx: Context = None,
    ) -> dict:
        """Write content to a file inside the container workspace (overwrites if exists)."""
        docker = ctx.lifespan_context["docker"]
        try:
            path = _resolve_path(path)
        except ValueError as exc:
            return usage_error(
                "workspace_write_file",
                "invalid_options",
                str(exc),
                received={"path": path},
                expected="A relative path or absolute path under /opt/workspace.",
            )

        try:
            applied_mode = _parse_mode(mode)
        except ValueError as exc:
            return usage_error(
                "workspace_write_file",
                "invalid_options",
                str(exc),
                received={"mode": mode},
                expected={"mode": ["0644", "0o644", 420]},
                examples=[
                    "workspace_write_file(path='script.sh', content='id\\n', mode='0755')",
                    "workspace_write_file(path='notes.txt', content='hello', mode=420)",
                ],
            )

        try:
            if content and content_base64:
                return usage_error(
                    "workspace_write_file",
                    "invalid_options",
                    "Provide either content or content_base64, not both.",
                    received={"content": "<provided>", "content_base64": "<provided>"},
                    expected="Exactly one content representation.",
                )
            if content_base64:
                payload = base64.b64decode(content_base64, validate=True)
                encoding = "base64"
            else:
                payload = content
                encoding = "text"
            await docker.write_file(path, payload, mode=applied_mode)
            byte_count = len(payload) if isinstance(payload, bytes) else len(payload.encode("utf-8"))
            return {
                "tool": "workspace_write_file",
                "path": path,
                "status": "success",
                "encoding": encoding,
                "bytes": byte_count,
                "applied_mode": _format_mode(applied_mode),
            }
        except (binascii.Error, ValueError) as exc:
            return usage_error(
                "workspace_write_file",
                "invalid_options",
                f"content_base64 is not valid base64: {exc}",
                received={"content_base64": "<provided>"},
                expected="Valid base64-encoded file bytes.",
                examples="workspace_write_file(path='payload.bin', content_base64='AAE=', mode='0644')",
            )
        except Exception as exc:
            return {"tool": "workspace_write_file", "path": path, "error": str(exc)}
