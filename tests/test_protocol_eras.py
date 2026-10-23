"""The same cold STDIO server supports both MCP protocol eras."""

import asyncio
import os
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters


@pytest.mark.parametrize("mode", ["legacy", "2026-07-28"])
def test_cold_stdio_protocol_eras(mode, tmp_path):
    root = Path(__file__).resolve().parents[1]

    async def scenario():
        server = StdioServerParameters(
            command=sys.executable,
            args=["-m", "hercules.main"],
            cwd=str(root),
            env={**os.environ, "HERCULES_WORKSPACE_ROOT": str(tmp_path)},
        )
        async with Client(server, mode=mode) as client:
            tools = await client.list_tools()
            resources = await client.list_resources()
            templates = await client.list_resource_templates()
            cold = await client.call_tool("shell_exec", {"command": "true"})
            return (
                client.protocol_version,
                {tool.name for tool in tools.tools},
                {str(resource.uri) for resource in resources.resources},
                {template.uri_template for template in templates.resource_templates},
                cold.structured_content,
            )

    version, tools, resources, templates, cold = asyncio.run(scenario())
    assert version == ("2025-11-25" if mode == "legacy" else "2026-07-28")
    assert len(tools) == 47
    assert len(resources) == 5
    assert not any(uri.startswith("resource://agent_skills/") for uri in resources)
    assert templates == {
        "resource://post_exploitation/gtfobins/{name}",
        "resource://post_exploitation/lolbas/{name}",
    }
    assert cold["error_type"] == "runtime_not_started"
    assert not any(path.is_dir() for path in tmp_path.iterdir())
