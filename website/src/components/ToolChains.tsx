import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ArrowRight } from "@phosphor-icons/react/ArrowRight";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { ArrowsSplit } from "@phosphor-icons/react/ArrowsSplit";
import { Browser } from "@phosphor-icons/react/Browser";
import { Check } from "@phosphor-icons/react/Check";
import { Circle } from "@phosphor-icons/react/Circle";
import { Cpu } from "@phosphor-icons/react/Cpu";
import { Fingerprint } from "@phosphor-icons/react/Fingerprint";
import { FolderOpen } from "@phosphor-icons/react/FolderOpen";
import { HardDrives } from "@phosphor-icons/react/HardDrives";
import { LockKey } from "@phosphor-icons/react/LockKey";
import { Network } from "@phosphor-icons/react/Network";
import { Pulse } from "@phosphor-icons/react/Pulse";
import { ShieldCheck } from "@phosphor-icons/react/ShieldCheck";
import { ShieldSlash } from "@phosphor-icons/react/ShieldSlash";
import { TerminalWindow } from "@phosphor-icons/react/TerminalWindow";
import { TreeStructure } from "@phosphor-icons/react/TreeStructure";

const evidence = (path: string) =>
  import.meta.env.BASE_URL + "assets/recordings/evidence/" + path;
const demoAsset = (path: string) =>
  import.meta.env.BASE_URL + "assets/demos/" + path;

export type CatalogItem = {
  key: string;
  category: string;
  description: string;
  mandatory: boolean;
  mcp_tools: string[];
  backend_binaries: string[];
  wordlists: string[];
  metasploit: boolean;
  browser: boolean;
  note: string;
};

export type CatalogData = {
  full_tool_count: number;
  without_metasploit_tool_count: number;
  resource_count: number;
  categories: { key: string; title: string }[];
  capabilities: CatalogItem[];
};

function useSectionMotion(
  root: React.RefObject<HTMLElement | null>,
  reduced: boolean,
) {
  const [visible, setVisible] = useState(reduced);
  const [entered, setEntered] = useState(reduced);
  useEffect(() => {
    if (reduced || !root.current) {
      setVisible(true);
      setEntered(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        const showing = entries.some((entry) => entry.isIntersecting);
        setVisible(showing);
        if (showing) setEntered(true);
      },
      { threshold: 0.06 },
    );
    observer.observe(root.current);
    return () => observer.disconnect();
  }, [reduced, root]);
  useEffect(() => {
    if (!entered || reduced || !root.current) return;
    const context = gsap.context(() => {
      const timeline = gsap.timeline({ defaults: { ease: "power3.out" } });
      timeline
        .fromTo(
          ".capability-heading > *",
          { y: 24, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.65, stagger: 0.08 },
        )
        .fromTo(
          ".demo-main",
          { y: 28, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.7 },
          "-=0.4",
        )
        .fromTo(
          ".demo-secondary",
          { y: 24, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.6, stagger: 0.1 },
          "-=0.4",
        );
    }, root);
    return () => context.revert();
  }, [entered, reduced, root]);
  return visible;
}

