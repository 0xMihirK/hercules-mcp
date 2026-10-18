import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ArrowLeft } from "@phosphor-icons/react/ArrowLeft";
import { Browser } from "@phosphor-icons/react/Browser";
import { Check } from "@phosphor-icons/react/Check";
import { Code } from "@phosphor-icons/react/Code";
import { FolderOpen } from "@phosphor-icons/react/FolderOpen";
import { FunnelSimple } from "@phosphor-icons/react/FunnelSimple";
import { Info } from "@phosphor-icons/react/Info";
import { Network } from "@phosphor-icons/react/Network";
import { Stack } from "@phosphor-icons/react/Stack";
import { TerminalWindow } from "@phosphor-icons/react/TerminalWindow";
import { X } from "@phosphor-icons/react/X";

const asset = (path: string) => import.meta.env.BASE_URL + "assets/" + path;
type Feature = "hercules" | "docker" | "browser" | "parallel" | "workspaces" | "filter";

const details: Record<Feature, { title: string; text: string }> = {
  hercules: { title: "One connection to your tools.", text: "Hercules runs on your computer and connects compatible agents through STDIO MCP. Your agent explicitly starts the Kali runtime when it needs the tools." },
  docker: { title: "Kali tools, inside Docker.", text: "Selected security tools run in a session-owned container rather than being installed on your host. You control networking, permissions, and target scope; Docker is not an absolute security boundary." },
  browser: { title: "A browser your agent can control.", text: "The optional CloakBrowser runtime can navigate, click, fill forms, and capture screenshots in headless sessions. It reduces common automation signals without guaranteeing CAPTCHA or bot-detection avoidance." },
  parallel: { title: "Several tools. One investigation.", text: "Your agent can run independent checks concurrently within configured limits and review background-job output. Tools in the active session share its workspace, so a browser check can build on a scan result." },
  workspaces: { title: "A workspace for each investigation.", text: "A connection has one active workspace and can inspect retained workspaces; creating a fresh session stops its current runtime. Separate client connections own independent runtimes and workspaces." },
  filter: { title: "Less routine noise in your context.", text: "Tool-specific filters remove known scanner chatter while preserving characterized findings and diagnostics. Separate response limits bound large results and report when output is shortened or raw evidence is available." },
};

