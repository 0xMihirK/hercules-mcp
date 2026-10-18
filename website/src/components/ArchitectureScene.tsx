import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowRight } from "@phosphor-icons/react/ArrowRight";
import { TerminalWindow } from "@phosphor-icons/react/TerminalWindow";
import { Network } from "@phosphor-icons/react/Network";
import { GlobeHemisphereWest } from "@phosphor-icons/react/GlobeHemisphereWest";
import { FileArchive } from "@phosphor-icons/react/FileArchive";
import { Code } from "@phosphor-icons/react/Code";
import { Browsers } from "@phosphor-icons/react/Browsers";
import { Key } from "@phosphor-icons/react/Key";
import { HardDrive } from "@phosphor-icons/react/HardDrive";

gsap.registerPlugin(ScrollTrigger);
const asset = (path: string) => import.meta.env.BASE_URL + "assets/" + path;

const phases = [
  {
    label: "Connect",
    title: "Connected. Tools are not running yet.",
    text: "Your agent registers 47 Hercules tools over STDIO MCP. The Kali container stays stopped until the agent explicitly starts a session.",
  },
  {
    label: "Start tools",
    title: "Start a workspace when the work begins.",
    text: "Hercules boots your session’s isolated Kali container and mounts a dedicated host workspace directory for raw outputs and reports.",
  },
  {
    label: "Separate sessions",
    title: "A separate container for each session.",
    text: "Another agent gets its own Hercules session, Kali container, working files, and allocated ports without colliding with Session A.",
  },
  {
    label: "Stop tools",
    title: "Stop your container. Other sessions continue.",
    text: "Hercules stops Session A’s container while preserving its host workspace artifacts. Session B keeps running uninterrupted.",
  },
];

function Connection({
  label,
  sublabel,
  active,
  docker = false,
}: {
  label: string;
  sublabel: string;
  active: boolean;
  docker?: boolean;
}) {
  return (
    <div
      className={
        "flow-connection" +
        (docker ? " docker-connection" : "") +
        (active ? " is-active" : "")
      }
      aria-hidden="true"
    >
      <span className="conduit-label">{label}</span>
      <div className="conduit-rail">
        <svg
          viewBox="0 0 120 20"
          className="conduit-svg"
          preserveAspectRatio="none"
        >
          <line x1="0" y1="10" x2="108" y2="10" className="conduit-track" />
          <line x1="0" y1="10" x2="108" y2="10" className="conduit-pulse" />
          <polygon points="106,5 118,10 106,15" className="conduit-arrow" />
        </svg>
        <b className="connection-packet" />
      </div>
      <small className="conduit-sublabel">{sublabel}</small>
    </div>
  );
}