function ReconVisual() {
  return (
    <div
      className="recon-board"
      data-ui
      role="img"
      aria-label="A scoped local lab is discovered first, then its sign-in app, proxy, and HTTPS service are individually verified"
    >
      <div className="recon-board-top">
        <span>
          <Pulse size={15} aria-hidden="true" />
          Target Reconnaissance &amp; Service Matrix
        </span>
        <small>SCOPE: 172.30.102.0/24 · ALLOWLISTED</small>
      </div>
      <div className="recon-board-body">
        <div className="recon-scope-node">
          <svg
            className="recon-radar-svg"
            viewBox="0 0 72 72"
            aria-hidden="true"
          >
            <circle
              cx="36"
              cy="36"
              r="34"
              fill="none"
              stroke="rgba(243,239,233,0.12)"
              strokeWidth="1"
              strokeDasharray="2 3"
            />
            <circle
              cx="36"
              cy="36"
              r="24"
              fill="none"
              stroke="rgba(255,106,43,0.22)"
              strokeWidth="1"
            />
            <circle
              cx="36"
              cy="36"
              r="14"
              fill="none"
              stroke="rgba(255,106,43,0.4)"
              strokeWidth="1"
            />
            <circle
              cx="36"
              cy="36"
              r="5"
              fill="#141110"
              stroke="#ff6a2b"
              strokeWidth="1.6"
            />
            <line
              x1="36"
              y1="2"
              x2="36"
              y2="70"
              stroke="rgba(243,239,233,0.12)"
              strokeWidth="1"
            />
            <line
              x1="2"
              y1="36"
              x2="70"
              y2="36"
              stroke="rgba(243,239,233,0.12)"
              strokeWidth="1"
            />
            <g className="radar-sweep-group">
              <path
                d="M36 36 L36 3 A33 33 0 0 1 63 17 Z"
                fill="url(#radarGradient)"
              />
              <line
                x1="36"
                y1="36"
                x2="36"
                y2="3"
                stroke="#ffb48a"
                strokeWidth="1.8"
              />
            </g>
            <defs>
              <linearGradient
                id="radarGradient"
                x1="0%"
                y1="0%"
                x2="100%"
                y2="100%"
              >
                <stop offset="0%" stopColor="rgba(255,106,43,0.45)" />
                <stop offset="100%" stopColor="rgba(255,106,43,0)" />
              </linearGradient>
            </defs>
            <circle
              className="radar-blip radar-blip--1"
              cx="52"
              cy="20"
              r="3.2"
              fill="#7ce38b"
            />
            <circle
              className="radar-blip radar-blip--2"
              cx="54"
              cy="48"
              r="3"
              fill="#ffb48a"
            />
            <circle
              className="radar-blip radar-blip--3"
              cx="24"
              cy="22"
              r="2.8"
              fill="#7ce38b"
            />
            <circle cx="36" cy="36" r="3.2" fill="#ff6a2b" />
          </svg>
          <strong>Scoped Target Lab</strong>
          <small>3 verified services · 12ms avg</small>
        </div>
        <div className="recon-routes-col" aria-hidden="true">
          <svg
            className="recon-routes-svg"
            viewBox="0 0 92 144"
            preserveAspectRatio="none"
          >
            <path
              d="M 0 72 C 38 72, 42 24, 92 24"
              fill="none"
              stroke="rgba(243,239,233,0.18)"
              strokeWidth="1.5"
            />
            <path
              d="M 0 72 L 92 72"
              fill="none"
              stroke="rgba(243,239,233,0.18)"
              strokeWidth="1.5"
            />
            <path
              d="M 0 72 C 38 72, 42 120, 92 120"
              fill="none"
              stroke="rgba(243,239,233,0.18)"
              strokeWidth="1.5"
            />
            <path
              className="recon-route-pulse recon-route-pulse--1"
              d="M 0 72 C 38 72, 42 24, 92 24"
              fill="none"
              stroke="#ff6a2b"
              strokeWidth="2.2"
            />
            <path
              className="recon-route-pulse recon-route-pulse--2"
              d="M 0 72 L 92 72"
              fill="none"
              stroke="#7ce38b"
              strokeWidth="2.2"
            />
            <path
              className="recon-route-pulse recon-route-pulse--3"
              d="M 0 72 C 38 72, 42 120, 92 120"
              fill="none"
              stroke="#ff6a2b"
              strokeWidth="2.2"
            />
            <circle cx="4" cy="72" r="3.5" fill="#ff6a2b" />
            <circle cx="88" cy="24" r="3" fill="#7ce38b" />
            <circle cx="88" cy="72" r="3" fill="#7ce38b" />
            <circle cx="88" cy="120" r="3" fill="#7ce38b" />
          </svg>
        </div>
        <div className="recon-service-stack">
          <div className="recon-service recon-service--app">
            <span className="recon-service-main">
              <Browser size={16} aria-hidden="true" />
              <code>8000</code>
              <span>HTTP/2 SPA · Auth Gateway</span>
            </span>
            <em className="recon-badge recon-badge--live">200 OK</em>
          </div>
          <div className="recon-service recon-service--proxy">
            <span className="recon-service-main">
              <Network size={16} aria-hidden="true" />
              <code>8080</code>
              <span>HTTP Proxy · Fwd Routing</span>
            </span>
            <em className="recon-badge recon-badge--live">Verified</em>
          </div>
          <div className="recon-service recon-service--tls">
            <span className="recon-service-main">
              <ShieldCheck size={16} aria-hidden="true" />
              <code>8443</code>
              <span>HTTPS TLS · Valid Cert Chain</span>
            </span>
            <em className="recon-badge recon-badge--live">CA valid</em>
          </div>
        </div>
      </div>
      <div className="recon-board-foot">
        <Check size={15} aria-hidden="true" /> Discovery maps raw surfaces. Service verification proves live vulnerabilities.
      </div>
    </div>
  );
}

