import { useState, useRef } from "react";
import { TerminalWindow } from "@phosphor-icons/react/TerminalWindow";
import { ShieldCheck } from "@phosphor-icons/react/ShieldCheck";
import { FunnelSimple } from "@phosphor-icons/react/FunnelSimple";
import { Browsers } from "@phosphor-icons/react/Browsers";
import { Lightning } from "@phosphor-icons/react/Lightning";
import { HardDrive } from "@phosphor-icons/react/HardDrive";
import { Network } from "@phosphor-icons/react/Network";
import { GlobeHemisphereWest } from "@phosphor-icons/react/GlobeHemisphereWest";
import { FileArchive } from "@phosphor-icons/react/FileArchive";
import { Code } from "@phosphor-icons/react/Code";
import { ArrowRight } from "@phosphor-icons/react/ArrowRight";
import { ArrowDown } from "@phosphor-icons/react/ArrowDown";
import { CheckCircle } from "@phosphor-icons/react/CheckCircle";
import { Eye } from "@phosphor-icons/react/Eye";

const asset = (path: string) => import.meta.env.BASE_URL + "assets/" + path;

type SubsystemKey =
  | "agent"
  | "gateway"
  | "filter"
  | "docker"
  | "cloakbrowser"
  | "concurrent"
  | "workspaces";

interface SubsystemData {
  title: string;
  category: string;
  tag: string;
  mechanism: string;
  metrics: { label: string; value: string }[];
  securityNote: string;
}

