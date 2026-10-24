import { useEffect, useRef, useState, type FocusEvent, type MouseEvent } from "react";
import gsap from "gsap";
import { Check } from "@phosphor-icons/react/Check";
import { FolderOpen } from "@phosphor-icons/react/FolderOpen";
import { FunnelSimple } from "@phosphor-icons/react/FunnelSimple";
import { Info } from "@phosphor-icons/react/Info";
import { TerminalWindow } from "@phosphor-icons/react/TerminalWindow";
import { X } from "@phosphor-icons/react/X";

const asset = (path: string) => import.meta.env.BASE_URL + "assets/" + path;
const details = {
  hercules: { title: "Your agent directs. Hercules connects.", text: "Hercules exposes tools over STDIO MCP and manages their execution. Connecting loads the tool schemas; your agent explicitly starts the Docker runtime when it needs it." },
  docker: { title: "A tool environment inside Docker.", text: "Selected Kali tools run in a session-owned container rather than being installed on your host. You control networking, permissions, and target scope; Docker is not an absolute security boundary." },
  browser: { title: "Browser automation, with limits.", text: "Obscura handles pages, screenshots, and named sessions in the Kali container. It does not enforce CSP, has incomplete browser fidelity, and does not support native downloads. Browser traffic is not confined: with host networking it can reach host-local and private-network services. Browse only trusted, authorized targets." },
  network: { title: "From a target to a service map.", text: "Use Amass and DNS tools to discover hosts, then Nmap to inspect reachable services. The agent can follow up with curl or Ncat to check what a service actually returns." },
  protocol: { title: "Check a service at the protocol level.", text: "Use Ncat for controlled TCP or UDP exchanges and Hping3 for packet-level probes against authorized targets. Compare responses with a known control before treating silence or a timeout as a finding." },
  web: { title: "Discover, then verify web issues.", text: "Use ffuf for endpoint discovery, Nuclei for template-based checks, and SQLMap for database injection testing. Browser checks can help the agent verify a result instead of treating every scanner alert as a finding." },
  files: { title: "Follow clues inside files.", text: "ExifTool and Steghide help examine metadata and hidden content. Shell and workspace tools let the agent inspect saved artifacts and continue an investigation." },
  reverse: { title: "Start with binary and firmware evidence.", text: "Binwalk can identify and extract embedded files; shell access to binutils such as readelf and objdump helps triage executable structure. This is basic analysis, not a full decompiler or reverse-engineering service." },
  research: { title: "Research and test applicability.", text: "SearchSploit searches exploit references; the optional Metasploit bundle supports module search and managed execution. These are operator-scoped capabilities, not an automatic claim that a service is exploitable." },
  passwords: { title: "Test credentials in an authorized lab.", text: "Hydra supports online authentication checks, while John the Ripper works with password hashes. The agent can combine these with shell tools and files in the active workspace." },
  parallel: { title: "Independent work can overlap.", text: "Hercules supports concurrent calls within configured limits and background jobs with partial output. A service scan can keep running while the agent inspects a page or examines a file." },
  workspaces: { title: "Fresh runtime. Separate investigation.", text: "Creating a fresh session stops the connection’s current runtime and creates a new workspace; prior workspaces remain inspectable. Separate client connections can own independent runtimes and workspaces." },
  filter: { title: "Keep useful output in the conversation.", text: "Within Hercules, tool-specific filters remove known routine chatter while preserving characterized findings and diagnostics. Separate response-size limits can shorten large results, with raw-output availability disclosed." },
};
type Feature = keyof typeof details;
const capabilities = [
  { key: "browser", title: "Browser control", tools: "Obscura · no CSP" },
  { key: "network", title: "Recon & services", tools: "Amass · DNS · Nmap" },
  { key: "web", title: "Web assessment", tools: "ffuf · Nuclei · SQLMap" },
  { key: "protocol", title: "Protocol testing", tools: "Ncat · Hping3" },
  { key: "files", title: "Files & forensics", tools: "ExifTool · Steghide · workspace files" },
  { key: "reverse", title: "Reverse engineering", tools: "Binwalk · readelf · objdump" },
  { key: "research", title: "Exploit research", tools: "SearchSploit · Metasploit" },
  { key: "passwords", title: "Credential testing", tools: "Hydra · John the Ripper" },
] as const;