function JobsVisual() {
  return (
    <div
      className="demo-job-board"
      data-ui
      role="img"
      aria-label="A long-running background check keeps its output while the agent moves to a second lead, then returns to resume it"
    >
      <div className="job-board-heading">
        <span>
          <Pulse size={15} aria-hidden="true" />
          Parallel Job Orchestration Deck
        </span>
        <span className="job-live">
          <i />
          job_8f2a running · PID 2491
        </span>
      </div>
      <div className="job-lanes">
        <div className="job-lane job-lane--running">
          <div className="job-lane-top">
            <span className="job-icon">
              <TerminalWindow size={17} />
            </span>
            <div className="job-lane-title">
              <strong>Background Deep Vulnerability Scan</strong>
              <small>Streaming output buffered without blocking client</small>
            </div>
            <span className="job-status-pill is-running">Streaming</span>
          </div>
          <div className="job-terminal-peek">
            <code>[+] 172.30.102.10:8000 (Express/Node) · probing CVE-2024-auth...</code>
            <small>38.4 KB buffered · 412 lines</small>
          </div>
          <div className="job-bar-track" aria-hidden="true">
            <i className="job-bar-fill job-bar-fill--stream" />
          </div>
        </div>
        <div className="job-fork-row" aria-hidden="true">
          <div className="job-fork-icon">
            <ArrowsSplit size={17} />
          </div>
          <svg
            className="job-fork-svg"
            viewBox="0 0 200 24"
            preserveAspectRatio="none"
          >
            <path
              d="M 10 12 L 80 12 L 120 4 L 190 4"
              fill="none"
              stroke="#ff6a2b"
              strokeWidth="1.5"
              strokeDasharray="3 3"
            />
            <circle cx="10" cy="12" r="3" fill="#ff6a2b" />
            <circle cx="190" cy="4" r="3" fill="#7ce38b" />
          </svg>
          <span>
            Agent unblocks immediately to verify fast lead while scanner runs
          </span>
        </div>
        <div className="job-lane job-lane--verify">
          <div className="job-lane-top">
            <span className="job-icon">
              <Browser size={17} />
            </span>
            <div className="job-lane-title">
              <strong>Targeted HTTP &amp; Headless Browser Probe</strong>
              <small>Extracts forms, DOM state, &amp; session cookies</small>
            </div>
            <span className="job-status-pill is-verified">Verified · 14ms</span>
          </div>
          <div className="job-bar-track" aria-hidden="true">
            <i className="job-bar-fill job-bar-fill--done" />
          </div>
        </div>
      </div>
      <div className="job-board-foot">
        <Check size={15} aria-hidden="true" /> Reconnect to any background job at any time with earlier output buffers intact.
      </div>
    </div>
  );
}

