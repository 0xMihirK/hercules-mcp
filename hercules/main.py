"""
Hercules — AI-Orchestrated Kali MCP Server for Offensive Security.

Entry point. Uses composable FastMCP lifespans to separate Docker
container management from concurrency control. Registers all tool
modules and post-exploitation resources.
"""

from __future__ import annotations

import logging
import sys

from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from hercules.core.concurrency import ConcurrencyManager
from hercules.core.config import HerculesConfig
from hercules.core.docker_manager import DockerManager

# Tool registrations
from hercules.tools.network.nmap_tool import register_nmap_tools
from hercules.tools.exploitation.metasploit_tool import register_metasploit_tools
from hercules.tools.exploitation.sqlmap_tool import register_sqlmap_tools
from hercules.tools.web.nuclei_tool import register_nuclei_tools
from hercules.tools.exploitation.searchsploit_tool import register_searchsploit_tools
from hercules.tools.system.scripts_tool import register_scripts_tools
from hercules.tools.system.shell_tool import register_shell_tools
from hercules.tools.system.file_tool import register_file_tools
from hercules.tools.system.system_tool import register_system_tools

# New grouped categories
from hercules.tools.recon.recon_tool import register_recon_tools
from hercules.tools.web.web_scanner_tool import register_web_scanner_tools
from hercules.tools.network.network_tool import register_network_tools
from hercules.tools.cracking.cracking_tool import register_cracking_tools
from hercules.tools.cracking.wordlist_tool import register_wordlist_tools
from hercules.tools.ctf.ctf_tool import register_ctf_tools

# Resource registrations
from hercules.resources.post_exploitation import register_post_exploitation_resources

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("hercules")


# ---------------------------------------------------------------------------
# Composable lifespans
# ---------------------------------------------------------------------------

@lifespan
async def docker_lifespan(server):
    """Manage the Kali Docker container lifecycle."""
    config = HerculesConfig.from_env()
    docker_mgr = DockerManager(config)

    logger.info("=== Hercules starting ===")
    logger.info("Session ID: %s", docker_mgr.session_id)
    logger.info("Skip Metasploit: %s", config.skip_metasploit)
    logger.info("Preserve container: %s", config.preserve_container)

    await docker_mgr.start_container()
    logger.info("Workspace: workspace/%s/", docker_mgr.session_id)

    # Wait for msfrpcd if Metasploit is enabled
    msf_client = None
    if not config.skip_metasploit:
        try:
            msf_client = await docker_mgr.wait_for_msfrpcd()
        except TimeoutError:
            logger.warning("msfrpcd did not become ready — Metasploit tools will be unavailable.")

    try:
        yield {
            "docker": docker_mgr,
            "config": config,
            "msf_client": msf_client,
        }
    finally:
        logger.info("=== Hercules shutting down ===")
        await docker_mgr.stop_container()


@lifespan
async def concurrency_lifespan(server):
    """Initialize concurrency controls."""
    config = HerculesConfig.from_env()
    concurrency_mgr = ConcurrencyManager(
        max_heavy=config.max_concurrent_heavy,
        max_light=config.max_concurrent_light,
    )
    logger.info(
        "Concurrency limits: heavy=%d, light=%d",
        config.max_concurrent_heavy,
        config.max_concurrent_light,
    )
    yield {"concurrency": concurrency_mgr}


# ---------------------------------------------------------------------------
# FastMCP server — compose lifespans with | operator
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Hercules MCP – Kali MCP Server",
    lifespan=docker_lifespan | concurrency_lifespan,
)

# Register all tools
config = HerculesConfig.from_env()

register_nmap_tools(mcp)
if not config.skip_metasploit:
    register_metasploit_tools(mcp)
else:
    logger.info("SKIP_METASPLOIT=true: Metasploit tools will not be registered.")

register_sqlmap_tools(mcp)
register_nuclei_tools(mcp)
register_searchsploit_tools(mcp)
register_scripts_tools(mcp)
register_shell_tools(mcp)
register_file_tools(mcp)
register_system_tools(mcp)

# New categorized tools
register_recon_tools(mcp)
register_web_scanner_tools(mcp)
register_network_tools(mcp)
register_cracking_tools(mcp)
register_wordlist_tools(mcp)
register_ctf_tools(mcp)

# Register post-exploitation resources
register_post_exploitation_resources(mcp)

# ---------------------------------------------------------------------------
# Universal Parameter Leakage Interceptor
# ---------------------------------------------------------------------------
from mcp.types import CallToolRequest

original_call_tool_handler = mcp._mcp_server.request_handlers.get(CallToolRequest)
if original_call_tool_handler:
    async def patched_call_tool(request: CallToolRequest, *args, **kwargs):
        tool_name = request.params.name
        tool_args = request.params.arguments or {}
        
        try:
            tool = await mcp.get_tool(tool_name)
            if tool:
                expected_keys = tool.parameters.get("properties", {}).keys()
                stripped_args = {k: v for k, v in tool_args.items() if k in expected_keys}
                
                dropped = set(tool_args.keys()) - set(stripped_args.keys())
                if dropped:
                    logger.debug("Stripped unknown injected parameters from '%s': %s", tool_name, dropped)
                    
                request.params.arguments = stripped_args
        except Exception as exc:
            logger.debug("Interceptor failed to process tool '%s': %s", tool_name, exc)
            
        return await original_call_tool_handler(request, *args, **kwargs)

    mcp._mcp_server.request_handlers[CallToolRequest] = patched_call_tool

logger.info("Hercules MCP server configured with all tools and resources.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Run the Hercules MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
