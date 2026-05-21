from fastmcp import FastMCP
from mcp.types import CallToolRequest
import asyncio

mcp = FastMCP("test")

@mcp.tool()
def my_tool(x: int) -> str:
    return f"x is {x}"

# Setup the patch
original_handler = mcp._mcp_server.request_handlers[CallToolRequest]

async def patched_call_tool(request: CallToolRequest, *args, **kwargs):
    tool_name = request.params.name
    tool_args = request.params.arguments or {}
    
    # Get the tool from FastMCP
    tool = await mcp.get_tool(tool_name)
    if tool:
        expected_keys = tool.parameters.get("properties", {}).keys()
        stripped_args = {k: v for k, v in tool_args.items() if k in expected_keys}
        
        # Log if we stripped anything
        dropped = set(tool_args.keys()) - set(stripped_args.keys())
        if dropped:
            print(f"Stripped unknown args: {dropped}")
            
        request.params.arguments = stripped_args
        
    return await original_handler(request, *args, **kwargs)

mcp._mcp_server.request_handlers[CallToolRequest] = patched_call_tool

# Simulate a call
async def test():
    from mcp.types import CallToolRequestParams
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(
            name="my_tool",
            arguments={"x": 5, "waitForPreviousTools": False, "_meta": {"foo": "bar"}}
        )
    )
    result = await mcp._mcp_server.request_handlers[CallToolRequest](req)
    print(result.content[0].text)

asyncio.run(test())