function WorkspacesVisual() {
  return (
    <div
      className="demo-workspace-compare"
      data-ui
      role="img"
      aria-label="Two connected clients each own a Hercules runtime and workspace, separated by a boundary"
    >
      <div className="session-pod session-pod--a">
        <div className="session-pod-head">
          <TerminalWindow size={18} />
          <div>
            <strong>Client A · Claude Code</strong>
            <small>STDIO pipe · PID 3140</small>
          </div>
          <span className="session-state-tag session-state-tag--a">
            <Circle className="runtime-led" weight="fill" size={8} />
            Active
          </span>
        </div>
        <div className="session-specs-bar">
          <span>Port set :15553</span>
          <span>PID: isolated</span>
        </div>
        <div className="session-pipeline">
          <div className="session-node">
            <HardDrives size={17} />
            <div>
              <b>Kali container A</b>
              <small>On-demand runtime</small>
            </div>
          </div>
          <div className="session-wire" aria-hidden="true">
            <i />
            <ArrowRight size={14} />
          </div>
          <div className="session-node">
            <FolderOpen size={17} />
            <div>
              <b>Workspace A</b>
              <small>/opt/workspace/session-a</small>
            </div>
          </div>
        </div>
      </div>
      <div className="workspace-separator" aria-hidden="true">
        <i />
        <span className="separator-badge">
          <LockKey size={16} />
          <b>KERNEL ISOLATION</b>
          <small>Dedicated PIDs, ports &amp; mounts</small>
        </span>
        <i />
      </div>
      <div className="session-pod session-pod--b">
        <div className="session-pod-head">
          <TerminalWindow size={18} />
          <div>
            <strong>Client B · Codex</strong>
            <small>STDIO pipe · PID 3141</small>
          </div>
          <span className="session-state-tag session-state-tag--b">
            <Circle className="runtime-led" weight="fill" size={8} />
            Active
          </span>
        </div>
        <div className="session-specs-bar">
          <span>Port set :15554</span>
          <span>PID: isolated</span>
        </div>
        <div className="session-pipeline">
          <div className="session-node">
            <HardDrives size={17} />
            <div>
              <b>Kali container B</b>
              <small>Independent lifecycle</small>
            </div>
          </div>
          <div className="session-wire" aria-hidden="true">
            <i />
            <ArrowRight size={14} />
          </div>
          <div className="session-node">
            <FolderOpen size={17} />
            <div>
              <b>Workspace B</b>
              <small>/opt/workspace/session-b</small>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ToolChains({
  reduced,
  paused,
}: {
  reduced: boolean;
  paused: boolean;
}) {
  const root = useRef<HTMLElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const visible = useSectionMotion(root, reduced);
  const [videoFailed, setVideoFailed] = useState(false);

  useEffect(() => {
    const element = video.current;
    if (!element || reduced || paused || videoFailed) return;
    let inView = false;
    const sync = () => {
      if (inView && !document.hidden) void element.play().catch(() => {});
      else element.pause();
    };
    const observer = new IntersectionObserver(
      (entries) => {
        inView = entries[0]?.isIntersecting ?? false;
        sync();
      },
      { threshold: 0.05 },
    );
    observer.observe(element);
    document.addEventListener("visibilitychange", sync);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", sync);
      element.pause();
    };
  }, [reduced, paused, videoFailed]);

  return (
    <section
      id="tools"
      ref={root}
      className={`chapter wrap capabilities-section${visible ? " is-visible" : ""}`}
      aria-labelledby="capability-title"
    >
      <div className="feature-heading feature-heading--split capability-heading">
        <div>
          <span className="capability-eyebrow">
            STEALTH CHROMIUM · COMPILE-TIME EVASION
          </span>
          <h2 id="capability-title">Stealth browser automation. Zero bot traces.</h2>
        </div>
        <p>
          Drive a compile-time patched stealth Chromium backend through FastMCP.
          Evade bot detection heuristics, navigate authenticated SPAs with
          token-lean @e accessibility trees, and preserve forensic screenshot
          proof directly on your host machine.
        </p>
      </div>
      <div className="capability-gallery">
        <article
          className="demo-card demo-main demo-browser"
          aria-labelledby="juice-title"
        >
          <div className="demo-browser-media">
            <div className="demo-card-topline">
              <span className="demo-status">
                <i />
                CloakBrowser Stealth Engine Active
              </span>
              <span className="demo-topline-tag">
                <ShieldSlash size={14} aria-hidden="true" />
                Anti-Bot Fingerprint Masking
              </span>
            </div>
            <div className="juice-browser-frame" data-ui>
              <div className="juice-browser-bar">
                <div className="browser-dots" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </div>
                <span className="browser-url">
                  http://172.30.78.10:3000/#/login
                </span>
                <span className="browser-tactical-chip">
                  <Cpu size={13} aria-hidden="true" />
                  navigator.webdriver = false
                </span>
              </div>
              <div className="juice-video-stage">
                {!reduced && !paused && !videoFailed ? (
                  <video
                    ref={video}
                    key="juice-session"
                    aria-label="Looping recording of Hercules driving a stealth headless browser session to solve authentication via SQL injection"
                    src={demoAsset("juice-shop-session.mp4")}
                    muted
                    loop
                    playsInline
                    preload="metadata"
                    poster={demoAsset("juice-shop-poster.png")}
                    onError={() => setVideoFailed(true)}
                  />
                ) : (
                  <img
                    src={demoAsset("juice-shop-poster.png")}
                    alt="CloakBrowser session confirming headless authentication and scoreboard verification"
                    width="1280"
                    height="600"
                  />
                )}
                <div className="juice-video-hud">
                  <span className="hud-badge hud-badge--live">
                    <Circle className="runtime-led" weight="fill" size={7} />
                    LIVE RUNTIME
                  </span>
                  <span className="hud-metric">
                    Target: <code>172.30.78.10:3000</code>
                  </span>
                  <span className="hud-metric">
                    Action: <code>SQLi Auth Flow via @e refs</code>
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="demo-browser-aside">
            <div className="demo-browser-copy">
              <h3 id="juice-title">Headless automation that doesn't trigger bot shields.</h3>
              <p>
                Standard headless drivers leak automation flags, CDP listeners,
                and telltale WebGL hashes. CloakBrowser pairs compile-time C++
                anti-fingerprinting patches with a persistent Rust daemon that
                maps pages into ultra-compact accessibility trees (~320 tokens vs
                48,000 HTML tokens), executes deterministic actions, and writes
                host forensic proof.
              </p>
            </div>

            <div className="stealth-matrix" role="region" aria-label="CloakBrowser Anti-Detection Matrix">
              <div className="stealth-spec-item">
                <ShieldSlash size={18} className="stealth-spec-icon" />
                <div>
                  <strong>Compile-time C++ patches</strong>
                  <small>navigator.webdriver=false &amp; no CDP leak headers</small>
                </div>
              </div>
              <div className="stealth-spec-item">
                <Fingerprint size={18} className="stealth-spec-icon" />
                <div>
                  <strong>Hardware noise spoofing</strong>
                  <small>Canvas, WebGL, audio &amp; font fingerprint shields</small>
                </div>
              </div>
              <div className="stealth-spec-item">
                <TreeStructure size={18} className="stealth-spec-icon" />
                <div>
                  <strong>Token-lean @e snapshots</strong>
                  <small>Accessibility tree refs save 99% LLM context tokens</small>
                </div>
              </div>
              <div className="stealth-spec-item">
                <HardDrives size={18} className="stealth-spec-icon" />
                <div>
                  <strong>Persistent daemon &amp; vault</strong>
                  <small>Session state survives MCP calls; PNG proof kept on host</small>
                </div>
              </div>
            </div>

            <div className="browser-pipeline-summary">
              <div className="pipeline-step-chip">
                <span>1</span>
                <code>browser_open</code>
              </div>
              <ArrowRight size={14} aria-hidden="true" />
              <div className="pipeline-step-chip">
                <span>2</span>
                <code>snapshot (@e)</code>
              </div>
              <ArrowRight size={14} aria-hidden="true" />
              <div className="pipeline-step-chip">
                <span>3</span>
                <code>act (fill/click)</code>
              </div>
              <ArrowRight size={14} aria-hidden="true" />
              <div className="pipeline-step-chip">
                <span>4</span>
                <code>screenshot</code>
              </div>
            </div>

            <div className="stealth-telemetry-banner">
              <div className="stealth-telemetry-count">
                28<span>calls</span>
              </div>
              <div>
                <strong>
                  <Check size={16} aria-hidden="true" />
                  0 bot flags triggered · 100% evidence retained
                </strong>
                <p>
                  Full headless SQL injection authentication completed with zero
                  automation markers. Host workspace retains Markdown &amp; PNG reports.
                </p>
                <div className="stealth-telemetry-links">
                  <a
                    href={demoAsset("juice-shop-walkthrough.md")}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Read walkthrough <ArrowUpRight size={14} aria-hidden="true" />
                  </a>
                  <a
                    href={demoAsset("juice-shop-session.mp4")}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Full recording <ArrowUpRight size={14} aria-hidden="true" />
                  </a>
                </div>
              </div>
            </div>

            <p className="browser-limitation">
              CloakBrowser eliminates standard automation signals; it operates in an isolated Docker container with host evidence retention.
            </p>
          </div>
        </article>

        <article
          className="demo-card demo-secondary demo-recon"
          aria-labelledby="recon-title"
        >
          <div className="demo-card-topline">
            <span className="demo-kicker">Controlled target scope</span>
            <Network size={19} aria-hidden="true" />
          </div>
          <ReconVisual />
          <div className="demo-copy">
            <h3 id="recon-title">Map first. Then verify.</h3>
            <p>
              Resolve an allowlisted lab, discover reachable ports, and inspect
              actual HTTP and TLS responses before reporting. An open port is a
              lead, not a finding.
            </p>
            <a
              href={evidence("claude-network-120/reports/network.html")}
              target="_blank"
              rel="noreferrer"
            >
              Read the verified inventory <ArrowUpRight size={16} />
            </a>
          </div>
        </article>

        <article
          className="demo-card demo-secondary demo-parallel"
          aria-labelledby="parallel-title"
        >
          <div className="demo-card-topline">
            <span className="demo-kicker">Asynchronous background jobs</span>
            <Pulse size={19} aria-hidden="true" />
          </div>
          <JobsVisual />
          <div className="demo-copy">
            <h3 id="parallel-title">Keep the investigation moving.</h3>
            <p>
              Launch long-running scans in the background while verifying
              another lead in parallel. Inspect partial output at any point and
              return to the same job log.
            </p>
            <a
              href={evidence("claude-recovery-120/reports/recovery.html")}
              target="_blank"
              rel="noreferrer"
            >
              See a recovered investigation <ArrowUpRight size={16} />
            </a>
          </div>
        </article>

        <article
          className="demo-card demo-secondary demo-workspaces"
          aria-labelledby="workspaces-title"
        >
          <div className="demo-card-topline">
            <span className="demo-kicker">Concurrent multi-agent isolation</span>
            <HardDrives size={19} aria-hidden="true" />
          </div>
          <div className="demo-workspaces-body">
            <WorkspacesVisual />
            <div className="demo-copy demo-copy--workspaces">
              <h3 id="workspaces-title">Separate work. Separate workspaces.</h3>
              <p>
                Each connected STDIO client owns its Hercules session, Kali
                container, auto-allocated loopback ports, and host workspace
                directory. Stopping one session cleans up only its owned
                container without touching another client’s active jobs or
                retained files.
              </p>
            </div>
          </div>
        </article>
      </div>

      <div className="capability-footnote">
        <p>
          Demonstrations execute against disposable local labs. Hercules returns
          real tool results; model investigation narration is scripted.
        </p>
        <a
          className="text-link"
          href="https://github.com/0xMihirK/hercules-mcp#capabilities-and-mcp-surface"
        >
          View documentation on GitHub <ArrowUpRight size={18} />
        </a>
      </div>
    </section>
  );
}
