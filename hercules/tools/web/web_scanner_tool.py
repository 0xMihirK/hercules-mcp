"""
Web scanning and fingerprinting tools for Hercules MCP server.

Includes httpx, whatweb, wafw00f, nikto, wpscan, arjun, and fuzz_dirs (gobuster/ffuf).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.web_scanner")

# SecLists path if mounted, fallback to Kali built-in dirbuster list
_DEFAULT_WORDLIST = "/usr/share/wordlists/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt"
_FALLBACK_WORDLIST = "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt"


def register_web_scanner_tools(mcp: "FastMCP") -> None:

    @mcp.tool()
    async def web_httpx(
        urls: str,
        title: bool = True,
        tech_detect: bool = True,
        status_code: bool = True,
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """HTTP probe (status, tech, title)."""
        docker = ctx.lifespan_context["docker"]
        concurrency = ctx.lifespan_context["concurrency"]

        url_str = "\\n".join([u.strip() for u in urls.split(",") if u.strip()])

        parts = ["httpx", "-silent"]
        if title:
            parts.append("-title")
        if tech_detect:
            parts.append("-tech-detect")
        if status_code:
            parts.append("-status-code")
        if extra_args:
            parts.append(extra_args)

        cmd = f"echo -e '{url_str}' | " + " ".join(parts)

        async with concurrency.acquire_light("web_httpx"):
            result = await docker.exec_command(cmd, timeout=300)

        return {"tool": "web_httpx", **result.to_dict()}

    @mcp.tool()
    async def web_whatweb(target: str, agg_level: int = 1, extra_args: str = "", ctx: Context = None) -> dict:
        """CMS/server fingerprinting (whatweb)."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target)

        cmd = f"whatweb -a {agg_level} --color=NEVER {extra_args} {target}"

        async with concurrency.acquire_light("web_whatweb"):
            result = await docker.exec_command(cmd, timeout=120, tool_name="whatweb")

        return {"tool": "web_whatweb", "target": target, **result.to_dict()}

    @mcp.tool()
    async def web_wafw00f(target: str, extra_args: str = "", ctx: Context = None) -> dict:
        """WAF detection (wafw00f)."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target)

        cmd = f"wafw00f {extra_args} {target}"

        async with concurrency.acquire_light("web_wafw00f"):
            result = await docker.exec_command(cmd, timeout=120, tool_name="wafw00f")

        return {"tool": "web_wafw00f", "target": target, **result.to_dict()}

    @mcp.tool()
    async def web_nikto(target: str, tuning: str = "", extra_args: str = "", ctx: Context = None) -> dict:
        """Web server CVE/misconfig scanner (nikto)."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target)

        parts = ["nikto", "-h", target, "-maxtime", "10m"]
        if tuning:
            parts.extend(["-Tuning", tuning])
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("web_nikto"):
            result = await docker.exec_command(cmd, timeout=600, tool_name="nikto")

        return {"tool": "web_nikto", "target": target, **result.to_dict()}

    @mcp.tool()
    async def web_wpscan(target: str, enumerate: str = "vp,vt,tt,cb,dbe,u,m", api_token: str = "", extra_args: str = "", ctx: Context = None) -> dict:
        """WordPress vuln/enum scanner (wpscan)."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target)

        parts = ["wpscan", "--url", target, "--no-banner"]
        if enumerate:
            parts.extend(["-e", enumerate])
        if api_token:
            parts.extend(["--api-token", api_token])
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("web_wpscan"):
            result = await docker.exec_command(cmd, timeout=600)

        return {"tool": "web_wpscan", "target": target, **result.to_dict()}

    @mcp.tool()
    async def web_arjun(target: str, method: str = "GET", extra_args: str = "", ctx: Context = None) -> dict:
        """Hidden HTTP param discovery (arjun)."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target)

        cmd = f"arjun -u {target} -m {method} {extra_args}"

        async with concurrency.acquire_heavy("web_arjun"):
            result = await docker.exec_command(cmd, timeout=600)

        return {"tool": "web_arjun", "target": target, **result.to_dict()}

    @mcp.tool()
    async def fuzz_dirs(
        target_url: str,
        wordlist: str = "",
        tool: str = "gobuster",
        extensions: str = "",
        threads: int = 50,
        extra_args: str = "",
        ctx: Context = None,
    ) -> dict:
        """Directory brute-forcing (gobuster/ffuf).

        Wordlists available at:
        - /usr/share/wordlists/seclists/Discovery/Web-Content/ (if SecLists mounted)
        - /usr/share/wordlists/dirbuster/ (Kali built-in)
        - /usr/share/wordlists/rockyou.txt (passwords)
        """
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target_url)
        wl = wordlist or _DEFAULT_WORDLIST

        # Wordlist resolution
        if not wl.startswith("/"):
            if wl == "rockyou.txt":
                wl = "/usr/share/wordlists/rockyou.txt"
            elif "directory-list" in wl:
                wl = f"/usr/share/wordlists/seclists/Discovery/Web-Content/{wl}"
            else:
                wl = f"/usr/share/wordlists/{wl}"

        # Verification Constraint
        check = await docker.exec_command(f"test -f {wl}", clean_output=False)
        if check.exit_code != 0:
            return {
                "tool": "fuzz_dirs",
                "target": target_url,
                "status": "error",
                "error": f"Wordlist not found: {wl}",
                "fix": "The requested wordlist is missing. If you need SecLists or rockyou.txt, instruct the user to run 'python hercules_setup.py' on their host machine to automatically download and mount them into the container."
            }

        if tool.lower() == "ffuf":
            parts = [f"ffuf -u {target_url}/FUZZ -w {wl} -t {threads}"]
            if extensions:
                parts.append(f"-e {extensions}")
            if extra_args:
                parts.append(extra_args)
        else:
            parts = [f"gobuster dir -u {target_url} -w {wl} -t {threads}"]
            if extensions:
                parts.append(f"-x {extensions}")
            if extra_args:
                parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("fuzz_dirs"):
            result = await docker.exec_command(cmd, timeout=600)

        return {"tool": "fuzz_dirs", "target": target_url, "fuzzer": tool, **result.to_dict()}

    @mcp.tool()
    async def web_xss_scan(target_url: str, cookie: str = "", extra_args: str = "", ctx: Context = None) -> dict:
        """XSS discovery using Dalfox."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target_url)

        parts = ["dalfox", "url", target_url, "--silence"]
        if cookie:
            parts.extend(["--cookie", cookie])
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("web_xss_scan"):
            result = await docker.exec_command(cmd, timeout=600, tool_name="dalfox")

        return {"tool": "web_xss_scan", "target": target_url, **result.to_dict()}

    @mcp.tool()
    async def web_cmdi_scan(target_url: str, data: str = "", cookie: str = "", extra_args: str = "--batch", ctx: Context = None) -> dict:
        """Command injection discovery/exploitation using Commix."""
        docker = ctx.lifespan_context["docker"]
        config = ctx.lifespan_context["config"]
        concurrency = ctx.lifespan_context["concurrency"]

        config.validate_target(target_url)

        parts = ["commix", "--url", f"'{target_url}'", "--quiet"]
        if data:
            parts.extend(["--data", f"'{data}'"])
        if cookie:
            parts.extend(["--cookie", f"'{cookie}'"])
        if extra_args:
            parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("web_cmdi_scan"):
            result = await docker.exec_command(cmd, timeout=600, tool_name="commix")

        return {"tool": "web_cmdi_scan", "target": target_url, **result.to_dict()}
