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
  browser: { title: "Control a real browser.", text: "The optional CloakBrowser runtime supports navigation, snapshots, clicks, form filling, screenshots, and browser sessions. It reduces common automation signals without guaranteeing CAPTCHA or bot-detection avoidance." },
  network: { title: "From a target to a service map.", text: "Use Amass and DNS tools to discover hosts, then Nmap to inspect reachable services. The agent can follow up with curl or Ncat to check what a service actually returns." },
  web: { title: "Discover, then verify web issues.", text: "Use ffuf for endpoint discovery, Nuclei for template-based checks, and SQLMap for database injection testing. Browser checks can help the agent verify a result instead of treating every scanner alert as a finding." },
  files: { title: "Follow clues inside files.", text: "Binwalk, ExifTool, and Steghide help examine embedded data, metadata, and hidden content. Shell and workspace tools let the agent inspect extracted files and continue an investigation." },
  research: { title: "Research and test applicability.", text: "SearchSploit searches exploit references; the optional Metasploit bundle supports module search and managed execution. These are operator-scoped capabilities, not an automatic claim that a service is exploitable." },
  passwords: { title: "Test credentials in an authorized lab.", text: "Hydra supports online authentication checks, while John the Ripper works with password hashes. The agent can combine these with shell tools and files in the active workspace." },
  parallel: { title: "Independent work can overlap.", text: "Hercules supports concurrent calls within configured limits and background jobs with partial output. A service scan can keep running while the agent inspects a page or examines a file." },
  workspaces: { title: "Fresh runtime. Separate investigation.", text: "Creating a fresh session stops the connection’s current runtime and creates a new workspace; prior workspaces remain inspectable. Separate client connections can own independent runtimes and workspaces." },
  filter: { title: "Keep useful output in the conversation.", text: "Within Hercules, tool-specific filters remove known routine chatter while preserving characterized findings and diagnostics. Separate response-size limits can shorten large results, with raw-output availability disclosed." },
};
type Feature = keyof typeof details;
const capabilities = [
  { key: "browser", title: "Browser control", tools: "CloakBrowser" },
  { key: "network", title: "Recon & services", tools: "Amass · DNS · Nmap" },
  { key: "web", title: "Web assessment", tools: "ffuf · Nuclei · SQLMap" },
  { key: "files", title: "Files & forensics", tools: "Binwalk · ExifTool · Steghide" },
  { key: "research", title: "Exploit research", tools: "SearchSploit · Metasploit" },
  { key: "passwords", title: "Credential testing", tools: "Hydra · John the Ripper" },
] as const;

// Small software vignettes describe capabilities, not captured interfaces or findings.
const illustrations = {
  browser: <><rect x="2" y="4" width="66" height="49" rx="2"/><path d="M2 15H68M9 10H11M16 10H18M23 10H25M10 23H33M10 30H47M10 37H37"/><rect className="map-mini-field" x="43" y="40" width="17" height="7"/><path className="map-mini-cursor" d="M53 32L53 44L57 40L62 40Z"/></>,
  network: <><rect x="2" y="23" width="20" height="16"/><path d="M22 31H34V10H49M34 31H49M34 31V52H49M7 28H16M7 33H13"/><rect x="49" y="3" width="20" height="14"/><rect x="49" y="24" width="20" height="14"/><rect x="49" y="45" width="20" height="14"/><path className="map-mini-node" d="M55 10H63"/><path className="map-mini-node" d="M55 31H63"/><path className="map-mini-node" d="M55 52H63"/></>,
  web: <><rect x="3" y="5" width="48" height="48"/><path d="M3 15H51M10 10H12M17 10H19M10 24H37M10 33H31M10 42H27"/><circle className="map-mini-accent" cx="48" cy="36" r="13"/><path className="map-mini-accent" d="M58 46L68 56M43 36L47 40L54 32"/></>,
  files: <><path d="M4 17V7H40L51 18V29M40 7V18H51M10 14H31M10 21H30"/><path d="M13 32V25H40L47 32H66V54H13Z"/><path className="map-mini-accent" d="M24 47L29 42L24 37M36 37H53M36 43H57M36 49H49"/><path d="M4 32V51H8"/></>,
  research: <><path d="M4 8H28V43H4ZM10 16H22M10 22H19M10 28H22M10 35H16M12 48H34V14"/><path d="M38 29H47M44 25L48 29L44 33"/><rect className="map-mini-accent" x="51" y="16" width="17" height="29"/><path className="map-mini-accent" d="M56 24L63 30L56 36Z"/></>,
  passwords: <><rect x="3" y="7" width="40" height="43"/><path d="M3 17H43M10 12H12M17 12H19M10 27H34M10 37H12M17 37H19M24 37H26M31 37H33"/><circle className="map-mini-accent" cx="53" cy="38" r="9"/><path className="map-mini-accent" d="M53 29V15H63M59 15V21M53 21H59"/></>,
};
const runtimeLabels = { ready: "Ready for a new task", working: "Independent checks running", complete: "Checks complete", stopping: "Stopping current runtime", starting: "Starting fresh runtime" };
type RuntimeState = keyof typeof runtimeLabels;

