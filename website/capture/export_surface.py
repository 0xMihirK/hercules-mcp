"""Export the real FastMCP schemas, without entering the Docker lifespan."""
import asyncio
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# Capture the full public profile independently of the operator's runtime profile.
os.environ.update(SKIP_METASPLOIT="false", HERCULES_DISABLED_TOOLS="", HERCULES_INSTALLED_CAPABILITIES="")
from hercules.main import mcp

async def export():
    tools = await mcp.list_tools(run_middleware=False)
    resources = await mcp.list_resources(run_middleware=False)
    payload = {
        "tools": [tool.to_mcp_tool().model_dump(mode="json", exclude_none=True) for tool in tools],
        "resources": [resource.to_mcp_resource().model_dump(mode="json", exclude_none=True) for resource in resources],
    }
    assert len(payload["tools"]) == 46 and len(payload["resources"]) == 7
    target = Path(__file__).with_name("hercules-surface.json")
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Exported {len(tools)} real tool schemas and {len(resources)} resources")

asyncio.run(export())
