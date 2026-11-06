"""Build self-contained README artwork from the project's static brand assets."""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def image(name: str) -> str:
    path = ASSETS / name
    kind = "image/svg+xml" if path.suffix == ".svg" else (
        "image/jpeg" if path.suffix in {".jpg", ".jpeg"} else "image/png"
    )
    return f"data:{kind};base64,{base64.b64encode(path.read_bytes()).decode()}"


SHADER = image("readme-shader.jpg")
LION = image("hercules-mark-large.png")


def text(x: int, y: int, value: str, style: str, extra: str = "") -> str:
    return f'<text x="{x}" y="{y}" class="{style}" {extra}>{escape(value)}</text>'


def box(x: int, y: int, width: int, height: int, accent: bool = False) -> str:
    stroke = "#ff6a2b" if accent else "#46505a"
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'fill="#11151b" fill-opacity=".94" stroke="{stroke}" stroke-width="2"/>'
        f'<path d="M{x} {y}h90" stroke="#ff6a2b" stroke-width="5"/>'
    )


def frame(name: str, title: str, description: str, width: int, height: int, body: str) -> None:
    markup = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
<title id="title">{escape(title)}</title><desc id="description">{escape(description)}</desc>
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="10" markerHeight="10" orient="auto"><path d="M1 1L9 5 1 9" fill="none" stroke="#ff9b65" stroke-width="1.8"/></marker>
  <style>
    .eyebrow{{font:700 24px Arial,Helvetica,sans-serif;letter-spacing:3px;fill:#ffaf83}}
    .title{{font:700 52px Arial,Helvetica,sans-serif;fill:#f5f3ef}}
    .name{{font:700 32px Arial,Helvetica,sans-serif;fill:#f5f3ef}}
    .body{{font:400 24px Arial,Helvetica,sans-serif;fill:#d2d6da}}
    .small{{font:400 20px Arial,Helvetica,sans-serif;fill:#adb5bd}}
    .mono{{font:700 19px Consolas,monospace;letter-spacing:1px;fill:#ffaf83}}
    .number{{font:700 80px Arial,Helvetica,sans-serif;fill:#f5f3ef}}
  </style>
</defs>
<rect width="{width}" height="{height}" fill="#080b0f"/>
<image href="{SHADER}" x="0" y="0" width="{width}" height="{height}" preserveAspectRatio="xMidYMid slice" opacity=".42"/>
<rect width="{width}" height="{height}" fill="#090c11" fill-opacity=".66"/>
{body}
</svg>'''
    (ASSETS / name).write_text(markup + "\n", encoding="utf-8")


def hero() -> None:
    body = f'''
<path d="M58 62H1342M58 698H1342" stroke="#ff6a2b" stroke-width="3"/>
<path d="M72 106V654" stroke="#ff6a2b" stroke-width="6"/>
<image href="{LION}" x="112" y="149" width="430" height="430"/>
<path d="M583 154V602" stroke="#ff6a2b" stroke-opacity=".55" stroke-width="2"/>
{text(635, 218, 'KALI WORKSPACE • MCP SERVER', 'eyebrow', 'style="font-size:27px"')}
{text(622, 357, 'HERCULES', 'title', 'style="font-size:120px;letter-spacing:-5px"')}
{text(633, 476, 'MCP', 'title', 'style="font-size:110px;letter-spacing:-3px;fill:#ff8b56"')}
{text(637, 561, 'Security tools for your AI agent.', 'name', 'style="font-size:39px"')}
<path d="M634 592H1260" stroke="#ff6a2b" stroke-width="3"/>
'''
    frame("readme-hero.svg", "Hercules MCP", "A Kali workspace for your AI agent.", 1400, 760, body)


def architecture() -> None:
    brands = [
        ("Claude Code", "claude.svg"),
        ("Codex", "codex.png"),
        ("Cursor", "cursor.svg"),
        ("Hermes", "hermes.png"),
    ]
    client_rows = "".join(
        f'<rect x="86" y="{271 + i * 75}" width="290" height="62" fill="#20252c" stroke="#38414a"/>'
        f'<image href="{image("readme-brands/" + logo)}" x="100" y="{281 + i * 75}" width="42" height="42"/>'
        f'{text(158, 311 + i * 75, label, "body")}'
        for i, (label, logo) in enumerate(brands)
    )
    tools = [("Nmap", 1206, 282), ("Nuclei", 1371, 282), ("SQLMap", 1206, 365),
             ("Metasploit*", 1371, 365), ("Obscura", 1206, 448), ("Binwalk", 1371, 448)]
    tool_rows = "".join(
        f'<rect x="{x}" y="{y}" width="150" height="67" fill="#20252c" stroke="#38414a"/>'
        f'{text(x + 15, y + 43, label, "small")}'
        for label, x, y in tools
    )
    body = f'''
<path d="M44 53H1556" stroke="#ff6a2b" stroke-width="3"/>
{text(60, 108, 'EACH SESSION • ONE OWNED RUNTIME • RETAINED EVIDENCE', 'eyebrow')}
{box(60, 174, 340, 472)}
{text(86, 224, 'YOUR AGENT', 'eyebrow')}{text(86, 256, 'Any local STDIO MCP client', 'small')}
{client_rows}
{text(86, 609, 'Other STDIO clients supported', 'small')}
<path d="M408 410H547" stroke="#ff9b65" stroke-width="4" marker-end="url(#arrow)"/>
{text(421, 379, 'MCP / STDIO', 'mono')}
{box(567, 174, 450, 472, True)}
{text(594, 224, 'HOST SERVER', 'eyebrow')}
<image href="{LION}" x="704" y="258" width="174" height="174"/>
{text(642, 484, 'Hercules MCP', 'title')}
{text(601, 541, 'Routes tools and owns this session', 'body')}
<path d="M594 565H990" stroke="#46505a"/>
{text(601, 602, 'Returns bounded results and evidence paths', 'small')}
<path d="M1025 410H1154" stroke="#ff9b65" stroke-width="4" marker-end="url(#arrow)"/>
{text(1050, 379, 'START', 'mono')}
{box(1174, 174, 366, 472, True)}
<image href="{image('readme-brands/docker.svg')}" x="1202" y="202" width="46" height="46"/>
{text(1262, 232, 'KALI RUNTIME', 'eyebrow')}
{text(1205, 266, 'Full image • selected tools exposed', 'small')}
{tool_rows}
{text(1207, 565, '* Optional MCP capability', 'small')}
{text(1207, 605, 'Plus shell and custom tools', 'small')}
<path d="M796 647V708M1357 647V708" stroke="#ff9b65" stroke-width="3"/>
{box(567, 708, 973, 155)}
{text(601, 762, 'HOST WORKSPACE / EVIDENCE', 'eyebrow')}
{text(601, 807, 'Current session mounted in Kali; stopped sessions remain inspectable.', 'body')}
{text(601, 840, 'New sessions get a separate workspace. Files do not move automatically.', 'small')}
'''
    frame("architecture-v4.svg", "Hercules MCP architecture", "Claude Code, Codex, Cursor, Hermes, and other STDIO MCP agents call the Hercules host server. It explicitly starts a session-owned full Kali runtime. The current host workspace is mounted in that runtime, and previous session evidence remains inspectable.", 1600, 920, body)


def setup() -> None:
    steps = [
        (60, "01 / STATUS", "Discover", "Read revision, client and config", "No Docker or mutation"),
        (455, "02 / HOST", "Install / repair", "Register selected client", "Cold STDIO check"),
        (850, "03 / IMAGE", "Choose runtime", "Prebuilt recommended", "Local build is available"),
        (1245, "04 / VERIFY", "Check separately", "Container test by choice", "Cleanup and report"),
    ]
    parts = []
    for x, tag, name, first, second in steps:
        parts += [box(x, 133, 325, 270, tag == "03 / IMAGE"), text(x + 25, 188, tag, "eyebrow"),
                  text(x + 25, 246, name, "name"), text(x + 25, 302, first, "small"),
                  text(x + 25, 343, second, "small")]
    body = f'''
<path d="M46 51H1554" stroke="#ff6a2b" stroke-width="3"/>
{text(60, 99, 'SETUP / FOUR SEPARATE PHASES', 'eyebrow')}
{''.join(parts)}
<path d="M389 267H441M784 267H836M1179 267H1231" stroke="#ff9b65" stroke-width="3" marker-end="url(#arrow)"/>
{text(60, 451, 'A cold MCP connection confirms host setup. It does not prove that Kali has run.', 'body')}
'''
    frame("setup-flow-v2.svg", "Hercules setup phases", "Read-only discovery, host installation, image choice between prebuilt and local build, and separate verification.", 1630, 500, body)


def lifecycle() -> None:
    stages = [
        (60, "MCP CONNECTS", "Stopped", "Workspace A allocated", "No container created"),
        (562, "EXPLICIT START", "Running", "Owned Kali + workspace A", "Repeated starts reuse it"),
        (1064, "STOP CONTAINER", "Stopped", "Workspace A retained", "Start again in same workspace"),
    ]
    parts = []
    for x, tag, name, first, second in stages:
        parts += [box(x, 146, 430, 240, tag == "EXPLICIT START"), text(x + 25, 200, tag, "eyebrow"),
                  text(x + 25, 270, name, "title"), text(x + 25, 322, first, "body"),
                  text(x + 25, 359, second, "small")]
    body = f'''
<path d="M46 51H1548" stroke="#ff6a2b" stroke-width="3"/>
{text(60, 104, 'CONTAINER / WORKSPACE LIFECYCLE', 'eyebrow')}
{''.join(parts)}
<path d="M502 264H548M1004 264H1050" stroke="#ff9b65" stroke-width="3" marker-end="url(#arrow)"/>
<rect x="60" y="425" width="1434" height="70" fill="#171b20" stroke="#46505a"/>
{text(88, 471, 'NEW SESSION → FRESH STOPPED WORKSPACE B', 'name', 'style="font-size:26px"')}
{text(944, 471, 'A stays available to inspect', 'small')}
'''
    frame("workspace-lifecycle-v2.svg", "Hercules container and workspace lifecycle", "Connecting allocates a stopped workspace without a container. Explicit start runs owned Kali with workspace A. Stop retains A. A new session creates separate stopped workspace B while A remains inspectable.", 1554, 520, body)


if __name__ == "__main__":
    hero()
    architecture()
    setup()
    lifecycle()
