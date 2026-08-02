"""
Web scanning and fingerprinting tools for Hercules MCP server.

Consolidates HTTP fingerprinting into web_scan and web vulnerability
scanners into web_vuln_scan while keeping directory fuzzing standalone.
"""

from __future__ import annotations

import json
import logging
import re
import shlex
from typing import TYPE_CHECKING, Literal

from fastmcp import Context

from hercules.core.guidance import (
    TOOL_DESCRIPTIONS,
    missing_param_error,
    selector_error,
    target_error,
    usage_error,
)
from hercules.core.security import (
    redact_secrets,
    redact_url,
    safe_identifier,
    shell_quote,
    validate_target_async,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger("hercules.tools.web_scanner")

# SecLists path if mounted, fallback to Kali built-in dirbuster list
_DEFAULT_WORDLIST = "/usr/share/wordlists/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt"
_SECLISTS_DIRBUSTER_WORDLIST = "/usr/share/wordlists/seclists/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-medium.txt"
_FALLBACK_WORDLIST = "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt"


def _has_flag(extra_args: str, *flags: str) -> bool:
    try:
        tokens = shlex.split(extra_args or "")
    except ValueError:
        tokens = (extra_args or "").split()
    return any(token == flag or token.startswith(f"{flag}=") for token in tokens for flag in flags)


def _jsonl_results(stdout: str) -> list[dict]:
    results = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped or not stripped.startswith("{"):
            continue
        try:
            results.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    return results


def _jsonl_diagnostics(stdout: str) -> str:
    """Return non-JSONL stdout without duplicating parsed records."""
    lines: list[str] = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            if stripped.startswith("{") and isinstance(json.loads(stripped), dict):
                continue
        except json.JSONDecodeError:
            pass
        lines.append(line)
    return "\n".join(lines)


async def _run_httpx(
    ctx: Context,
    urls: str,
    target: str,
    title: bool,
    tech_detect: bool,
    status_code: bool,
    threads: int,
    extra_args: str,
    include_raw: bool,
) -> dict:
    docker = ctx.lifespan_context["docker"]
    config = ctx.lifespan_context["config"]
    concurrency = ctx.lifespan_context["concurrency"]

    source_urls = urls or target
    url_values = [u.strip() for u in source_urls.split(",") if u.strip()]
    try:
        for url in url_values:
            await validate_target_async(config, url)
    except ValueError as exc:
        return target_error("web_scan", url, exc, config)
    if not 0 <= int(threads) <= 10_000:
        return {
            "tool": "web_scan",
            "status": "invalid_parameter",
            "parameter": "threads",
            "error": "threads must be between 0 and 10000",
        }

    parts = ["httpx", "-silent"]
    if title:
        parts.append("-title")
    if tech_detect:
        parts.append("-tech-detect")
    if status_code:
        parts.append("-status-code")
    if threads > 0:
        parts.extend(["-threads", str(threads)])
    if not include_raw and not _has_flag(extra_args, "-json", "-jsonl"):
        parts.append("-json")
    if extra_args:
        parts.append(extra_args)

    quoted_urls = " ".join(shlex.quote(url) for url in url_values)
    cmd = f"printf '%s\\n' {quoted_urls} | " + " ".join(parts)

    async with concurrency.acquire_light("web_httpx"):
        result = await docker.exec_command(
            cmd,
            timeout=300,
            compact_output=not include_raw,
            preserve_raw=not include_raw,
        )

    response = {
        "tool": "web_scan",
        "selected_tool": "httpx",
        "urls": redact_secrets(source_urls),
        **result.to_dict(),
    }
    results = _jsonl_results(result.stdout)
    if results:
        response["results"] = results
        response["result_count"] = len(results)
        if not include_raw:
            diagnostics = _jsonl_diagnostics(result.stdout)
            if diagnostics:
                response["stdout"] = diagnostics
            else:
                response.pop("stdout", None)
            response["inline_stdout_chars"] = len(diagnostics)
            response["structured_output"] = True
            response["stdout_replaced_by"] = "results"
    return response


async def _run_whatweb(ctx: Context, target: str, agg_level: int, extra_args: str) -> dict:
    docker = ctx.lifespan_context["docker"]
    config = ctx.lifespan_context["config"]
    concurrency = ctx.lifespan_context["concurrency"]

    try:
        await validate_target_async(config, target)
    except ValueError as exc:
        return target_error("web_scan", target, exc, config)
    if not 1 <= int(agg_level) <= 4:
        return {
            "tool": "web_scan",
            "status": "invalid_parameter",
            "parameter": "agg_level",
            "error": "agg_level must be between 1 and 4",
        }
    cmd = f"whatweb -a {agg_level} --color=NEVER {extra_args} {shlex.quote(target)}"

    async with concurrency.acquire_light("web_whatweb"):
        result = await docker.exec_command(cmd, timeout=120, tool_name="whatweb")

    return {"tool": "web_scan", "selected_tool": "whatweb", "target": redact_url(target), **result.to_dict()}


async def _run_wafw00f(ctx: Context, target: str, extra_args: str, include_raw: bool) -> dict:
    docker = ctx.lifespan_context["docker"]
    config = ctx.lifespan_context["config"]
    concurrency = ctx.lifespan_context["concurrency"]

    try:
        await validate_target_async(config, target)
    except ValueError as exc:
        return target_error("web_scan", target, exc, config)
    parts = ["wafw00f"]
    if not _has_flag(extra_args, "--no-colors"):
        parts.append("--no-colors")
    if extra_args:
        parts.append(extra_args)
    parts.append(shlex.quote(target))
    cmd = " ".join(parts)

    async with concurrency.acquire_light("web_wafw00f"):
        result = await docker.exec_command(
            cmd,
            timeout=120,
            tool_name="wafw00f",
            compact_output=not include_raw,
            preserve_raw=not include_raw,
        )

    return {"tool": "web_scan", "selected_tool": "wafw00f", "target": redact_url(target), **result.to_dict()}


async def _run_nikto(ctx: Context, target: str, tuning: str, extra_args: str, include_raw: bool) -> dict:
    docker = ctx.lifespan_context["docker"]
    config = ctx.lifespan_context["config"]
    concurrency = ctx.lifespan_context["concurrency"]

    try:
        await validate_target_async(config, target)
    except ValueError as exc:
        return target_error("web_scan", target, exc, config)
    if tuning and not re.fullmatch(r"[0-9A-Za-zx]+", tuning):
        return {
            "tool": "web_scan",
            "status": "invalid_parameter",
            "parameter": "tuning",
            "error": "tuning contains unsupported characters",
        }

    parts = ["nikto", "-h", shlex.quote(target), "-maxtime", "10m"]
    if tuning:
        parts.extend(["-Tuning", shlex.quote(tuning)])
    if extra_args:
        parts.append(extra_args)

    cmd = " ".join(parts)

    async with concurrency.acquire_heavy("web_nikto"):
        result = await docker.exec_command(
            cmd,
            timeout=600,
            tool_name="nikto",
            compact_output=not include_raw,
            preserve_raw=not include_raw,
        )

    return {"tool": "web_scan", "selected_tool": "nikto", "target": redact_url(target), **result.to_dict()}


async def _run_wpscan(
    ctx: Context,
    target: str,
    enumerate: str,
    api_token: str,
    extra_args: str,
    include_raw: bool,
) -> dict:
    docker = ctx.lifespan_context["docker"]
    config = ctx.lifespan_context["config"]
    concurrency = ctx.lifespan_context["concurrency"]

    try:
        await validate_target_async(config, target)
    except ValueError as exc:
        return target_error("web_scan", target, exc, config)
    if enumerate and not re.fullmatch(r"[A-Za-z0-9,._-]+", enumerate):
        return {
            "tool": "web_scan",
            "status": "invalid_parameter",
            "parameter": "enumerate",
            "error": "enumerate contains unsupported characters",
        }

    parts = ["wpscan", "--url", shlex.quote(target), "--no-banner"]
    if enumerate:
        parts.extend(["-e", shlex.quote(enumerate)])
    if api_token:
        parts.extend(["--api-token", shell_quote(api_token, label="WPScan API token")])
    if extra_args:
        parts.append(extra_args)

    cmd = " ".join(parts)

    async with concurrency.acquire_heavy("web_wpscan"):
        result = await docker.exec_command(
            cmd,
            timeout=600,
            tool_name="wpscan",
            compact_output=not include_raw,
            preserve_raw=not include_raw,
            sensitive_values=[api_token],
        )

    return {"tool": "web_scan", "selected_tool": "wpscan", "target": redact_url(target), **result.to_dict()}


async def _run_arjun(ctx: Context, target: str, method: str, threads: int, extra_args: str, include_raw: bool) -> dict:
    docker = ctx.lifespan_context["docker"]
    config = ctx.lifespan_context["config"]
    concurrency = ctx.lifespan_context["concurrency"]

    try:
        await validate_target_async(config, target)
    except ValueError as exc:
        return target_error("web_scan", target, exc, config)
    try:
        method = safe_identifier(method.upper(), label="HTTP method", maximum=16)
    except ValueError as exc:
        return {
            "tool": "web_scan",
            "status": "invalid_parameter",
            "parameter": "method",
            "error": str(exc),
        }
    if not 0 <= int(threads) <= 10_000:
        return {
            "tool": "web_scan",
            "status": "invalid_parameter",
            "parameter": "threads",
            "error": "threads must be between 0 and 10000",
        }
    parts = ["arjun", "-u", shlex.quote(target), "-m", method, "-T", "5", "--disable-redirects"]
    if threads > 0:
        parts.extend(["-t", str(threads)])
    if extra_args:
        parts.append(extra_args)
    cmd = " ".join(parts)

    async with concurrency.acquire_heavy("web_arjun"):
        result = await docker.exec_command(
            cmd,
            timeout=600,
            tool_name="arjun",
            compact_output=not include_raw,
            preserve_raw=not include_raw,
        )

    return {"tool": "web_scan", "selected_tool": "arjun", "target": redact_url(target), **result.to_dict()}


async def _run_dalfox(
    ctx: Context,
    target_url: str,
    cookie: str,
    threads: int,
    extra_args: str,
    include_raw: bool,
) -> dict:
    docker = ctx.lifespan_context["docker"]
    config = ctx.lifespan_context["config"]
    concurrency = ctx.lifespan_context["concurrency"]

    try:
        await validate_target_async(config, target_url)
    except ValueError as exc:
        return target_error("web_vuln_scan", target_url, exc, config)
    if not 0 <= int(threads) <= 10_000:
        return {
            "tool": "web_vuln_scan",
            "status": "invalid_parameter",
            "parameter": "threads",
            "error": "threads must be between 0 and 10000",
        }

    parts = ["dalfox", "url", shlex.quote(target_url), "--silence"]
    if not _has_flag(extra_args, "--no-color"):
        parts.append("--no-color")
    if cookie:
        parts.extend(["--cookie", shlex.quote(cookie)])
    if threads > 0:
        parts.extend(["--worker", str(threads)])
    if extra_args:
        parts.append(extra_args)

    cmd = " ".join(parts)

    async with concurrency.acquire_heavy("web_xss_scan"):
        result = await docker.exec_command(
            cmd,
            timeout=600,
            tool_name="dalfox",
            compact_output=not include_raw,
            preserve_raw=not include_raw,
            sensitive_values=[cookie],
        )

    return {"tool": "web_vuln_scan", "selected_tool": "dalfox", "target": redact_url(target_url), **result.to_dict()}


async def _run_commix(
    ctx: Context,
    target_url: str,
    data: str,
    cookie: str,
    threads: int,
    extra_args: str,
    include_raw: bool,
) -> dict:
    docker = ctx.lifespan_context["docker"]
    config = ctx.lifespan_context["config"]
    concurrency = ctx.lifespan_context["concurrency"]

    try:
        await validate_target_async(config, target_url)
    except ValueError as exc:
        return target_error("web_vuln_scan", target_url, exc, config)
    if not 0 <= int(threads) <= 10_000:
        return {
            "tool": "web_vuln_scan",
            "status": "invalid_parameter",
            "parameter": "threads",
            "error": "threads must be between 0 and 10000",
        }

    parts = ["commix", "--url", shlex.quote(target_url)]
    if not _has_flag(extra_args, "--disable-coloring"):
        parts.append("--disable-coloring")
    if data:
        parts.extend(["--data", shlex.quote(data)])
    if cookie:
        parts.extend(["--cookie", shlex.quote(cookie)])
    if threads > 0:
        thread_support = await docker.exec_command(
            "commix --help 2>&1 | grep -q -- '--threads'",
            timeout=10,
            clean_output=False,
        )
        if thread_support.exit_code == 0:
            parts.append(f"--threads={threads}")
    parts.append(extra_args or "--batch")

    cmd = " ".join(parts)

    async with concurrency.acquire_heavy("web_cmdi_scan"):
        result = await docker.exec_command(
            cmd,
            timeout=600,
            tool_name="commix",
            compact_output=not include_raw,
            preserve_raw=not include_raw,
            sensitive_values=[data, cookie],
        )

    return {"tool": "web_vuln_scan", "selected_tool": "commix", "target": redact_url(target_url), **result.to_dict()}


def register_web_scanner_tools(mcp: FastMCP) -> None:

    @mcp.tool(description=TOOL_DESCRIPTIONS["web_scan"])
    async def web_scan(
        tool: Literal["httpx", "whatweb", "wafw00f", "nikto", "wpscan", "arjun"],
        target: str = "",
        urls: str = "",
        title: bool = True,
        tech_detect: bool = True,
        status_code: bool = True,
        threads: int = 0,
        agg_level: int = 1,
        tuning: str = "",
        enumerate: str = "vp,vt,tt,cb,dbe,u,m",
        api_token: str = "",
        method: str = "GET",
        extra_args: str = "",
        include_raw: bool = False,
        ctx: Context = None,
    ) -> dict:
        """Run one web fingerprinting scanner selected by tool."""
        tool = (tool or "").lower()
        if tool == "httpx":
            if not (urls or target):
                return missing_param_error(
                    "web_scan",
                    "urls",
                    when="tool='httpx' and target is not provided",
                    examples="web_scan(tool='httpx', urls='http://a.test,http://b.test')",
                )
            return await _run_httpx(ctx, urls, target, title, tech_detect, status_code, threads, extra_args, include_raw)
        if tool == "whatweb":
            if not target:
                return missing_param_error("web_scan", "target", when="tool='whatweb'")
            return await _run_whatweb(ctx, target, agg_level, extra_args)
        if tool == "wafw00f":
            if not target:
                return missing_param_error("web_scan", "target", when="tool='wafw00f'")
            return await _run_wafw00f(ctx, target, extra_args, include_raw)
        if tool == "nikto":
            if not target:
                return missing_param_error("web_scan", "target", when="tool='nikto'")
            return await _run_nikto(ctx, target, tuning, extra_args, include_raw)
        if tool == "wpscan":
            if not target:
                return missing_param_error("web_scan", "target", when="tool='wpscan'")
            return await _run_wpscan(ctx, target, enumerate, api_token, extra_args, include_raw)
        if tool == "arjun":
            if not target:
                return missing_param_error("web_scan", "target", when="tool='arjun'")
            return await _run_arjun(ctx, target, method, threads, extra_args, include_raw)
        return selector_error(
            "web_scan",
            "tool",
            tool,
            ["httpx", "whatweb", "wafw00f", "nikto", "wpscan", "arjun"],
            examples=[
                "web_scan(tool='httpx', urls='http://a.test,http://b.test')",
                "web_scan(tool='nikto', target='http://a.test')",
            ],
        )

    @mcp.tool(description=TOOL_DESCRIPTIONS["fuzz_dirs"])
    async def fuzz_dirs(
        target_url: str,
        wordlist: str = "",
        tool: Literal["gobuster", "ffuf"] = "gobuster",
        extensions: str = "",
        threads: int = 50,
        extra_args: str = "",
        include_raw: bool = False,
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

        try:
            await validate_target_async(config, target_url)
        except ValueError as exc:
            return target_error("fuzz_dirs", target_url, exc, config)
        tool = (tool or "").lower()
        if tool not in {"gobuster", "ffuf"}:
            return selector_error(
                "fuzz_dirs",
                "tool",
                tool,
                ["gobuster", "ffuf"],
            )
        if not 1 <= int(threads) <= 10_000:
            return {
                "tool": "fuzz_dirs",
                "status": "invalid_parameter",
                "parameter": "threads",
                "error": "threads must be between 1 and 10000",
            }
        if extensions and not re.fullmatch(r"[A-Za-z0-9,._-]+", extensions):
            return {
                "tool": "fuzz_dirs",
                "status": "invalid_parameter",
                "parameter": "extensions",
                "error": "extensions contains unsupported characters",
            }
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
        check = await docker.exec_command(f"test -f {shlex.quote(wl)}", clean_output=False)
        if check.exit_code != 0 and not wordlist:
            for candidate in (_SECLISTS_DIRBUSTER_WORDLIST, _FALLBACK_WORDLIST):
                candidate_check = await docker.exec_command(
                    f"test -f {shlex.quote(candidate)}", clean_output=False
                )
                if candidate_check.exit_code == 0:
                    wl = candidate
                    check = candidate_check
                    break
        if check.exit_code != 0:
            return usage_error(
                "fuzz_dirs",
                "resource_missing",
                f"Wordlist is unavailable in the container: {wl}",
                received={"wordlist": wordlist or _DEFAULT_WORDLIST, "resolved_wordlist": wl},
                expected=[
                    "/usr/share/wordlists/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt",
                    "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
                    "/usr/share/wordlists/rockyou.txt",
                ],
                examples=[
                    "fuzz_dirs(target_url='http://host', wordlist='/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt')",
                    "fuzz_dirs(target_url='http://host', tool='ffuf', wordlist='directory-list-2.3-medium.txt')",
                ],
                next_steps=[
                    "Choose an existing wordlist path inside the container.",
                    "Run hercules-install install to provision the wordlist required by the selected capability.",
                ],
                target=target_url,
            )

        if tool == "ffuf":
            fuzz_url = target_url.rstrip("/") + "/FUZZ"
            parts = [
                f"ffuf -u {shlex.quote(fuzz_url)} -w {shlex.quote(wl)} -t {threads}"
            ]
            if extensions:
                parts.append(f"-e {shlex.quote(extensions)}")
            if not include_raw:
                for flag in ("-ic", "-s", "-json"):
                    if not _has_flag(extra_args, flag):
                        parts.append(flag)
            if extra_args:
                parts.append(extra_args)
        else:
            parts = [
                (
                    f"gobuster dir -u {shlex.quote(target_url)} "
                    f"-w {shlex.quote(wl)} -t {threads}"
                )
            ]
            if extensions:
                parts.append(f"-x {shlex.quote(extensions)}")
            if not include_raw:
                for flag in ("--no-progress", "--no-color", "--quiet"):
                    if not _has_flag(extra_args, flag):
                        parts.append(flag)
            if extra_args:
                parts.append(extra_args)

        cmd = " ".join(parts)

        async with concurrency.acquire_heavy("fuzz_dirs"):
            result = await docker.exec_command(
                cmd,
                timeout=600,
                compact_output=not include_raw,
                preserve_raw=not include_raw,
            )

        response = {
            "tool": "fuzz_dirs",
            "target": redact_url(target_url),
            "fuzzer": tool,
            **result.to_dict(),
        }
        if tool == "ffuf":
            results = _jsonl_results(result.stdout)
            if results:
                response["results"] = results
                response["result_count"] = len(results)
                if not include_raw:
                    diagnostics = _jsonl_diagnostics(result.stdout)
                    if diagnostics:
                        response["stdout"] = diagnostics
                    else:
                        response.pop("stdout", None)
                    response["inline_stdout_chars"] = len(diagnostics)
                    response["structured_output"] = True
                    response["stdout_replaced_by"] = "results"
        return response

    @mcp.tool(description=TOOL_DESCRIPTIONS["web_vuln_scan"])
    async def web_vuln_scan(
        tool: Literal["dalfox", "commix"],
        target_url: str,
        data: str = "",
        cookie: str = "",
        threads: int = 0,
        extra_args: str = "",
        include_raw: bool = False,
        ctx: Context = None,
    ) -> dict:
        """Run Dalfox XSS scanning or Commix command-injection scanning."""
        tool = (tool or "").lower()
        if not target_url:
            return missing_param_error(
                "web_vuln_scan",
                "target_url",
                when="running dalfox or commix",
                examples="web_vuln_scan(tool='dalfox', target_url='http://host/?q=1')",
            )
        if tool == "dalfox":
            return await _run_dalfox(ctx, target_url, cookie, threads, extra_args, include_raw)
        if tool == "commix":
            return await _run_commix(ctx, target_url, data, cookie, threads, extra_args, include_raw)
        return selector_error(
            "web_vuln_scan",
            "tool",
            tool,
            ["dalfox", "commix"],
            examples=[
                "web_vuln_scan(tool='dalfox', target_url='http://host/?q=1')",
                "web_vuln_scan(tool='commix', target_url='http://host/cmd', data='x=1')",
            ],
        )