export function ArchitectureScene({ reduced, paused }: { reduced: boolean; paused: boolean }) {
  const root = useRef<HTMLElement>(null);
  const revealFrame = useRef(0);
  useEffect(() => () => cancelAnimationFrame(revealFrame.current), []);
  const inspecting = useRef(false);
  const transitioning = useRef(false);
  const syncMotion = useRef<(() => void) | null>(null);
  const [hovered, setHovered] = useState<Feature | null>(null);
  const [focused, setFocused] = useState<Feature | null>(null);
  const [selected, setSelected] = useState<Feature | null>(null);
  const [phase, setPhase] = useState("Start on request");
  const [runtimeState, setRuntimeState] = useState<RuntimeState>("ready");
  const [replacing, setReplacing] = useState(false);
  const [routes, setRoutes] = useState({ request: "", response: "", mount: "" });
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
      const agent = point(".map-agent-port"), hub = point(".map-hub-input"), dispatch = point(".map-hub-dispatch"), docker = point(".map-docker-port");
      const agentReturn = point(".map-agent-return"), filter = point(".map-filter-output"), filterInput = point(".map-filter-input"), hubReturn = point(".map-hub-return"), hubOutput = point(".map-hub-output"), result = point(".map-docker-return");
      const mount = point(".map-mount-port"), workspace = point(".map-workspace-port");
      const requestY = 28, responseY = result.y + 32;
      setRoutes({
        request: `M${agent.x},${agent.y} V${requestY} H${hub.x} V${hub.y} M${dispatch.x},${dispatch.y} V${requestY} H${docker.x} V${docker.y}`,
        response: `M${result.x},${result.y} V${responseY} H${hubReturn.x} V${hubReturn.y} M${hubOutput.x},${hubOutput.y} V${responseY} H${filterInput.x} V${filterInput.y} M${filter.x},${filter.y} V${responseY} H${agentReturn.x} V${agentReturn.y}`,
        mount: `M${mount.x},${mount.y} V${workspace.y - 16} H${workspace.x} V${workspace.y}`,
      });
    };
    const observer = new ResizeObserver(measure);
    observer.observe(map);
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
      const loop = gsap.timeline({ paused: true, repeat: -1 });
      loop.call(() => { setPhase("Agent dispatches independent checks"); setRuntimeState("working"); }, [], 0)
        .fromTo(".map-request-pulse", { strokeDashoffset: 1, opacity: 0 }, { strokeDashoffset: 0, opacity: 1, duration: 1 }, .3)
        .to(".map-request-pulse", { opacity: 0, duration: .3 }, 1.4)
        .fromTo(".map-agent-cursor", { opacity: .2 }, { opacity: 1, duration: .45, repeat: 7, yoyo: true }, .3)
        .fromTo(".map-mini-cursor", { x: -8, y: -6, opacity: .3 }, { x: 0, y: 0, opacity: 1, duration: 1.2, ease: "power2.out" }, 1.5)
        .fromTo(".map-mini-node", { opacity: .25 }, { opacity: 1, duration: .5, stagger: .4 }, 2)
        .fromTo(".map-job-fill", { scaleX: .08 }, { scaleX: 1, duration: 3.5, stagger: .55, ease: "power1.inOut" }, 1.4)
        .call(() => { setPhase("Findings and diagnostics return"); setRuntimeState("complete"); }, [], 6.6)
        .fromTo(".map-response-pulse", { strokeDashoffset: 1, opacity: 0 }, { strokeDashoffset: 0, opacity: 1, duration: 1.2 }, 6.6)
        .to(".map-response-pulse", { opacity: 0, duration: .3 }, 8)
        .fromTo(".map-noise", { opacity: .75, x: 0 }, { opacity: .15, x: -8, duration: .6, stagger: .15 }, 7)
        .fromTo(".map-retained-output", { opacity: .65 }, { opacity: 1, duration: .5, stagger: .2 }, 7.5)
        .call(() => { setPhase("Fresh session requested · stopping current runtime"); setRuntimeState("stopping"); }, [], 10)
        .call(() => { transitioning.current = true; setReplacing(true); }, [], 10.5)
        .to(".map-runtime-unit", { y: -35, opacity: 0, scale: .96, duration: .65, ease: "power2.in" }, 10.5)
        .call(() => { setRuntimeState("starting"); setPhase("Previous workspace retained · starting fresh runtime"); }, [], 11.3)
        .set(".map-job-fill", { scaleX: .08 }, 11.3)
        .set(".map-runtime-unit", { y: 40, scale: .96 }, 11.3)
        .to(".map-runtime-unit", { y: 0, opacity: 1, scale: 1, duration: .85, ease: "power2.out" }, 11.7)
        .call(() => { transitioning.current = false; setReplacing(false); setRuntimeState("ready"); setPhase("Fresh runtime ready · previous workspace retained"); syncMotion.current?.(); }, [], 12.6)
        .to({}, { duration: 2 }, 13);
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
      gsap.set(section.querySelectorAll(".map-runtime-unit,.map-mini-cursor,.map-mini-node,.map-agent-cursor,.map-job-fill,.map-noise,.map-retained-output,.map-request-pulse,.map-response-pulse"), { clearProps: "all" });
      delete section.dataset.motion;
    };
  }, [reduced, paused]);

  const reveal = (button: HTMLButtonElement) => {
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
        <div><span className="map-eyebrow">One connection. A complete tool environment.</span><h2 id="architecture-title">Powerful tools.<br/>A separate workspace.</h2></div>
        <p>Your agent coordinates the investigation. Hercules brings browser control and Kali tools together in Docker, manages their workspaces, and filters the output returned to your agent.</p>
      </div>
      <div className="capability-scene" data-active={active ?? "overview"} data-inspecting={selected || focused ? "true" : undefined}>
        <div className="map-caption"><span>Requests go out. Useful results come back.</span><span><Info size={15} aria-hidden="true"/> Select a part to explore</span></div>
        <p className="map-pan-hint">Follow the connection → <span>Swipe horizontally or focus the diagram and use the arrow keys.</span></p>
        <div className="map-flow-viewport" role="region" aria-label="Horizontal Hercules connection diagram" tabIndex={0}>
        <div className="architecture-map">
          <div className="map-request-label">Request → <span>STDIO MCP</span></div>
          <div className="map-response-label">← Results return through the noise filter</div>
          <svg className="map-connections" aria-hidden="true"><defs><marker id="map-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M1 1L7 4L1 7" fill="none" stroke="currentColor" strokeWidth="1.3"/></marker></defs>
            {Object.entries(routes).map(([key, d]) => <g key={key}>{d.split(/(?=M)/).filter(Boolean).map((segment, index) => <path key={index} className={`map-route map-route-${key}`} d={segment} markerEnd={key === "mount" ? undefined : "url(#map-arrow)"}/>)}{key !== "mount" && <path className={`map-${key}-pulse`} d={d} pathLength="1"/>}</g>)}
          </svg>
            <div className="map-agent"><i className="map-port map-agent-port" aria-hidden="true"/><i className="map-port map-agent-return" aria-hidden="true"/><TerminalWindow size={25} aria-hidden="true"/><div><strong>Your agent</strong><small>Any STDIO MCP client</small></div><span className="map-agent-task">“Investigate this local lab.”<i className="map-agent-cursor" aria-hidden="true"/></span></div>
            <button {...interaction("filter", "map-filter")} aria-label="Explore token-saving output filters"><span className="map-feature-title"><FunnelSimple size={22} aria-hidden="true"/><strong>Token-saving filter</strong><Info size={14} aria-hidden="true"/></span><span className="map-port map-filter-input" aria-hidden="true"/><span className="map-port map-filter-output" aria-hidden="true"/>
              <span className="map-filter-direction">On the return path</span><span className="map-output-lines"><span className="map-noise">Progress · banners · routine noise</span><span className="map-retained-output"><Check size={14} aria-hidden="true"/>Findings kept</span><span className="map-retained-output">! Important diagnostics kept</span></span><small>Removes routine noise. Large responses have separate size limits.</small>
            </button>
            <button {...interaction("hercules", "map-hub")} aria-label="Explore Hercules routing"><img src={asset("lion.svg")} width="47" height="54" alt=""/><span><strong>Hercules</strong><small>Host MCP server<br/>Routes calls, manages execution, and returns results.</small></span><Info size={15} aria-hidden="true"/><i className="map-port map-hub-input" aria-hidden="true"/><i className="map-port map-hub-dispatch" aria-hidden="true"/><i className="map-port map-hub-return" aria-hidden="true"/><i className="map-port map-hub-output" aria-hidden="true"/></button>
          <div className="map-runtime-stage"><i className="map-port map-docker-port" aria-hidden="true"/><i className="map-port map-docker-return" aria-hidden="true"/><i className="map-port map-mount-port" aria-hidden="true"/>
            <div className="map-runtime-backplate" aria-hidden="true"/>
            <div className="map-runtime-unit" inert={replacing} data-stage={reduced || paused ? "ready" : runtimeState}>
              <button {...interaction("docker", "map-runtime-header")} aria-label="Explore Docker sandboxing"><img src={asset("brands/docker.svg")} width="45" height="37" alt=""/><span><strong>Kali in Docker</strong><small>Started on request · session-owned</small></span><Info size={16} aria-hidden="true"/></button>
              <div className="map-runtime-state" aria-hidden="true" title={reduced || paused ? "Start on request → run tools → fresh session" : phase}><span>Current session</span><strong>{reduced || paused ? "Starts on request" : runtimeLabels[runtimeState]}</strong></div>
              <div className="map-capabilities">{capabilities.map(({ key, title }) => <button key={key} {...interaction(key, `map-capability map-capability-${key}`)} aria-label={`Explore ${title}`}><span className="map-tool-symbol" aria-hidden="true"><svg viewBox="0 0 72 60">{illustrations[key]}</svg></span><strong>{title}</strong><Info className="map-capability-info" size={13} aria-hidden="true"/></button>)}</div>
              <p className="map-tool-preview" aria-live="polite">{capabilities.find(item => item.key === active)?.tools ?? "Select a capability to see its tools."}</p>

              <button {...interaction("parallel", "map-parallel")} aria-label="Explore parallel tool execution"><span className="map-feature-title"><strong>Work in parallel</strong><Info size={14} aria-hidden="true"/></span><span className="map-job-lanes">{["Service scan", "Browser check", "File analysis"].map(label => <span key={label}><span>{label}</span><i><b className="map-job-fill"/></i></span>)}</span><small>Concurrent checks · inspect background output</small></button>
            </div>
          </div>
          <button {...interaction("workspaces", "map-workspaces")} aria-label="Explore managed workspaces"><i className="map-port map-workspace-port" aria-hidden="true"/><span className="map-feature-title"><FolderOpen size={22} aria-hidden="true"/><span><strong>Managed workspaces</strong><small>Stored on your host</small></span><Info size={14} aria-hidden="true"/></span><span className="map-workspace-pair"><span><FolderOpen size={20} aria-hidden="true"/><span>Previous session<small>Retained · available to inspect</small></span></span><span className="map-current-workspace"><FolderOpen size={20} aria-hidden="true"/><span>Current session<small>Active · mounted in this runtime</small></span></span></span><small>One active workspace per connection. Separate clients can own independent runtimes.</small></button>
        </div>
        </div>

        <div id="architecture-detail" className="map-detail" role="region" aria-label="Architecture explanation" tabIndex={0} aria-live="polite" aria-atomic="true"><h3>{current?.title ?? "Less noise in your agent’s context."}</h3><p>{current?.text ?? "Follow a request to the tools, then trace the response back through Hercules and its output filter. Select any outlined part for its role and capabilities."}</p>{selected && <button type="button" aria-label="Clear selected explanation" onClick={() => { root.current?.querySelector<HTMLButtonElement>(`[data-feature="${selected}"]`)?.focus(); setSelected(null); setHovered(null); setFocused(null); }}><X size={18}/></button>}</div>
      </div>
      <p className="map-scope">Tools start only when requested. You control networking, permissions, and target scope. Tool availability depends on your selected bundles.</p>
    </div>
  </section>;
}
export default ArchitectureScene;
