import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ArrowRight } from "@phosphor-icons/react/ArrowRight";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { Browser } from "@phosphor-icons/react/Browser";
import { Check } from "@phosphor-icons/react/Check";
import { Circle } from "@phosphor-icons/react/Circle";
import { FolderOpen } from "@phosphor-icons/react/FolderOpen";
import { HardDrives } from "@phosphor-icons/react/HardDrives";
import { LockKey } from "@phosphor-icons/react/LockKey";
import { Network } from "@phosphor-icons/react/Network";
import { Pulse } from "@phosphor-icons/react/Pulse";
import { ShieldCheck } from "@phosphor-icons/react/ShieldCheck";
import { TerminalWindow } from "@phosphor-icons/react/TerminalWindow";

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
          Discovery &amp; verification sweep
        </span>
        <small>172.30.102.10 · allowlisted lab</small>
      </div>
      <div className="recon-board-body">
        <div className="recon-scope-node">
          <svg
            className="recon-radar-svg"
            viewBox="0 0 64 64"
            aria-hidden="true"
          >
            <circle
              cx="32"
              cy="32"
              r="28"
              fill="none"
              stroke="rgba(243,239,233,0.18)"
              strokeWidth="1"
              strokeDasharray="3 3"
            />
            <circle
              cx="32"
              cy="32"
              r="20"
              fill="none"
              stroke="rgba(255,106,43,0.34)"
              strokeWidth="1"
            />
            <circle
              cx="32"
              cy="32"
              r="11"
              fill="#141110"
              stroke="#ff6a2b"
              strokeWidth="1.4"
            />
            <line
              x1="32"
              y1="4"
              x2="32"
              y2="60"
              stroke="rgba(243,239,233,0.12)"
              strokeWidth="1"
            />
            <line
              x1="4"
              y1="32"
              x2="60"
              y2="32"
              stroke="rgba(243,239,233,0.12)"
              strokeWidth="1"
            />
            <g className="radar-sweep-group">
              <path
                d="M32 32 L32 6 A26 26 0 0 1 54 18 Z"
                fill="rgba(255,106,43,0.28)"
              />
              <line
                x1="32"
                y1="32"
                x2="32"
                y2="6"
                stroke="#ffb48a"
                strokeWidth="1.6"
              />
            </g>
            <circle
              className="radar-blip"
              cx="45"
              cy="17"
              r="3.2"
              fill="#ffb48a"
            />
            <circle cx="32" cy="32" r="3.2" fill="#ff6a2b" />
          </svg>
          <strong>Scoped local lab</strong>
          <small>3 reachable ports</small>
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
              stroke="#ff6a2b"
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
              <span>HTTP sign-in</span>
            </span>
            <em className="recon-badge">200 OK</em>
          </div>
          <div className="recon-service recon-service--proxy">
            <span className="recon-service-main">
              <Network size={16} aria-hidden="true" />
              <code>8080</code>
              <span>HTTP proxy</span>
            </span>
            <em className="recon-badge">Verified</em>
          </div>
          <div className="recon-service recon-service--tls">
            <span className="recon-service-main">
              <ShieldCheck size={16} aria-hidden="true" />
              <code>8443</code>
              <span>HTTPS TLS</span>
            </span>
            <em className="recon-badge">CA valid</em>
          </div>
        </div>
      </div>
      <div className="recon-board-foot">
        <Check size={15} aria-hidden="true" /> Discovery creates leads. Service
        verification creates evidence.
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
          Parallel job orchestration
        </span>
        <span className="job-live">
          <i />
          job_8f2a active
        </span>
      </div>
      <div className="job-lanes">
        <div className="job-lane job-lane--running">
          <div className="job-lane-top">
            <span className="job-icon">
              <TerminalWindow size={17} />
            </span>
            <div className="job-lane-title">
              <strong>Long-running scan</strong>
              <small>Buffered output stays readable</small>
            </div>
            <span className="job-status-pill is-running">Running</span>
          </div>
          <div className="job-bar-track" aria-hidden="true">
            <i className="job-bar-fill job-bar-fill--stream" />
          </div>
        </div>
        <div className="job-fork-row" aria-hidden="true">
          <svg
            className="job-fork-svg"
            viewBox="0 0 320 26"
            preserveAspectRatio="none"
          >
            <path
              d="M 26 0 L 26 13 L 160 13 L 160 26"
              fill="none"
              stroke="#ff6a2b"
              strokeWidth="1.5"
              strokeDasharray="3 3"
            />
            <path
              d="M 278 26 L 278 13 L 304 13 L 304 0"
              fill="none"
              stroke="rgba(243,239,233,0.45)"
              strokeWidth="1.5"
            />
            <circle cx="26" cy="4" r="3" fill="#ff6a2b" />
            <circle cx="160" cy="22" r="3" fill="#ffb48a" />
            <circle cx="304" cy="4" r="3" fill="#7ce38b" />
          </svg>
          <span>
            Agent pivots to verify a fast lead while background job continues
          </span>
        </div>
        <div className="job-lane job-lane--verify">
          <div className="job-lane-top">
            <span className="job-icon">
              <Browser size={17} />
            </span>
            <div className="job-lane-title">
              <strong>Targeted HTTP &amp; browser check</strong>
              <small>Confirms live route &amp; narrows scope</small>
            </div>
            <span className="job-status-pill is-verified">Verified</span>
          </div>
          <div className="job-bar-track" aria-hidden="true">
            <i className="job-bar-fill job-bar-fill--done" />
          </div>
        </div>
      </div>
      <div className="job-board-foot">
        <Check size={15} aria-hidden="true" /> Reconnect to the background job
        with its earlier output intact.
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
            <small>STDIO session a81f · Port set 15553</small>
          </div>
          <span className="session-state-tag">
            <Circle className="runtime-led" weight="fill" size={8} />
            Active
          </span>
        </div>
        <div className="session-pipeline">
          <div className="session-node">
            <HardDrives size={18} />
            <div>
              <b>Kali container A</b>
              <small>Started on request</small>
            </div>
          </div>
          <div className="session-wire" aria-hidden="true">
            <i />
            <ArrowRight size={14} />
          </div>
          <div className="session-node">
            <FolderOpen size={18} />
            <div>
              <b>Workspace A</b>
              <small>Reports &amp; raw evidence</small>
            </div>
          </div>
        </div>
      </div>
      <div className="workspace-separator" aria-hidden="true">
        <i />
        <span className="separator-badge">
          <LockKey size={14} />
          Isolated PID, ports &amp; mounts
        </span>
        <i />
      </div>
      <div className="session-pod session-pod--b">
        <div className="session-pod-head">
          <TerminalWindow size={18} />
          <div>
            <strong>Client B · Codex</strong>
            <small>STDIO session c39d · Port set 15554</small>
          </div>
          <span className="session-state-tag">
            <Circle className="runtime-led" weight="fill" size={8} />
            Active
          </span>
        </div>
        <div className="session-pipeline">
          <div className="session-node">
            <HardDrives size={18} />
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
            <FolderOpen size={18} />
            <div>
              <b>Workspace B</b>
              <small>Separate files &amp; logs</small>
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
          <h2 id="capability-title">From page to proof.</h2>
        </div>
        <p>
          See how an agent inspects a real web application in CloakBrowser, maps
          an allowlisted lab, orchestrates background jobs, and isolates
          concurrent workspaces.
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
                Real CloakBrowser session
              </span>
              <span>OWASP Juice Shop · private Docker lab</span>
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
                <span className="browser-local-chip">
                  Edited local-lab capture · 2.5×
                </span>
              </div>
              <div className="juice-video-stage">
                {!reduced && !paused && !videoFailed ? (
                  <video
                    ref={video}
                    key="juice-session"
                    aria-label="Looping recording of Hercules driving a local OWASP Juice Shop browser walkthrough"
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
                    alt="Juice Shop confirms Login Admin and Score Board, with 2 of 186 challenges completed"
                    width="1280"
                    height="600"
                  />
                )}
              </div>
            </div>
          </div>

          <div className="demo-browser-aside">
            <div className="demo-browser-copy">
              <h3 id="juice-title">Test a local challenge. Keep the proof.</h3>
              <p>
                Hercules discovers the private service on port 3000, drives
                CloakBrowser through the authentication flow, captures
                screenshot proof, and writes the structured report. Juice Shop
                confirms Login Admin and Score Board. Model narration is
                scripted.
              </p>
              <div
                className="juice-proof-steps"
                role="group"
                aria-label="Walkthrough stages"
              >
                <div className="proof-step">
                  <b>Private lab</b>
                  <small>172.30.78.10:3000 ready</small>
                </div>
                <ArrowRight size={16} aria-hidden="true" />
                <div className="proof-step">
                  <b>Browser check</b>
                  <small>Login path verified</small>
                </div>
                <ArrowRight size={16} aria-hidden="true" />
                <div className="proof-step">
                  <b>Verified result</b>
                  <small>Host report retained</small>
                </div>
              </div>
            </div>

            <div className="demo-outcome">
              <div className="demo-outcome-count">
                2<span>/ 186</span>
              </div>
              <div>
                <strong>
                  <Check size={16} aria-hidden="true" />
                  Two local training challenges verified
                </strong>
                <p>
                  Juice Shop’s built-in challenge tracker confirms Login Admin
                  and Score Board.
                </p>
                <a
                  href={demoAsset("juice-shop-walkthrough.md")}
                  target="_blank"
                  rel="noreferrer"
                >
                  Read the walkthrough{" "}
                  <ArrowUpRight size={15} aria-hidden="true" />
                </a>
              </div>
            </div>

            <details className="demo-transcript">
              <summary>What the recording shows</summary>
              <p>
                The target application runs on a private Docker network with no
                published host port. Hercules starts its Kali runtime on
                request, drives CloakBrowser through MCP across 28 tool calls,
                and writes a Markdown and HTML report that remains in the host
                workspace after the container stops.{" "}
                <a
                  href={demoAsset("juice-shop-walkthrough.md")}
                  target="_blank"
                  rel="noreferrer"
                >
                  Read the verified walkthrough.
                </a>{" "}
                <a
                  href={demoAsset("juice-shop-session.mp4")}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open the full-size recording.
                </a>
              </p>
            </details>
            <p className="browser-limitation">
              CloakBrowser reduces common automation signals; it does not
              guarantee CAPTCHA or bot-detection bypass.
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