// Small software vignettes describe capabilities, not captured interfaces or findings.
const illustrations = {
  browser: <><rect x="2" y="4" width="66" height="49" rx="2"/><path d="M2 15H68M9 10H11M16 10H18M23 10H25M10 23H33M10 30H47M10 37H37"/><rect className="map-mini-field" x="43" y="40" width="17" height="7"/><path className="map-mini-cursor" d="M53 32L53 44L57 40L62 40Z"/></>,
  network: <><rect x="2" y="23" width="20" height="16"/><path d="M22 31H34V10H49M34 31H49M34 31V52H49M7 28H16M7 33H13"/><rect x="49" y="3" width="20" height="14"/><rect x="49" y="24" width="20" height="14"/><rect x="49" y="45" width="20" height="14"/><path className="map-mini-node" d="M55 10H63"/><path className="map-mini-node" d="M55 31H63"/><path className="map-mini-node" d="M55 52H63"/></>,
  protocol: <><path d="M3 30H16L21 19L29 43L37 24L43 30H69M10 14H26M46 14H62M11 47H24M48 47H62"/><circle className="map-mini-accent" cx="35" cy="14" r="3"/><circle className="map-mini-accent" cx="36" cy="47" r="3"/></>,
  web: <><rect x="3" y="5" width="48" height="48"/><path d="M3 15H51M10 10H12M17 10H19M10 24H37M10 33H31M10 42H27"/><circle className="map-mini-accent" cx="48" cy="36" r="13"/><path className="map-mini-accent" d="M58 46L68 56M43 36L47 40L54 32"/></>,
  files: <><path d="M4 17V7H40L51 18V29M40 7V18H51M10 14H31M10 21H30"/><path d="M13 32V25H40L47 32H66V54H13Z"/><path className="map-mini-accent" d="M24 47L29 42L24 37M36 37H53M36 43H57M36 49H49"/><path d="M4 32V51H8"/></>,
  reverse: <><rect x="4" y="8" width="64" height="44" rx="2"/><path d="M14 19H28M14 27H22M14 35H27M37 18L30 30L37 42M49 18L56 30L49 42M42 16L39 44" className="map-mini-accent"/></>,
  research: <><path d="M4 8H28V43H4ZM10 16H22M10 22H19M10 28H22M10 35H16M12 48H34V14"/><path d="M38 29H47M44 25L48 29L44 33"/><rect className="map-mini-accent" x="51" y="16" width="17" height="29"/><path className="map-mini-accent" d="M56 24L63 30L56 36Z"/></>,
  passwords: <><rect x="3" y="7" width="40" height="43"/><path d="M3 17H43M10 12H12M17 12H19M10 27H34M10 37H12M17 37H19M24 37H26M31 37H33"/><circle className="map-mini-accent" cx="53" cy="38" r="9"/><path className="map-mini-accent" d="M53 29V15H63M59 15V21M53 21H59"/></>,
};
type Point = { x: number; y: number };
export function roundedRoute(input: Point[], radius = 12) {
  const points = input.filter((point, index) => !index || point.x !== input[index - 1].x || point.y !== input[index - 1].y);
  if (points.length < 2) return "";
  let d = `M${points[0].x},${points[0].y}`;
  for (let index = 1; index < points.length - 1; index++) {
    const previous = points[index - 1], corner = points[index], next = points[index + 1];
    const before = Math.hypot(corner.x - previous.x, corner.y - previous.y);
    const after = Math.hypot(next.x - corner.x, next.y - corner.y);
    const r = Math.min(radius, before / 2, after / 2);
    d += ` L${corner.x - (corner.x - previous.x) * r / before},${corner.y - (corner.y - previous.y) * r / before}`;
    d += ` Q${corner.x},${corner.y} ${corner.x + (next.x - corner.x) * r / after},${corner.y + (next.y - corner.y) * r / after}`;
  }
  return d + ` L${points.at(-1)!.x},${points.at(-1)!.y}`;
}
export function architectureRoutes(ports: Record<string, Point>) {
  const { agent, hub, dispatch, docker, agentReturn, filter, filterInput, result, mount, workspace } = ports;
  const request = (from: Point, to: Point) => {
    const x = (from.x + to.x) / 2;
    return roundedRoute([from, { x, y: from.y }, { x, y: to.y }, to]);
  };
  const left = (agentReturn.x + filter.x) / 2, right = (result.x + filterInput.x) / 2;
  return {
    request: request(agent, hub) + " " + request(dispatch, docker),
    response: roundedRoute([result, { x: right, y: result.y }, { x: right, y: filterInput.y }, filterInput, filter, { x: left, y: filter.y }, { x: left, y: agentReturn.y }, agentReturn]),
    mount: roundedRoute([mount, { x: mount.x, y: workspace.y - 16 }, { x: workspace.x, y: workspace.y - 16 }, workspace]),
    arrows: [{ x: (right + filterInput.x) / 2, y: filterInput.y }, { x: (left + filter.x) / 2, y: filter.y }],
    mountLabel: { x: mount.x - 12, y: (mount.y + workspace.y) / 2 },
  };
}
const runtimeLabels = { request: "Requesting tools", working: "Running…", results: "Returning results", complete: "Complete", requested: "New session requested", stopping: "Stopping", stopped: "Runtime stopped", starting: "Starting", ready: "Ready" };
type RuntimeState = keyof typeof runtimeLabels;
type MotionTargets = { runtime: gsap.TweenTarget; rows: gsap.TweenTarget; bars: gsap.TweenTarget; request: gsap.TweenTarget; response: gsap.TweenTarget; noise: gsap.TweenTarget };
export function createArchitectureLoop(targets: MotionTargets, stage: (state: RuntimeState) => void, replace: (value: boolean) => void, stable: () => void) {
  return gsap.timeline({ paused: true, repeat: -1 })
    .call(() => stage("request"), [], 0)
    .set(targets.bars, { scaleX: 0 }, 0)
    .set(targets.noise, { opacity: 1, x: 0 }, 0)
    .fromTo(targets.request, { strokeDashoffset: 1, opacity: 0 }, { strokeDashoffset: 0, opacity: 1, duration: .7, immediateRender: false }, 0)
    .to(targets.request, { opacity: 0, duration: .1 }, .7)
    .call(() => stage("working"), [], .8)
    .to(targets.bars, { scaleX: 1, duration: 2.6, stagger: .4, ease: "power1.inOut" }, .8)
    .call(() => stage("results"), [], 4.2)
    .fromTo(targets.response, { strokeDashoffset: 1, opacity: 0 }, { strokeDashoffset: 0, opacity: 1, duration: 1.2, immediateRender: false }, 4.2)
    .to(targets.noise, { opacity: .2, x: -6, duration: .5 }, 4.6)
    .to(targets.response, { opacity: 0, duration: .15 }, 5.4)
    .call(() => stage("complete"), [], 5.4)
    .call(() => { replace(true); stage("requested"); }, [], 7)
    .call(() => stage("stopping"), [], 7.15)
    .to(targets.rows, { opacity: 0, y: 6, duration: .65, stagger: .04, ease: "power2.in" }, 7.15)
    .to(targets.runtime, { opacity: 0, scale: .96, filter: "grayscale(1)", duration: 1.25, ease: "power2.in" }, 7.15)
    .call(() => stage("stopped"), [], 8.4)
    .set(targets.bars, { scaleX: 0 }, 8.4)
    .call(() => stage("starting"), [], 9.1)
    .to(targets.runtime, { opacity: 1, scale: 1.02, filter: "grayscale(0)", duration: 1.2, ease: "power2.out" }, 9.1)
    .to(targets.rows, { opacity: 1, y: 0, duration: 1.1, stagger: { each: .04, from: "end" }, ease: "power2.out" }, 9.3)
    .to(targets.runtime, { scale: 1, duration: .5, ease: "power2.out" }, 10.3)
    .call(() => { stage("ready"); replace(false); stable(); }, [], 10.8)
    .to({}, { duration: 4.2 }, 10.8);
}

