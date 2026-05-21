from fastmcp import FastMCP
import inspect
from functools import wraps

def allow_parallel(func):
    @wraps(func)
    async def wrapper(*args, waitForPreviousTools: bool = False, wait_for_previous: bool = False, **kwargs):
        return await func(*args, **kwargs)
    
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    params.extend([
        inspect.Parameter("waitForPreviousTools", inspect.Parameter.KEYWORD_ONLY, default=False, annotation=bool),
        inspect.Parameter("wait_for_previous", inspect.Parameter.KEYWORD_ONLY, default=False, annotation=bool)
    ])
    wrapper.__signature__ = sig.replace(parameters=params)
    return wrapper

mcp = FastMCP("test")

@mcp.tool()
@allow_parallel
async def my_tool(x: int) -> str:
    return f"x is {x}"

print(mcp._tool_manager.get_tool("my_tool").parameters)