export default function ArchitectureScene({
  reduced,
  paused,
}: {
  reduced: boolean;
  paused: boolean;
}) {
  const root = useRef<HTMLElement>(null),
    scene = useRef<HTMLDivElement>(null),
    userSelected = useRef(false),
    [phase, setPhase] = useState(1);

  useEffect(() => {
    if (reduced || paused || !root.current || !scene.current) return;
    const context = gsap.context(() => {
      gsap.fromTo(
        ".architecture-heading > *",
        { y: 24, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.65,
          stagger: 0.08,
          ease: "power3.out",
          scrollTrigger: {
            trigger: root.current,
            start: "top 82%",
            once: true,
          },
        },
      );
      ScrollTrigger.create({
        trigger: scene.current,
        start: "top 68%",
        end: "bottom 28%",
        onUpdate(self) {
          if (userSelected.current) return;
          const idx = Math.min(3, Math.max(0, Math.floor(self.progress * 4)));
          setPhase((prev) => (prev === idx ? prev : idx));
        },
      });
    }, root);
    return () => context.revert();
  }, [reduced, paused]);

  useEffect(() => {
    if (reduced || paused || !root.current) return;
    const context = gsap.context(() => {
      gsap.fromTo(
        ".connection-packet",
        { xPercent: -100 },
        {
          xPercent: 520,
          duration: 1.05,
          ease: "power2.out",
        },
      );
      if (phase === 1 || phase === 2) {
        gsap.fromTo(
          ".runtime-capability",
          { opacity: 0.4, y: 6 },
          {
            opacity: 1,
            y: 0,
            duration: 0.38,
            stagger: 0.045,
            ease: "power3.out",
          },
        );
      }
      gsap.fromTo(
        ".sandbox-caption",
        { opacity: 0.35, y: 8 },
        { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" },
      );
    }, root);
    return () => context.revert();
  }, [phase, reduced, paused]);

  const selectPhase = (idx: number) => {
    userSelected.current = true;
    setPhase(idx);
  };

  const running = phase === 1 || phase === 2;
  const stoppedAfterRun = phase === 3;

  return (
    <section
      id="architecture"
      ref={root}
      className="chapter architecture"
      aria-labelledby="architecture-title"
    >
      <div className="wrap">
        <div className="feature-heading feature-heading--split architecture-heading">
          <h2 id="architecture-title">
            Kali in a container.
            <br />A separate workspace.
          </h2>
          <p>
            Hercules runs on your computer as a lightweight STDIO MCP host
            server. Heavy security tools execute inside a session-owned Kali
            Docker container.
          </p>
        </div>
        <div
          ref={scene}
          data-ui
          className={"sandbox-demonstration phase-" + phase}
        >
          <div
            className="sandbox-controls"
            role="group"
            aria-label="Explore the illustrated session lifecycle"
          >
            {phases.map((item, i) => (
              <button
                key={item.label}
                aria-pressed={phase === i}
                onClick={() => selectPhase(i)}
              >
                <span className="phase-dot" aria-hidden="true" />
                <span>{item.label}</span>
              </button>
            ))}
          </div>
          <div
            className="software-flow"
            role="group"
            aria-label="Your agent connects to Hercules on your computer. Hercules manages a separate Kali Docker container containing the security tools."
          >
            <div className="agent-request arch-node">
              <div className="arch-node-top">
                <span className="arch-node-badge">MCP client</span>
                <span className="arch-node-state is-online">Connected</span>
              </div>
              <div className="arch-node-Identity">
                <TerminalWindow size={32} aria-hidden="true" />
                <div>
                  <h3>Your agent</h3>
                  <p>Claude, Codex, Gemini, or custom client</p>
                </div>
              </div>
              <blockquote>
                “Assess target ports, web routes, and auth flows.”
              </blockquote>
              <div className="arch-node-meta">
                <span>Scope controlled by user</span>
                <code>47 tools registered</code>
              </div>
            </div>
            <Connection
              label="STDIO MCP"
              sublabel="JSON-RPC stream"
              active={true}
            />
            <div className="hercules-bridge arch-node">
              <div className="arch-node-top">
                <span className="arch-node-badge">Host server</span>
                <span className="arch-node-state is-online">Active</span>
              </div>
              <img src={asset("lion.svg")} width="76" height="84" alt="" />
              <h3>Hercules</h3>
              <p>
                Manages sessions, filters noisy tool output, and tracks
                background jobs.
              </p>
              <div className="arch-node-meta">
                <span>Runs on your computer</span>
                <code>session_id: a8f2</code>
              </div>
            </div>
            <Connection
              label={
                running
                  ? "Docker API · Active"
                  : stoppedAfterRun
                    ? "Container stopped"
                    : "Starts on request"
              }
              sublabel={
                running ? "Exec + volume mount" : "On-demand lifecycle"
              }
              active={running}
              docker
            />
            <div
              className={
                "tool-container arch-node" +
                (running ? " is-running" : "") +
                (stoppedAfterRun ? " is-stopped-clean" : "")
              }
            >
              <header>
                <div className="container-header-main">
                  <img
                    src={asset("brands/docker.svg")}
                    width="42"
                    height="42"
                    alt="Docker"
                  />
                  <div>
                    <h3>Kali Linux</h3>
                    <p>Docker container · Session A</p>
                  </div>
                </div>
                <span
                  className={
                    "container-pill" +
                    (running
                      ? " is-running"
                      : stoppedAfterRun
                        ? " is-preserved"
                        : "")
                  }
                >
                  {running
                    ? "Running"
                    : stoppedAfterRun
                      ? "Stopped · Saved"
                      : "Standby"}
                </span>
              </header>
              <div className="runtime-capabilities">
                <div className="runtime-capability">
                  <Network size={22} />
                  <span>
                    Network<small>Nmap, RustScan, masscan</small>
                  </span>
                </div>
                <div className="runtime-capability">
                  <GlobeHemisphereWest size={22} />
                  <span>
                    Web &amp; API<small>Nuclei, ffuf, Nikto, SQLMap</small>
                  </span>
                </div>
                <div className="runtime-capability">
                  <Browsers size={22} />
                  <span>
                    Browser<small>Isolated Chromium &amp; DOM</small>
                  </span>
                </div>
                <div className="runtime-capability">
                  <FileArchive size={22} />
                  <span>
                    Forensics<small>Binwalk, YARA, ExifTool</small>
                  </span>
                </div>
                <div className="runtime-capability">
                  <Key size={22} />
                  <span>
                    Cracking<small>John, Hydra, Hashid</small>
                  </span>
                </div>
                <div className="runtime-capability">
                  <Code size={22} />
                  <span>
                    Shell &amp; Jobs<small>Async tasks &amp; pipelines</small>
                  </span>
                </div>
              </div>
              <div
                className={
                  "volume-retention" +
                  (running || stoppedAfterRun ? " is-mounted" : "")
                }
              >
                <HardDrive size={18} />
                <span>
                  Host evidence mount: <code>/opt/workspace/session-a</code>
                </span>
                <strong>
                  {stoppedAfterRun
                    ? "Artifacts preserved on host"
                    : running
                      ? "Writing raw logs & reports"
                      : "Mounted when started"}
                </strong>
              </div>
              <footer>
                <span className="container-status">
                  {running
                    ? "Running for Session A"
                    : stoppedAfterRun
                      ? "Container stopped · Evidence kept"
                      : "Container stopped (0 CPU / RAM)"}
                </span>
                <span>Isolated from host packages</span>
              </footer>
            </div>
          </div>
          <div className={"second-session" + (phase >= 2 ? " is-active" : "")}>
            <div className="second-session-header">
              <span className="second-session-badge">
                {phase >= 2
                  ? "Parallel Session B · Running"
                  : "Multi-session isolation"}
              </span>
              {phase < 2 && (
                <button
                  type="button"
                  className="second-session-trigger"
                  onClick={() => selectPhase(2)}
                >
                  Preview parallel session <ArrowRight size={15} />
                </button>
              )}
            </div>
            <div className="secondary-flow">
              <div className="secondary-node">
                <TerminalWindow size={18} />
                <span>Another agent</span>
                <code>Client B</code>
              </div>
              <ArrowRight size={16} aria-hidden="true" />
              <div className="secondary-node">
                <span>Hercules Session B</span>
                <code>session_id: b4c9</code>
              </div>
              <ArrowRight size={16} aria-hidden="true" />
              <div className="secondary-node is-container">
                <img
                  src={asset("brands/docker.svg")}
                  width="20"
                  height="20"
                  alt=""
                />
                <span>Kali Container B</span>
                <code>
                  {phase >= 2
                    ? "Running · :9223 · /opt/workspace/session-b"
                    : "On-demand container & port pool"}
                </code>
              </div>
            </div>
          </div>
          <div className="sandbox-caption" aria-live="polite">
            <div>
              <span className="caption-step">{phases[phase].label}</span>
              <h3>{phases[phase].title}</h3>
            </div>
            <p>{phases[phase].text}</p>
          </div>
        </div>
        <p className="sandbox-scope">
          You control networking, permissions, and target scope. Container
          isolation depends on those settings.
        </p>
      </div>
    </section>
  );
}