export function ArchitectureScene({ reduced, paused }: { reduced: boolean; paused: boolean }) {
  const root = useRef<HTMLElement>(null);
  const revealFrame = useRef(0);
  const layoutTarget = useRef<HTMLButtonElement | null>(null);
  const syncReveal = useRef<(() => void) | null>(null);
  useEffect(() => {
    const release = () => { layoutTarget.current = null; cancelAnimationFrame(revealFrame.current); };
    const inputs = ["wheel", "touchstart", "pointerdown", "keydown"];
    inputs.forEach(type => window.addEventListener(type, release, { capture: true, passive: true }));
    return () => { release(); inputs.forEach(type => window.removeEventListener(type, release, true)); };
  }, []);
  const inspecting = useRef(false);
  const transitioning = useRef(false);
  const syncMotion = useRef<(() => void) | null>(null);
  const [hovered, setHovered] = useState<Feature | null>(null);
  const [focused, setFocused] = useState<Feature | null>(null);
  const [selected, setSelected] = useState<Feature | null>(null);
  const [runtimeState, setRuntimeState] = useState<RuntimeState>("ready");
  const [replacing, setReplacing] = useState(false);
  const [routes, setRoutes] = useState({ request: "", response: "", mount: "", arrows: [] as Point[], mountLabel: { x: 0, y: 0 } });
  const active = focused ?? selected ?? hovered;
  const current = active ? details[active] : null;
  inspecting.current = active !== null;
  useEffect(() => { syncMotion.current?.(); root.current?.querySelector(".map-detail")?.scrollTo({ top: 0, behavior: "instant" }); }, [active]);

  useEffect(() => {
    const map = root.current?.querySelector<HTMLElement>(".architecture-map");
    if (!map) return;
    const measure = () => {
      // Layout offsets keep ports attached after resizing during a runtime transition.
      const point = (selector: string) => {
        const port = map.querySelector<HTMLElement>(selector)!;
        let x = port.offsetLeft + port.offsetWidth / 2, y = port.offsetTop + port.offsetHeight / 2;
        for (let parent = port.offsetParent as HTMLElement | null; parent && parent !== map; parent = parent.offsetParent as HTMLElement | null) {
          x += parent.offsetLeft + parent.clientLeft;
          y += parent.offsetTop + parent.clientTop;
        }
        return { x, y };
      };
      setRoutes(architectureRoutes({
        agent: point(".map-agent-port"), hub: point(".map-hub-input"), dispatch: point(".map-hub-dispatch"), docker: point(".map-docker-port"),
        agentReturn: point(".map-agent-return"), filter: point(".map-filter-output"), filterInput: point(".map-filter-input"), result: point(".map-docker-return"),
        mount: point(".map-mount-port"), workspace: point(".map-workspace-port"),
      }));
      syncReveal.current?.();
    };
    const observer = new ResizeObserver(measure);
    observer.observe(map);
    const main = map.closest("main");
    if (main) observer.observe(main);
    map.querySelectorAll(".map-agent,.map-filter,.map-hub,.map-runtime-stage,.map-workspaces").forEach(node => observer.observe(node));
    measure();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const section = root.current;
    setReplacing(false);
    transitioning.current = false;
    if (!section || reduced || paused) return;
    let visible = false;
    const context = gsap.context(() => {
      const loop = createArchitectureLoop({
        runtime: section.querySelector(".map-runtime-unit")!, rows: section.querySelectorAll(".map-capability"), bars: section.querySelectorAll(".map-job-fill"),
        request: section.querySelectorAll(".map-request-pulse"), response: section.querySelectorAll(".map-response-pulse"), noise: section.querySelectorAll(".map-noise"),
      }, setRuntimeState, value => { transitioning.current = value; setReplacing(value); }, () => syncMotion.current?.());
      const sync = () => {
        const running = visible && !document.hidden && (!inspecting.current || transitioning.current);
        section.dataset.motion = running ? "playing" : "paused";
        if (running) loop.play(); else loop.pause();
      };
      syncMotion.current = sync;
      const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); }, { threshold: 0 });
      observer.observe(section.querySelector(".architecture-map")!);
      document.addEventListener("visibilitychange", sync);
      return () => { observer.disconnect(); document.removeEventListener("visibilitychange", sync); syncMotion.current = null; };
    }, section);
    return () => {
      context.revert();
      gsap.set(section.querySelectorAll(".map-runtime-unit,.map-capability,.map-job-fill,.map-noise,.map-request-pulse,.map-response-pulse"), { clearProps: "all" });
      delete section.dataset.motion;
    };
  }, [reduced, paused]);

  const reveal = (button: HTMLButtonElement) => {
    layoutTarget.current = button;
    cancelAnimationFrame(revealFrame.current);
    // Let viewport reflow and browser scroll anchoring settle before aligning the card.
    revealFrame.current = requestAnimationFrame(() => {
      revealFrame.current = requestAnimationFrame(() => {
        if (!button.isConnected) return;
        const flow = button.closest<HTMLElement>(".map-flow-viewport");
        if (flow) {
          const bounds = flow.getBoundingClientRect(), target = button.getBoundingClientRect();
          flow.scrollTo({ left: flow.scrollLeft + target.left - bounds.left - (flow.clientWidth - target.width) / 2, behavior: "instant" });
        }
        const panelHeight = root.current?.querySelector(".map-detail")?.getBoundingClientRect().height ?? 0;
        const card = button.getBoundingClientRect();
        const available = window.innerHeight - panelHeight - 12 - 84;
        window.scrollTo({ top: window.scrollY + card.top - 84 - Math.max(0, (available - card.height) / 2), behavior: "instant" });
      });
    });
  };
  syncReveal.current = () => { if (layoutTarget.current?.isConnected) reveal(layoutTarget.current); };
  const interaction = (key: Feature, className = "") => ({
    type: "button" as const,
    "aria-pressed": selected === key,
    "aria-controls": "architecture-detail",
    "data-feature": key,
    className: `map-hotspot ${className}${active === key ? " is-active" : ""}`,
    onMouseEnter: () => setHovered(key), onMouseLeave: () => setHovered(null),
    onFocus: (event: FocusEvent<HTMLButtonElement>) => { setFocused(key); if (event.currentTarget.matches(":focus-visible")) reveal(event.currentTarget); },
    onBlur: () => setFocused(null),
    onClick: (event: MouseEvent<HTMLButtonElement>) => { setSelected(selected === key ? null : key); if (selected !== key) reveal(event.currentTarget); },
  });

  return <section id="architecture" ref={root} className="chapter architecture" aria-labelledby="architecture-title"
    onKeyDown={event => { if (event.key === "Escape") { setSelected(null); setHovered(null); setFocused(null); } }}>
    <div className="wrap">
      <div className="feature-heading architecture-heading">
        <div><span className="map-eyebrow">One connection. A complete tool environment.</span><h2 id="architecture-title">Your agent, equipped.<br/>Your evidence, retained.</h2></div>
        <p>Hercules connects your agent to a session-owned Kali runtime. Run selected tools and browser checks, get useful results back, and keep evidence in a workspace on your host.</p>
      </div>
      <div className="capability-scene" data-active={active ?? "overview"} data-inspecting={selected || focused ? "true" : undefined}>
        <div className="map-caption"><span>Follow a request from your agent to Kali—and back.</span><span><Info size={15} aria-hidden="true"/> Select a part to explore</span></div>
        <p className="map-pan-hint">Follow the connection → <span>Swipe horizontally or focus the diagram and use the arrow keys.</span></p>
        <div className="map-flow-viewport" role="region" aria-label="Horizontal Hercules connection diagram" tabIndex={0}>
        <div className="architecture-map">
          <span className="map-request-label">Request</span><span className="map-tools-label">Run tools</span>
          <span className="map-response-label">Results return to your agent.</span>
          <span className="map-mount-label" style={{ left: routes.mountLabel.x, top: routes.mountLabel.y }}>Workspace mount</span>
          <svg className="map-connections" aria-hidden="true"><defs><marker id="map-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M1 1L7 4L1 7" fill="none" stroke="currentColor" strokeWidth="1.3"/></marker></defs>
            {(["request", "response", "mount"] as const).map(key => <g key={key}>{routes[key].split(/(?=M)/).filter(Boolean).map((segment, index) => <path key={index} className={`map-route map-route-${key}`} d={segment} markerEnd={key === "mount" ? undefined : "url(#map-arrow)"}/>)}{key !== "mount" && <path className={`map-${key}-pulse`} d={routes[key]} pathLength="1"/>}</g>)}
            {routes.arrows.map((point, index) => <path key={index} className="map-flow-arrow" d={`M${point.x + 5},${point.y} H${point.x - 5}`} markerEnd="url(#map-arrow)"/>)}
          </svg>
          <div className="map-agent"><div className="map-node-head"><i className="map-port map-agent-port" aria-hidden="true"/><TerminalWindow size={26} aria-hidden="true"/><span><strong>Your agent</strong><small>STDIO MCP client</small></span></div><div className="map-agent-brands">{([["Claude Code", "claude.svg"], ["Cursor", "cursor.svg"], ["Codex", "codex.png"], ["Hermes", "hermes.png"]] as const).map(([name, file]) => <span key={name}><img src={asset(`brands/${file}`)} width="20" height="20" alt=""/>{name}</span>)}</div><p className="map-agent-note">Other STDIO clients supported</p><i className="map-port map-agent-return" aria-hidden="true"/></div>
          <button {...interaction("hercules", "map-hub")} aria-label="Explore Hercules routing"><span className="map-node-head"><img src={asset("lion.png")} width="44" height="50" alt=""/><span><strong>Hercules</strong><small>Host MCP server</small></span><Info size={14} aria-hidden="true"/><i className="map-port map-hub-input" aria-hidden="true"/><i className="map-port map-hub-dispatch" aria-hidden="true"/></span><span className="map-node-copy">Routes calls and manages execution on your computer.</span></button>
          <div className="map-runtime-stage"><i className="map-port map-docker-return" aria-hidden="true"/><i className="map-port map-mount-port" aria-hidden="true"/>
            <div className="map-runtime-status" aria-hidden="true"><span>Current session</span><strong>{runtimeLabels[reduced || paused ? "ready" : runtimeState]}</strong></div>
            <div className="map-runtime-backplate" aria-hidden="true"/>
            <div className="map-runtime-unit" inert={replacing} data-stage={reduced || paused ? "ready" : runtimeState}>
              <button {...interaction("docker", "map-runtime-header")} aria-label="Explore Docker sandboxing"><i className="map-port map-docker-port" aria-hidden="true"/><img src={asset("brands/docker.svg")} width="45" height="37" alt=""/><span><strong>Kali in Docker</strong><small>Started on request · session-owned</small></span><Info size={16} aria-hidden="true"/></button>

              <div className="map-capabilities">{capabilities.map(({ key, title }) => <button key={key} {...interaction(key, `map-capability map-capability-${key}`)} aria-label={`Explore ${title}`}><span className="map-tool-symbol" aria-hidden="true"><svg viewBox="0 0 72 60">{illustrations[key]}</svg></span><strong>{title}</strong><Info className="map-capability-info" size={13} aria-hidden="true"/></button>)}</div>
              <p className="map-tool-preview" aria-live="polite">{capabilities.find(item => item.key === active)?.tools ?? "Select a capability to see its tools."}</p>

              <button {...interaction("parallel", "map-parallel")} aria-label="Explore parallel tool execution"><span className="map-feature-title"><strong>Example job progress</strong><Info size={14} aria-hidden="true"/></span><span className="map-job-lanes">{["Service scan", "Browser check", "File analysis"].map(label => <span key={label}><span>{label}</span><i><b className="map-job-fill"/></i></span>)}</span><small>Illustrated concurrent work</small></button>
            </div>
          </div>
          <button {...interaction("filter", "map-filter")} aria-label="Explore token-saving output filters"><i className="map-port map-filter-input" aria-hidden="true"/><i className="map-port map-filter-output" aria-hidden="true"/><span className="map-feature-title"><FunnelSimple size={22} aria-hidden="true"/><strong>Output filtering</strong><Info size={14} aria-hidden="true"/></span><span className="map-filter-direction">Part of Hercules · on the return path</span><span className="map-output-lines"><span className="map-noise">Progress · banners · routine noise</span><span><Check size={14} aria-hidden="true"/>Findings kept</span><span><Info size={14} aria-hidden="true"/>Important diagnostics kept</span></span></button>
          <button {...interaction("workspaces", "map-workspaces")} aria-label="Explore managed workspaces"><span className="map-feature-title"><FolderOpen size={22} aria-hidden="true"/><span><strong>Managed workspaces</strong><small>Evidence stays on your host</small></span><Info size={14} aria-hidden="true"/></span><span className="map-workspace-pair"><span className="map-previous-workspace"><FolderOpen size={22} aria-hidden="true"/><span>Previous session<small>Retained · available to inspect</small></span></span><span className="map-current-workspace"><i className="map-port map-workspace-port" aria-hidden="true"/><FolderOpen size={22} aria-hidden="true"/><span>Current session<small>Active · mounted in this runtime</small></span></span></span><small>Each connection has its own active workspace; earlier sessions remain inspectable.</small></button>
        </div>
        </div>

        <div id="architecture-detail" className="map-detail" role="region" aria-label="Architecture explanation" tabIndex={0} aria-live="polite" aria-atomic="true"><h3>{current?.title ?? "From request to retained evidence."}</h3><p>{current?.text ?? "Your agent requests a tool. Hercules runs it in the selected Kali runtime, filters routine output, and returns results while evidence stays in your host workspace."}</p>{selected && <button type="button" aria-label="Clear selected explanation" onClick={() => { root.current?.querySelector<HTMLButtonElement>(`[data-feature="${selected}"]`)?.focus(); setSelected(null); setHovered(null); setFocused(null); }}><X size={18}/></button>}</div>
      </div>
      <p className="sr-only">The illustrative cycle shows a request, concurrent jobs, filtered results, and an explicit new session stopping the current runtime before a fresh runtime starts.</p>
    </div>
  </section>;
}
export default ArchitectureScene;