export function ArchitectureScene({ reduced, paused }: { reduced: boolean; paused: boolean }) {
  const root = useRef<HTMLElement>(null);
  const [hovered, setHovered] = useState<Feature | null>(null);
  const [focused, setFocused] = useState<Feature | null>(null);
  const [selected, setSelected] = useState<Feature | null>(null);
  const [phase, setPhase] = useState("Start on request");
  const [routes, setRoutes] = useState<Record<string, { d: string; x: number; y: number }>>(() => Object.fromEntries(["request", "dispatch", "output", "response", "workspace"].map(key => [key, { d: "", x: 0, y: 0 }])));
  const active = hovered ?? focused ?? selected;
  const current = active ? details[active] : null;

  useEffect(() => {
    const circuit = root.current?.querySelector<HTMLElement>(".scene-circuit");
    if (!circuit) return;
    const measure = () => {
      const origin = circuit.getBoundingClientRect();
      const box = (selector: string) => {
        const r = circuit.querySelector(selector)!.getBoundingClientRect();
        return { x: r.left - origin.left, y: r.top - origin.top, w: r.width, h: r.height };
      };
      const agent = box(".scene-agent-symbol"), bridge = box(".scene-bridge-tile"), bridgeRegion = box(".scene-bridge"), docker = box(".scene-docker");
      const workspace = box(".scene-workspace"), raw = box(".scene-filter-raw"), result = box(".scene-filter-result"), support = box(".scene-support");
      const link = (x1: number, y1: number, x2: number, y2: number) => ({ d: `M${x1},${y1} C${(x1+x2)/2},${y1} ${(x1+x2)/2},${y2} ${x2},${y2}`, x: (x1+x2)/2, y: Math.min(y1,y2)-12 });
      const small = matchMedia("(max-width:960px)").matches;
      const dispatchX = docker.x + docker.w * (small ? .76 : 0);
      const dispatchY = small ? docker.y - 5 : bridge.y + bridge.h / 2;
      setRoutes({
        request: link(agent.x+agent.w+6, agent.y+agent.h/2, bridge.x-7, bridge.y+bridge.h/2),
        dispatch: small
          ? { d:`M${bridge.x+bridge.w/2},${bridgeRegion.y+bridgeRegion.h+5} V${docker.y-20} Q${bridge.x+bridge.w/2},${docker.y-10} ${dispatchX},${docker.y-10} V${dispatchY}`, x:dispatchX+12, y:docker.y-22 }
          : link(bridge.x+bridge.w+7, bridge.y+bridge.h/2, docker.x-5, dispatchY),
        output: { d:`M${docker.x+docker.w+3},${docker.y+docker.h-25} H${origin.width-12} V${raw.y+raw.h/2} H${raw.x+raw.w+6}`, x:0, y:0 },
        response: { d:`M${result.x-5},${result.y+result.h/2} H${result.x-15} V${support.y+support.h+22} H12 V${agent.y+agent.h/2} H${agent.x-7}`, x:Math.max(28,support.x), y:support.y+support.h+39 },
        workspace: { d:`M${docker.x+28},${docker.y+docker.h+4} V${docker.y+docker.h+25} H${workspace.x-10} V${workspace.y+workspace.h/2} H${workspace.x-4}`, x:0, y:0 },
      });
    };
    const observer = new ResizeObserver(measure);
    observer.observe(circuit);
    measure();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const section = root.current;
    if (!section || reduced || paused) return;
    let visible = false;
    let entered = false;
    const context = gsap.context(() => {
      const loop = gsap.timeline({ paused: true, repeat: -1 });
      loop.call(() => setPhase("Start on request"), [], 0)
        .fromTo(".scene-shell-arrival", { x: 8, y: 10, opacity: 0 }, { x: 0, y: 0, opacity: .7, duration: .7, ease: "power2.out" }, 0)
        .to(".scene-shell-arrival", { opacity: 0, duration: .3 }, .8)
        .fromTo(".scene-route-request.scene-route-pulse", { strokeDashoffset: 1, opacity: 0 }, { strokeDashoffset: 0, opacity: 1, duration: .8, ease: "power2.inOut" }, .3)
        .to(".scene-route-request.scene-route-pulse", { opacity: 0, duration: .4 }, 1.2)
        .fromTo(".scene-route-dispatch.scene-route-pulse", { strokeDashoffset: 1, opacity: 0 }, { strokeDashoffset: 0, opacity: 1, duration: .8, ease: "power2.inOut" }, 1.4)
        .to(".scene-route-dispatch.scene-route-pulse", { opacity: 0, duration: .4 }, 2.3)
        .call(() => setPhase("Agent coordinates checks"), [], 2.5)
        .fromTo(".scene-agent-activity i", { scaleY: .3 }, { scaleY: 1, duration: .4, stagger: .16, yoyo: true, repeat: 5 }, 2.5)
        .fromTo(".scene-tool-progress", { scaleX: .12 }, { scaleX: 1, duration: 3.2, stagger: .32, ease: "power1.inOut" }, 2.5)
        .call(() => setPhase("Filtered results return"), [], 6.5)
        .fromTo(".scene-route-response.scene-route-pulse,.scene-route-output.scene-route-pulse", { strokeDashoffset:1,opacity:0 }, { strokeDashoffset:0,opacity:.8,duration:1.2,stagger:.4 }, 6)
        .to(".scene-route-response.scene-route-pulse,.scene-route-output.scene-route-pulse", { opacity:0,duration:.6 }, 8.8)
        .fromTo(".scene-noise", { opacity: .65, scaleX: 1 }, { opacity: .12, scaleX: .25, duration: 1.1, stagger: .12 }, 6.5)
        .fromTo(".scene-filter-arrow", { x: 4, opacity: .4 }, { x: -4, opacity: 1, duration: 1, ease: "power2.inOut" }, 7)
        .fromTo(".scene-kept", { opacity: .7 }, { opacity: 1, duration: .8, stagger: .2 }, 8)
        .call(() => setPhase("Fresh session, new runtime"), [], 9.5)
        .fromTo(".scene-shell-departure", { x: 0, y: 0, opacity: .8 }, { x: 14, y: -12, opacity: 0, duration: .7, ease: "power2.in" }, 9.5)
        .fromTo(".scene-shell-arrival", { x: -10, y: 12, opacity: 0 }, { x: 0, y: 0, opacity: 1, duration: .7, ease: "power2.out" }, 10.1)
        .fromTo(".scene-replacement-label", { opacity: 0, y: 3 }, { opacity: 1, y: 0, duration: .25 }, 10.1)
        .to(".scene-shell-arrival", { opacity: 0, duration: .4 }, 10.8)
        .to(".scene-replacement-label", { opacity: 0, duration: .3 }, 11.5)
        .call(() => setPhase("Start on request"), [], 12);
      const entrance = gsap.fromTo(".scene-intro", { y: 14 }, { y: 0, duration: .65, stagger: .07, ease: "power2.out", clearProps: "transform", paused: true });
      const sync = () => {
        const running = visible && !document.hidden;
        section.dataset.motion = running ? "playing" : "paused";
        if (running) loop.play(); else loop.pause();
        if (running && !entered) {
          entered = true;
          entrance.play();
        }
      };
      const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); }, { threshold: 0 });
      observer.observe(section.querySelector(".scene-circuit")!);
      document.addEventListener("visibilitychange", sync);
      return () => { observer.disconnect(); document.removeEventListener("visibilitychange", sync); };
    }, section);
    return () => { context.revert(); delete section.dataset.motion; };
  }, [reduced, paused]);

  const interaction = (key: Feature) => ({
    type: "button" as const,
    "aria-pressed": selected === key,
    "aria-controls": "architecture-detail",
    "data-feature": key,
    className: `scene-hotspot${active === key ? " is-active" : ""}`,
    onMouseEnter: () => setHovered(key),
    onMouseLeave: () => setHovered(null),
    onFocus: () => setFocused(key),
    onBlur: () => setFocused(null),
    onClick: () => setSelected(selected === key ? null : key),
  });

  return <section id="architecture" ref={root} className="chapter architecture" aria-labelledby="architecture-title"
    onKeyDown={(event) => { if (event.key === "Escape") { setSelected(null); setHovered(null); setFocused(null); } }}>
    <div className="wrap">
      <div className="feature-heading architecture-heading">
        <h2 id="architecture-title">Powerful tools.<br/>A separate workspace.</h2>
        <p>Your agent coordinates Kali tools in Docker. Hercules manages the runtime, workspaces, and the output returned to your agent.</p>
      </div>

      <div className="workspace-scene" data-active={active ?? "overview"}>
        <div className="scene-caption"><span>Your computer</span><span className="scene-cycle" aria-hidden="true">Illustrated cycle · {reduced || paused ? "Start · work · fresh session" : phase}</span><span><Info size={15} aria-hidden="true"/> Hover or select a part to explore</span></div>
        <div className="scene-circuit">
        <svg className="scene-connections" aria-hidden="true">
          <defs><marker id="scene-arrow" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="5" markerHeight="5" orient="auto"><path d="M1 1L5 3L1 5" fill="none" stroke="currentColor" strokeWidth="1"/></marker></defs>
          {Object.entries(routes).map(([key,route]) => <g key={key}>
            <path className={`scene-route scene-route-${key}`} d={route.d} markerEnd="url(#scene-arrow)"/>
            <path className={`scene-route-pulse scene-route-${key}`} d={route.d} pathLength="1"/>
            {route.d && (key === "request" || key === "dispatch" || key === "response") && <text x={route.x} y={route.y} textAnchor={key === "response" ? "start" : "middle"}>{key === "request" ? "MCP" : key === "dispatch" ? "Run tools" : "Concise response to your agent"}</text>}
          </g>)}
        </svg>
        <div className="scene-execution">
          <div className="scene-agent scene-intro">
            <div className="scene-agent-symbol" aria-hidden="true"><TerminalWindow size={38} weight="light"/><span/><span/></div>
            <h3>Your agent</h3><p>You set the task.<br/>Your agent coordinates.</p>
            <span className="scene-agent-compatibility">Any STDIO MCP client</span>
            <span className="scene-agent-activity" aria-hidden="true"><i/><i/><i/></span>
          </div>
          <div className="scene-gap" aria-hidden="true"/>
          <div className="scene-bridge scene-intro">
            <button {...interaction("hercules")} aria-label="Explore Hercules routing">
              <span className="scene-bridge-tile"><img src={asset("lion.svg")} width="64" height="70" alt=""/></span>
              <strong className="scene-bridge-name">Hercules</strong><span className="scene-node-description">Connect. Coordinate.<br/>Return the result.</span><Info size={14} className="scene-info" aria-hidden="true"/>
            </button>
          </div>
          <div className="scene-gap scene-gap-docker" aria-hidden="true"/>
          <div className={`scene-docker scene-intro${active === "docker" ? " is-active" : ""}`}>
            <span className="scene-shell-trace scene-shell-arrival" aria-hidden="true"/><span className="scene-shell-trace scene-shell-departure" aria-hidden="true"/>
            <span className="scene-replacement-label" aria-hidden="true">Fresh runtime</span>
            <button {...interaction("docker")} aria-label="Explore Docker sandboxing">
              <img src={asset("brands/docker.svg")} width="42" height="42" alt=""/>
              <span><strong>Kali in Docker</strong><small>Session-owned tool runtime</small></span><Info size={16} className="scene-info" aria-hidden="true"/>
            </button>
            <div className="scene-tools">
              <button {...interaction("browser")} aria-label="Explore CloakBrowser control">
                <span className="scene-browser-chrome" aria-hidden="true"><i/><i/><i/><span>local lab</span></span>
                <span className="scene-browser-page" aria-hidden="true"><Browser size={26} weight="light"/><span/><span/><i><Check size={12}/></i></span>
                <strong>Browser control</strong><small>CloakBrowser</small>
                <span className="scene-tool-track" aria-hidden="true"><i className="scene-tool-progress"/></span>
              </button>
              <div className="scene-tool-lanes" aria-label="Example tool categories">
                <div><Network size={20} aria-hidden="true"/><span>Network tools<small>Discover &amp; verify</small></span><i className="scene-tool-track" aria-hidden="true"><b className="scene-tool-progress"/></i></div>
                <div><Code size={20} aria-hidden="true"/><span>Web checks<small>Inspect &amp; test</small></span><i className="scene-tool-track" aria-hidden="true"><b className="scene-tool-progress"/></i></div>
                <div><Stack size={20} aria-hidden="true"/><span>File analysis<small>Examine &amp; correlate</small></span></div>
              </div>
            </div>
            <button {...interaction("parallel")} aria-label="Explore parallel tool execution"><span className="scene-parallel-symbol" aria-hidden="true"><i/><i/><i/></span><span>Independent checks can run together</span><Info size={14} className="scene-info" aria-hidden="true"/></button>
          </div>
        </div>


        <div className="scene-support">
          <button {...interaction("workspaces")} aria-label="Explore managed workspaces">
            <span className="scene-support-heading"><FolderOpen size={21} aria-hidden="true"/><strong>Space for each investigation</strong><Info size={14} className="scene-info" aria-hidden="true"/></span>
            <span className="scene-workspace-stack">
              <span className="scene-workspace"><FolderOpen size={21} weight="light" aria-hidden="true"/><span>Workspace A<small>Active · mounted in this runtime</small></span></span>
              <span className="scene-workspace is-retained"><FolderOpen size={21} weight="light" aria-hidden="true"/><span>Workspace B<small>Retained · available to inspect</small></span></span>
            </span>
            <span className="scene-host-storage">Managed on your computer</span>
          </button>
          <button {...interaction("filter")} aria-label="Explore token-saving output filters">
            <span className="scene-support-heading"><FunnelSimple size={21} aria-hidden="true"/><strong>Token-saving filter</strong><Info size={14} className="scene-info" aria-hidden="true"/></span>
            <span className="scene-filter-flow">
              <span className="scene-filter-result"><small>To your agent</small><span className="scene-kept"><Check size={13} aria-hidden="true"/>Finding</span><span className="scene-kept scene-warning">Warning retained</span></span>
              <span className="scene-filter-gate" aria-hidden="true"><ArrowLeft size={17} className="scene-filter-arrow"/><FunnelSimple size={32} weight="light"/></span>
              <span className="scene-filter-raw"><small>From the tools</small><i className="scene-noise"/><i className="scene-noise"/><i className="scene-kept"/><i className="scene-noise"/><i className="scene-kept"/></span>
            </span>
            <span className="scene-host-storage">Known scanner chatter filtered before the response</span>
          </button>
        </div>
        </div>
        <div id="architecture-detail" className="scene-detail" aria-live="polite" aria-atomic="true">
          <div className="scene-detail-title"><Info size={19} aria-hidden="true"/><h3>{current?.title ?? "Follow the work, from request to response."}</h3></div>
          <p>{current?.text ?? "Explore how Hercules connects your agent to Docker, coordinates tools, and keeps the response concise. Select a part to keep its explanation open."}</p>
          {selected && <button type="button" className="scene-detail-close" aria-label="Clear selected explanation" onClick={() => { root.current?.querySelector<HTMLButtonElement>(`[data-feature="${selected}"]`)?.focus(); setSelected(null); setHovered(null); setFocused(null); }}><X size={18}/></button>}
        </div>
      </div>
      <p className="scene-scope">Tools start only when requested. You control networking, permissions, and target scope.</p>
    </div>
  </section>;
}

export default ArchitectureScene;