const SUBSYSTEM_INFO: Record<SubsystemKey, SubsystemData> = {
  agent: {
    title: "AI Agent (MCP Client)",
    category: "ORCHESTRATION LAYER",
    tag: "UNPRIVILEGED HOST CLIENT",
    mechanism:
      "Communicates over standard STDIO using JSON-RPC 2.0. Enforces target CIDR scope boundaries before any tool dispatch.",
    metrics: [
      { label: "Supported Clients", value: "Claude, Codex, Gemini, OpenCode" },
      { label: "Transport", value: "STDIO / JSON-RPC 2.0" },
      { label: "Scope Enforcement", value: "Strict CIDR whitelist" },
      { label: "Context Window", value: "Protected by Token Filter" },
    ],
    securityNote:
      "The agent runs as a normal host process without root privileges and has no direct socket access to the Docker daemon.",
  },
  gateway: {
    title: "Hercules Host Gateway",
    category: "HOST CONTROL PLANE",
    tag: "ZERO HOST POLLUTION",
    mechanism:
      "A lightweight 18MB background daemon that translates MCP tool calls into Docker exec commands and manages background async job pools.",
    metrics: [
      { label: "Idle RAM Footprint", value: "18 MB" },
      { label: "Host Package Pollution", value: "0 bytes / 0 packages" },
      { label: "Lifecycle", value: "On-demand container boot" },
      { label: "Process ID", value: "PID: 4912 (unprivileged)" },
    ],
    securityNote:
      "All offensive binaries, scripts, wordlists, and packet injectors remain quarantined inside Docker, keeping your host OS pristine.",
  },
  filter: {
    title: "Token Reduction & Noise Strip Engine",
    category: "EFFICIENCY & CONTEXT LAYER",
    tag: "80% - 98.5% SAVINGS",
    mechanism:
      "Streams raw stdout from tools like Nmap, Nikto, ffuf, and SQLMap through in-memory AST and regex filters, stripping noisy banners, progress tickers, and redundant headers while preserving full evidence on disk.",
    metrics: [
      { label: "Average Savings", value: "92.4% token reduction" },
      { label: "Raw Tool Output", value: "50 KB – 5 MB scan captures" },
      { label: "Inline Response", value: "1.2 KB – 6 KB compact context" },
      { label: "Audit Evidence", value: "100% complete logs to host mount" },
    ],
    securityNote:
      "Vulnerability proofs, CVE signatures, HTTP response codes, and capture flags are never truncated or omitted from the inline response.",
  },
  docker: {
    title: "Hardened Kali Docker Sandbox",
    category: "CONTAINMENT RUNTIME",
    tag: "ISOLATED ATTACK ENVIRONMENT",
    mechanism:
      "Boots an isolated, ephemeral kali-rolling:2024.4 container per session. Heavy security tools and raw socket operations run safely inside containerized namespaces.",
    metrics: [
      { label: "Base Image", value: "kali-rolling:2024.4" },
      { label: "Network Namespace", value: "Bridge-isolated veth" },
      { label: "Resource Quota", value: "512MB RAM / 2 Cores cap" },
      { label: "Teardown", value: "Auto-cleanup on session stop" },
    ],
    securityNote:
      "Root operations and network attacks remain trapped in the container namespace. Zero ability to mutate or compromise the host kernel.",
  },
  cloakbrowser: {
    title: "CloakBrowser Stealth Automation",
    category: "EVASION & WEB RUNTIME",
    tag: "HEADLESS BOT EVASION",
    mechanism:
      "A custom patched headless Chromium engine with compile-time fingerprint cloaking. Injects CDP evasion scripts, overrides navigator.webdriver, masks WebGL/Canvas hashes, and humanizes interaction curves.",
    metrics: [
      { label: "Engine", value: "Stealth Chromium 130" },
      { label: "Bot Traces", value: "0 navigator.webdriver signals" },
      { label: "Capture Output", value: "DOM queries + full-page PNGs" },
      { label: "Anti-Bot Evasion", value: "Cloudflare & Akamai verified" },
    ],
    securityNote:
      "Automates authenticated web assessments and complex JavaScript SPAs without tripping anti-bot shields or honeypots.",
  },
  concurrent: {
    title: "Concurrent Multi-Tool Dispatcher",
    category: "EXECUTION SCHEDULER",
    tag: "NON-BLOCKING PARALLEL JOBS",
    mechanism:
      "Allows the AI agent to orchestrate multiple tools simultaneously. Hercules returns immediate Job IDs and coordinates parallel async execution pipelines inside Kali without blocking the main loop.",
    metrics: [
      { label: "Parallelism", value: "Multiple simultaneous tools" },
      { label: "Job Tracking", value: "Async Job IDs + status polling" },
      { label: "Active Pipelines", value: "Nmap + CloakBrowser + Nuclei" },
      { label: "Execution Model", value: "Non-blocking background workers" },
    ],
    securityNote:
      "Each background worker runs in an isolated process group inside Kali with per-job timeout enforcement and bounded memory limits.",
  },
  workspaces: {
    title: "Multi-Session Host Workspaces",
    category: "DATA PERSISTENCE & ISOLATION",
    tag: "HOST-MOUNTED AUDIT TRAILS",
    mechanism:
      "Each investigation session receives an isolated host workspace directory volume-mounted into Kali. Keeps captures, reports, and evidence separated without cross-session contamination.",
    metrics: [
      { label: "Mount Type", value: "Bidirectional Docker volume" },
      { label: "Session A Mount", value: "/opt/workspace/session-a (Port :15553)" },
      { label: "Session B Mount", value: "/opt/workspace/session-b (Port :15554)" },
      { label: "Persistence", value: "Evidence stays on host after exit" },
    ],
    securityNote:
      "Raw terminal outputs and full HTTP transcripts persist directly to the host filesystem even when the Docker container is destroyed.",
  },
};

