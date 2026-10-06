/** Synthetic local-lab excerpts. These are never sent to an MCP server. */
export const workflow = [
  {
    title: "Connect without starting Docker.",
    description:
      "Your MCP client discovers the selected tools and seven resources. The container stays stopped until the agent explicitly starts it.",
    name: "tools/list",
    state: "runtime: stopped",
    node: 0,
    call: { method: "tools/list" },
    result: {
      tools: [
        { name: "system_start_container" },
        { name: "web_scan" },
        { name: "workspace_read_file" },
      ],
    },
  },
  {
    title: "Start when the work starts.",
    description:
      "The agent explicitly starts the owned Kali container. Repeating the call reuses the running environment. Connecting alone never starts Docker.",
    name: "system_start_container",
    state: "runtime: running",
    node: 1,
    call: { name: "system_start_container", arguments: {} },
    result: {
      tool: "system_start_container",
      status: "success",
      start_mode: "created",
      session_id: "a1b2c3d4",
    },
  },
  {
    title: "Ask a tool a specific question.",
    description:
      "Here, the agent chooses httpx to inspect an authorized local web fixture. Hercules routes the typed call to the selected backend inside Kali.",
    name: "web_scan",
    state: "tool: httpx",
    node: 2,
    call: {
      name: "web_scan",
      arguments: { tool: "httpx", urls: "http://lab.local:8080" },
    },
    result: { tool: "web_scan", selected_tool: "httpx", result_count: 1 },
  },
  {
    title: "Read the result, not the noise.",
    description:
      "For supported tools, structured records replace duplicated terminal output. Warnings, errors, and completeness information remain visible.",
    name: "web_scan / result",
    state: "result: inspectable",
    node: 2,
    call: {
      name: "web_scan",
      arguments: { tool: "httpx", urls: "http://lab.local:8080" },
    },
    result: {
      results: [
        {
          url: "http://lab.local:8080",
          status_code: 200,
          title: "Local lab",
          webserver: "nginx",
        },
      ],
      result_count: 1,
    },
  },
  {
    title: "Return to the evidence.",
    description:
      "When larger output is saved as a workspace artifact, the agent can read it in bounded chunks. Stopping the container preserves workspace files.",
    name: "workspace_read_file",
    state: "workspace: retained",
    node: 4,
    call: {
      name: "workspace_read_file",
      arguments: { path: "logs/lab-stdout.log", offset: 0, max_bytes: 512 },
    },
    result: {
      tool: "workspace_read_file",
      bytes: 512,
      total_bytes: 2048,
      offset: 0,
      truncated: true,
      next_offset: 512,
    },
  },
];

export const categories = {
  core: {
    title: "The workspace comes first.",
    kicker: "Always included",
    description:
      "Start and stop the runtime, manage jobs, and read or write workspace files. These core tools are part of every installation.",
    backends: "Bash · Session manager · Workspace I/O",
  },
  recon: {
    title: "Find a place to begin.",
    kicker: "Reconnaissance",
    description:
      "Look up DNS records, query WHOIS, or enumerate subdomains and ASNs. Choose the next check from what you discover.",
    backends: "dig · dnsx · WHOIS · Amass",
  },
  network: {
    title: "Look closer at the service.",
    kicker: "Network",
    description:
      "Scan ports and services with Nmap, send HTTP requests, manage sockets, or craft packets. Author and run custom NSE checks in the workspace.",
    backends: "Nmap / NSE · curl · Ncat · hping3",
  },
  web: {
    title: "Follow the web surface.",
    kicker: "Web assessment",
    description:
      "Fingerprint applications, discover content, and run focused vulnerability checks. Write and run scoped Nuclei templates when an existing check does not answer the question.",
    backends: "httpx · WhatWeb · ffuf · Gobuster · Nuclei · SQLMap + more",
  },
  exploitation: {
    title: "Work with the session.",
    kicker: "Exploitation",
    description:
      "Search Exploit-DB and use Metasploit through its RPC interface. Manage modules, listeners, payloads, sessions, and jobs within your authorized scope.",
    backends: "Searchsploit · Metasploit Framework",
  },
  cracking: {
    title: "Test authorized credentials.",
    kicker: "Passwords",
    description:
      "Use Hydra for authorized online credential testing and John the Ripper for offline hash cracking with your selected wordlists.",
    backends: "Hydra · John the Ripper",
  },
  ctf: {
    title: "Inspect what the file contains.",
    kicker: "CTF / forensics",
    description:
      "Analyze and extract embedded file content with Binwalk, or inspect and extract steganographic data with Steghide.",
    backends: "Binwalk · Steghide",
  },
  browser: {
    title: "See the page your agent sees.",
    kicker: "Headless browser",
    description:
      "Open a page, inspect snapshots, act on elements, and capture screenshots. Named sessions use CloakBrowser-backed Chromium. Bot-detection avoidance is not guaranteed.",
    backends: "agent-browser · CloakBrowser / Chromium",
  },
};

export const evidence = {
  compact: {
    heading: "Know what was left out.",
    description:
      "In this example, the inline output was shortened. The full stdout was saved as an artifact, so the agent can read it in chunks.",
    filename: "response.json",
    content: {
      tool: "shell_exec",
      exit_code: 0,
      stdout: "Local lab report…",
      stdout_truncated: true,
      output_complete: false,
      evidence_complete: true,
      stdout_artifact: "/opt/workspace/logs/lab-stdout.log",
    },
  },
  artifact: {
    heading: "Read what remains available.",
    description:
      "A workspace read returns its byte offset, total size, and next offset. Continue reading without placing the whole artifact in the conversation at once.",
    filename: "workspace_read_file / excerpt",
    content: {
      tool: "workspace_read_file",
      path: "/opt/workspace/logs/lab-stdout.log",
      encoding: "text",
      bytes: 512,
      total_bytes: 2048,
      offset: 0,
      truncated: true,
      next_offset: 512,
      content: "Local lab report\nFixture: lab.local:8080\nStatus: 200\n…",
    },
  },
};