export function ArchitectureScene({
  reduced,
  paused,
}: {
  reduced: boolean;
  paused: boolean;
}) {
  const root = useRef<HTMLElement>(null);
  const [hovered, setHovered] = useState<SubsystemKey | null>(null);
  const [selected, setSelected] = useState<SubsystemKey | null>(null);

  const activeKey = hovered || selected;
  const activeData = activeKey ? SUBSYSTEM_INFO[activeKey] : null;

  const toggleSelect = (key: SubsystemKey) => {
    setSelected((prev) => (prev === key ? null : key));
  };

  return (
    <section
      id="architecture"
      ref={root}
      className="chapter architecture"
      aria-labelledby="architecture-title"
    >
      <div className="wrap">
        <div className="feature-heading feature-heading--split architecture-heading">
          <div>
            <span className="architecture-eyebrow">
              CONTAINERIZED DISPOSABLE RUNTIME · SYSTEM ARCHITECTURE
            </span>
            <h2 id="architecture-title">
              Kali in a container.
              <br />
              Zero host pollution.
            </h2>
          </div>
          <p>
            Your AI agent speaks standard MCP over STDIO. Hercules acts as a
            lightweight 18MB gateway on your computer. Heavy security tools,
            CloakBrowser automation, and attack runtimes execute inside an
            isolated Docker container that boots on demand, saves tokens through
            intelligent filtering, and cleans up without leaving trace packages
            or raw logs on your host OS.
          </p>
        </div>

        {/* Master Architectural Blueprint Console */}
        <div className="arch-blueprint-chassis" data-ui>
          {/* Console Header Bar */}
          <div className="arch-hud-topline">
            <div className="arch-hud-left">
              <span className="arch-live-blip" aria-hidden="true" />
              <strong className="arch-hud-title">
                HERCULES MCP ARCHITECTURAL SCHEMATIC
              </strong>
              <span className="arch-hud-pill">CONTAINERIZED_ISOLATION_V3</span>
              <span className="arch-hud-pill">KALI-ROLLING:2024.4</span>
            </div>
            <div className="arch-hud-right">
              <Eye size={15} aria-hidden="true" />
              <span>Tap or hover any subsystem to inspect live telemetry</span>
            </div>
          </div>

          {/* Main 3-Column Architectural Grid */}
          <div className="arch-schematic-grid">
            {/* COLUMN 1: HOST OS ENVIRONMENT (AGENT & WORKSPACES) */}
            <div className="arch-column arch-col-host">
              <div className="arch-col-badge">
                <span>HOST OS ENVIRONMENT</span>
                <code>MCP CLIENT &amp; STORAGE</code>
              </div>

              {/* AI Agent Card */}
              <div
                className={`arch-card arch-card-agent${
                  activeKey === "agent" ? " is-highlighted" : ""
                }`}
                onMouseEnter={() => setHovered("agent")}
                onMouseLeave={() => setHovered(null)}
                onClick={() => toggleSelect("agent")}
                tabIndex={0}
                role="region"
                aria-label="AI Agent Environment"
              >
                <div className="card-topline">
                  <div className="card-title-group">
                    <TerminalWindow size={24} weight="duotone" />
                    <div>
                      <h4>Your AI Agent</h4>
                      <small>Terminal-capable orchestrator</small>
                    </div>
                  </div>
                  <span className="status-chip is-online">Connected</span>
                </div>

                <div className="agent-client-chips" aria-label="Supported Agents">
                  <span className="mini-chip">Claude Code</span>
                  <span className="mini-chip">Codex CLI</span>
                  <span className="mini-chip">Gemini</span>
                  <span className="mini-chip">OpenCode</span>
                </div>

                <div className="agent-prompt-display">
                  <span className="prompt-label">ACTIVE PROMPT SCOPE:</span>
                  <p>
                    “Assess web attack surfaces, scan ports, and test auth flows
                    on <code>172.30.102.0/24</code>.”
                  </p>
                </div>

                <div className="card-footline">
                  <span className="footline-scope">
                    <ShieldCheck size={16} /> Strict CIDR Guardrails
                  </span>
                  <code>47 Tools Registered</code>
                </div>
              </div>

              {/* Multi-Session Workspaces (Mounted from Host) */}
              <div
                className={`arch-card arch-card-workspaces${
                  activeKey === "workspaces" ? " is-highlighted" : ""
                }`}
                onMouseEnter={() => setHovered("workspaces")}
                onMouseLeave={() => setHovered(null)}
                onClick={() => toggleSelect("workspaces")}
                tabIndex={0}
                role="region"
                aria-label="Multi-Session Workspaces"
              >
                <div className="card-topline">
                  <div className="card-title-group">
                    <HardDrive size={22} weight="duotone" />
                    <div>
                      <h4>Host Workspaces</h4>
                      <small>Session mount &amp; audit trails</small>
                    </div>
                  </div>
                  <span className="status-chip is-mount">Host Mount</span>
                </div>

                <p className="card-micro-desc">
                  Dual isolated workspace directories persist captures and raw tool logs
                  on host storage with zero cross-session leakage.
                </p>

                <div className="workspace-mounts-grid">
                  <div className="workspace-mount-item">
                    <span className="mount-tag">Session A</span>
                    <code>/opt/workspace/session-a</code>
                    <small>Port :15553</small>
                  </div>
                  <div className="workspace-mount-item">
                    <span className="mount-tag">Session B</span>
                    <code>/opt/workspace/session-b</code>
                    <small>Port :15554</small>
                  </div>
                </div>
              </div>
            </div>

            {/* CONDUIT 1: STDIO MCP BUS */}
            <div
              className={`arch-conduit-col${
                activeKey === "agent" || activeKey === "gateway"
                  ? " is-conduit-active"
                  : ""
              }`}
              aria-hidden="true"
            >
              <span className="conduit-bus-label">STDIO MCP</span>
              <div className="conduit-bus-line">
                <svg
                  viewBox="0 0 100 24"
                  className="conduit-vector"
                  preserveAspectRatio="none"
                >
                  <line
                    x1="0"
                    y1="12"
                    x2="90"
                    y2="12"
                    className="conduit-wire-track"
                  />
                  <line
                    x1="0"
                    y1="12"
                    x2="90"
                    y2="12"
                    className={`conduit-wire-pulse${
                      reduced || paused ? " no-anim" : ""
                    }`}
                  />
                  <polygon
                    points="88,6 100,12 88,18"
                    className="conduit-wire-arrow"
                  />
                </svg>
              </div>
              <small className="conduit-sub">JSON-RPC 2.0</small>
            </div>

            {/* COLUMN 2: HERCULES HOST GATEWAY & TOKEN FILTER */}
            <div className="arch-column arch-col-gateway">
              <div className="arch-col-badge">
                <span>HOST CONTROL PLANE</span>
                <code>PID: 4912</code>
              </div>

              {/* Host Gateway Box */}
              <div
                className={`arch-card arch-card-gateway${
                  activeKey === "gateway" ? " is-highlighted" : ""
                }`}
                onMouseEnter={() => setHovered("gateway")}
                onMouseLeave={() => setHovered(null)}
                onClick={() => toggleSelect("gateway")}
                tabIndex={0}
                role="region"
                aria-label="Hercules Host Gateway"
              >
                <div className="card-topline">
                  <div className="card-title-group">
                    <img
                      src={asset("lion.svg")}
                      width="28"
                      height="28"
                      alt=""
                      className="hercules-lion-icon"
                    />
                    <div>
                      <h4>Hercules Gateway</h4>
                      <small>Lightweight Host Control Plane</small>
                    </div>
                  </div>
                  <span className="status-chip is-light">18MB RAM</span>
                </div>
                <p className="gateway-desc">
                  Acts as an unprivileged host bridge between your agent and the
                  Docker API. Dispatches tools, manages background tasks, and
                  intercepts output.
                </p>
                <div className="gateway-footline">
                  <span>Dispatch: Async Job Pool</span>
                  <code>Bridge Mode: Active</code>
                </div>
              </div>

              {/* Vertical Control & Filter Bridge */}
              <div className="internal-bridge-pipe" aria-hidden="true">
                <div className="bridge-pipe-line" />
                <span className="bridge-pipe-label">
                  <ArrowDown size={12} weight="bold" />
                  STDOUT AST FILTER INTERCEPT
                </span>
                <div className="bridge-pipe-line" />
              </div>

              {/* TOKEN REDUCTION & NOISE STRIP CHAMBER */}
              <div
                className={`arch-card token-filter-chamber${
                  activeKey === "filter" ? " is-highlighted" : ""
                }`}
                onMouseEnter={() => setHovered("filter")}
                onMouseLeave={() => setHovered(null)}
                onClick={() => toggleSelect("filter")}
                tabIndex={0}
                role="region"
                aria-label="Token Reduction & Noise Strip Filter"
              >
                <div className="filter-chamber-header">
                  <span className="filter-chamber-tag">
                    <FunnelSimple size={16} weight="bold" />
                    TOKEN REDUCTION &amp; NOISE STRIP
                  </span>
                  <span className="savings-badge">80% – 98.5% SAVED</span>
                </div>

                <div className="filter-pipeline-visual">
                  <div className="filter-stream-box is-raw">
                    <span className="stream-caption">Raw Tool Output</span>
                    <strong>50KB – 5MB</strong>
                    <small>Banners, progress spam</small>
                  </div>

                  <div className="filter-arrow-group">
                    <ArrowRight size={18} weight="bold" />
                    <span className="filter-core-pill">AST Filter</span>
                  </div>

                  <div className="filter-stream-box is-clean">
                    <span className="stream-caption">Inline to LLM</span>
                    <strong>1.2KB – 6KB</strong>
                    <small className="signal-text">High-signal findings</small>
                  </div>
                </div>

                <div className="filter-audit-route">
                  <CheckCircle size={15} weight="fill" />
                  <span>100% full raw captures preserved in host workspace</span>
                </div>
              </div>
            </div>

            {/* CONDUIT 2: DOCKER API SOCKET */}
            <div
              className={`arch-conduit-col${
                activeKey === "gateway" || activeKey === "docker" || activeKey === "filter"
                  ? " is-conduit-active"
                  : ""
              }`}
              aria-hidden="true"
            >
              <span className="conduit-bus-label">DOCKER API</span>
              <div className="conduit-bus-line">
                <svg
                  viewBox="0 0 100 24"
                  className="conduit-vector"
                  preserveAspectRatio="none"
                >
                  <line
                    x1="0"
                    y1="12"
                    x2="90"
                    y2="12"
                    className="conduit-wire-track"
                  />
                  <line
                    x1="0"
                    y1="12"
                    x2="90"
                    y2="12"
                    className={`conduit-wire-pulse${
                      reduced || paused ? " no-anim" : ""
                    }`}
                  />
                  <polygon
                    points="88,6 100,12 88,18"
                    className="conduit-wire-arrow"
                  />
                </svg>
              </div>
              <small className="conduit-sub">Exec + Socket</small>
            </div>

            {/* COLUMN 3: DOCKER ISOLATION BOUNDARY (KALI LINUX & TOOLS) */}
            <div
              className={`arch-column arch-col-docker docker-sandbox-perimeter${
                activeKey === "docker" ? " is-boundary-active" : ""
              }`}
              onMouseEnter={() => setHovered("docker")}
              onMouseLeave={() => setHovered(null)}
              onClick={() => toggleSelect("docker")}
              tabIndex={0}
              role="region"
              aria-label="Docker Isolation Boundary and Kali Runtime"
            >
              <div className="docker-perimeter-header">
                <div className="docker-header-brand">
                  <img
                    src={asset("brands/docker.svg")}
                    width="24"
                    height="24"
                    alt="Docker"
                  />
                  <span>DOCKER ISOLATION BOUNDARY</span>
                </div>
                <span className="perimeter-badge">kali-rolling:2024.4</span>
              </div>

              <div className="docker-specs-bar">
                <span>Net: bridge-veth</span>
                <span>Quota: 512MB RAM</span>
                <span>Zero Host Pollution</span>
              </div>

              {/* CLOAKBROWSER HERO CARD */}
              <div
                className={`arch-subcard cloakbrowser-card${
                  activeKey === "cloakbrowser" ? " is-highlighted" : ""
                }`}
                onMouseEnter={(e) => {
                  e.stopPropagation();
                  setHovered("cloakbrowser");
                }}
                onMouseLeave={() => setHovered(null)}
                onClick={(e) => {
                  e.stopPropagation();
                  toggleSelect("cloakbrowser");
                }}
                tabIndex={0}
                role="region"
                aria-label="CloakBrowser Stealth Automation"
              >
                <div className="subcard-header">
                  <div className="subcard-title">
                    <Browsers size={20} weight="duotone" />
                    <strong>CloakBrowser Automation</strong>
                  </div>
                  <span className="tool-pill is-stealth">Anti-Bot Evasion</span>
                </div>
                <p className="subcard-summary">
                  Stealth headless Chromium with compile-time fingerprint cloaking,
                  zero <code>navigator.webdriver</code> traces, human input curves,
                  and verified Cloudflare/Akamai bypass.
                </p>
                <div className="cloak-badges-row">
                  <span>CDP Evasion</span>
                  <span>DOM Extraction</span>
                  <span>Visual Screenshots</span>
                  <span>Session Replay</span>
                </div>
              </div>

              {/* OFFENSIVE TOOL ARSENAL MATRIX */}
              <div className="tool-matrix-grid">
                <div className="tool-matrix-cell">
                  <Network size={18} weight="duotone" />
                  <div>
                    <strong>Network Recon</strong>
                    <small>Nmap, RustScan, masscan</small>
                  </div>
                </div>
                <div className="tool-matrix-cell">
                  <GlobeHemisphereWest size={18} weight="duotone" />
                  <div>
                    <strong>Web &amp; API</strong>
                    <small>Nuclei, ffuf, Nikto, SQLMap</small>
                  </div>
                </div>
                <div className="tool-matrix-cell">
                  <Code size={18} weight="duotone" />
                  <div>
                    <strong>Exploits &amp; Shell</strong>
                    <small>Metasploit RPC, async jobs</small>
                  </div>
                </div>
                <div className="tool-matrix-cell">
                  <FileArchive size={18} weight="duotone" />
                  <div>
                    <strong>Forensics &amp; Keys</strong>
                    <small>Binwalk, ExifTool, Hashid</small>
                  </div>
                </div>
              </div>

              {/* CONCURRENT TOOL PIPELINES ENGINE */}
              <div
                className={`arch-subcard concurrency-card${
                  activeKey === "concurrent" ? " is-highlighted" : ""
                }`}
                onMouseEnter={(e) => {
                  e.stopPropagation();
                  setHovered("concurrent");
                }}
                onMouseLeave={() => setHovered(null)}
                onClick={(e) => {
                  e.stopPropagation();
                  toggleSelect("concurrent");
                }}
                tabIndex={0}
                role="region"
                aria-label="Concurrent Multi-Tool Pipelines"
              >
                <div className="subcard-header">
                  <div className="subcard-title">
                    <Lightning size={19} weight="duotone" />
                    <strong>Concurrent Multi-Tool Execution</strong>
                  </div>
                  <span className="tool-pill is-active-pill">3 Active Jobs</span>
                </div>
                <div className="concurrency-pipelines-list">
                  <div className="pipeline-job-item">
                    <div className="job-cmd-row">
                      <span className="job-indicator is-running" />
                      <code>Job #1: nmap -sS -p- 172.30.102.1</code>
                    </div>
                    <span className="job-status-tag">Background</span>
                  </div>
                  <div className="pipeline-job-item">
                    <div className="job-cmd-row">
                      <span className="job-indicator is-running" />
                      <code>Job #2: cloakbrowser goto target.lab/auth</code>
                    </div>
                    <span className="job-status-tag">Stealth Web</span>
                  </div>
                  <div className="pipeline-job-item">
                    <div className="job-cmd-row">
                      <span className="job-indicator is-queued" />
                      <code>Job #3: nuclei -t cves/ -target ...</code>
                    </div>
                    <span className="job-status-tag">Queued AST</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* GROUNDED TELEMETRY INSPECTOR HUD */}
          <div
            className={`arch-inspector-hud${
              activeData ? " is-inspecting" : " is-idle"
            }`}
            aria-live="polite"
          >
            {activeData ? (
              <div className="hud-content-active">
                <div className="hud-topline">
                  <div className="hud-identity">
                    <span className="hud-category-chip">{activeData.category}</span>
                    <h3 className="hud-title">{activeData.title}</h3>
                  </div>
                  <div className="hud-actions-group">
                    <span className="hud-tag-pill">{activeData.tag}</span>
                    {selected && (
                      <button
                        type="button"
                        className="hud-reset-btn"
                        onClick={() => setSelected(null)}
                      >
                        Reset
                      </button>
                    )}
                  </div>
                </div>

                <p className="hud-mechanism-text">{activeData.mechanism}</p>

                <div className="hud-metrics-strip">
                  {activeData.metrics.map((m) => (
                    <div key={m.label} className="hud-metric-cell">
                      <span className="metric-label">{m.label}</span>
                      <strong className="metric-value">{m.value}</strong>
                    </div>
                  ))}
                </div>

                <div className="hud-security-footnote">
                  <ShieldCheck size={16} weight="fill" />
                  <span>{activeData.securityNote}</span>
                </div>
              </div>
            ) : (
              <div className="hud-content-idle">
                <div className="idle-indicator-box">
                  <span className="idle-radar-pulse" aria-hidden="true" />
                  <strong>SYSTEM TELEMETRY INSPECTOR · PLATFORM OVERVIEW</strong>
                  <span className="idle-live-tag">READY</span>
                </div>
                <p>
                  Tap or hover any subsystem above—or click a quick selector pill below—to
                  inspect exact runtime mechanisms, memory quotas, and security boundaries.
                </p>

                <div className="idle-metrics-strip">
                  <div className="idle-metric-item">
                    <span className="idle-metric-label">Containment Runtime</span>
                    <strong className="idle-metric-val">kali-rolling:2024.4</strong>
                  </div>
                  <div className="idle-metric-item">
                    <span className="idle-metric-label">Host Daemon Overhead</span>
                    <strong className="idle-metric-val">18 MB RAM (0 pkgs)</strong>
                  </div>
                  <div className="idle-metric-item">
                    <span className="idle-metric-label">Context Reduction</span>
                    <strong className="idle-metric-val">80% – 98.5% Saved</strong>
                  </div>
                  <div className="idle-metric-item">
                    <span className="idle-metric-label">Offensive Fleet</span>
                    <strong className="idle-metric-val">47 Tools + CloakBrowser</strong>
                  </div>
                </div>

                <div className="idle-quick-pills">
                  <button
                    type="button"
                    className="idle-pill"
                    onClick={() => toggleSelect("agent")}
                    onMouseEnter={() => setHovered("agent")}
                  >
                    Agent Client
                  </button>
                  <button
                    type="button"
                    className="idle-pill"
                    onClick={() => toggleSelect("workspaces")}
                    onMouseEnter={() => setHovered("workspaces")}
                  >
                    Host Workspaces
                  </button>
                  <button
                    type="button"
                    className="idle-pill"
                    onClick={() => toggleSelect("gateway")}
                    onMouseEnter={() => setHovered("gateway")}
                  >
                    Host Gateway
                  </button>
                  <button
                    type="button"
                    className="idle-pill is-featured"
                    onClick={() => toggleSelect("filter")}
                    onMouseEnter={() => setHovered("filter")}
                  >
                    Token Filter Engine
                  </button>
                  <button
                    type="button"
                    className="idle-pill"
                    onClick={() => toggleSelect("docker")}
                    onMouseEnter={() => setHovered("docker")}
                  >
                    Docker Sandbox
                  </button>
                  <button
                    type="button"
                    className="idle-pill is-featured"
                    onClick={() => toggleSelect("cloakbrowser")}
                    onMouseEnter={() => setHovered("cloakbrowser")}
                  >
                    CloakBrowser
                  </button>
                  <button
                    type="button"
                    className="idle-pill"
                    onClick={() => toggleSelect("concurrent")}
                    onMouseEnter={() => setHovered("concurrent")}
                  >
                    Concurrent Jobs
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <p className="sandbox-scope">
          You control networking, permissions, and target scope. Container
          isolation, token reduction, and workspace mounts execute on demand
          with zero permanent host alteration.
        </p>
      </div>
    </section>
  );
}

export default ArchitectureScene;
