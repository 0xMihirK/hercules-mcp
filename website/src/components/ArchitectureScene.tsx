import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowRight, Cube, Desktop, FolderOpen, PlugsConnected } from "@phosphor-icons/react";
gsap.registerPlugin(ScrollTrigger);
const phases = [
  { title: "Connect your agent.", text: "STDIO exposes Hercules’s tools and resources. Connecting alone does not start Kali.", code: "agent → host MCP server" },
  { title: "Start work explicitly.", text: "system_start_container starts the client’s owned runtime. The selected capability catalog determines its tools and verified image.", code: "system_start_container()" },
  { title: "Keep clients apart.", text: "Each client owns its session, workspace and allocated host ports. A second client gets a separate runtime rather than inheriting the first client’s process.", code: "client A → runtime A\nclient B → runtime B" },
  { title: "Keep the evidence.", text: "Tools write into the mounted workspace. Reports, diagnostics and artifacts survive an intentional stop; cleanup targets the exact owned container.", code: "system_stop_container()\nworkspace evidence stays" },
];

export default function ArchitectureScene({ reduced, paused }: { reduced: boolean; paused: boolean }) {
  const root = useRef<HTMLElement>(null), [phase, setPhase] = useState(0);
  useEffect(() => {
    if (reduced || paused || !root.current) return;
    const media = gsap.matchMedia();
    media.add("(min-width: 1000px) and (min-height: 900px)", () => {
      const timeline = gsap.timeline({ scrollTrigger: { trigger: root.current?.querySelector(".architecture-scene"), start: "top 64px", end: "+=180%", pin: true, scrub: .7, anticipatePin: 1, onUpdate: self => setPhase(Math.min(3, Math.floor(self.progress * 4))) } });
      timeline.fromTo(".architecture-path", { strokeDashoffset: 600 }, { strokeDashoffset: 0, duration: 4, ease: "none" });
      timeline.to(".runtime-illustration", { y: -18, rotation: -2, duration: 2, ease: "none" }, 1);
      return () => timeline.kill();
    }, root);
    return () => media.revert();
  }, [reduced, paused]);
  return <section id="architecture" ref={root} className="architecture chapter">
    <div className="wrap"><div className="chapter-heading"><h2>One connection.<br />An owned workspace.</h2><p>The agent speaks MCP. Hercules manages the runtime. Docker contains the tools. Your workspace retains what happened.</p></div>
      <div className="architecture-scene">
        <div className="architecture-nodes" aria-label="Hercules architecture">
          <div className="architecture-node"><Desktop size={30} aria-hidden="true" /><h3>Your agent</h3><p>Windows · macOS · Linux<br />Worker or custom integration</p></div><ArrowRight className="node-arrow" size={24} aria-hidden="true" />
          <div className="architecture-node"><PlugsConnected size={30} aria-hidden="true" /><h3>Host MCP server</h3><p>STDIO transport<br />Explicit lifecycle + ownership</p></div><ArrowRight className="node-arrow" size={24} aria-hidden="true" />
          <div className="architecture-node runtime-node"><Cube size={30} aria-hidden="true" /><h3>Kali in Docker</h3><p>Client-owned runtime<br />Selected capabilities</p></div><ArrowRight className="node-arrow" size={24} aria-hidden="true" />
          <div className="architecture-node"><FolderOpen size={30} aria-hidden="true" /><h3>Workspace</h3><p>Raw diagnostics + findings<br />Files + verified reports</p></div>
          <svg viewBox="0 0 1000 10" className="architecture-line" aria-hidden="true"><path className="architecture-path" d="M0 5H1000" stroke="currentColor" strokeWidth="2" fill="none" strokeDasharray="600" /></svg>
        </div>
        <div className="architecture-detail"><div className="architecture-visual"><img className="runtime-illustration" src={`${import.meta.env.BASE_URL}assets/illustrations/container-cutaway.png`} width="1536" height="1024" alt="Illustration of a graphite enclosure with copper boundaries representing a contained runtime." loading="lazy" decoding="async" /><span>Illustration · runtime containment</span></div>
          <div className="architecture-story"><div className="phase-buttons" aria-label="Architecture stages">{phases.map((item,i) => <button key={item.title} aria-pressed={phase === i} onClick={() => setPhase(i)}>{item.title}</button>)}</div><h3>{phases[phase].title}</h3><p>{phases[phase].text}</p><pre>{phases[phase].code}</pre></div>
        </div>
      </div>
      <div className="ownership-ledger" aria-label="Separate runtime ownership"><div><strong>Client A</strong><span>Container A</span><span>Workspace A</span><span>Allocated port set A</span></div><div><strong>Client B</strong><span>Container B</span><span>Workspace B</span><span>Allocated port set B</span></div><p>Ownership diagram · ports are checked at startup and reallocated when a configured set is occupied.</p></div>
      <div className="containment-note"><strong>Isolation you control.</strong><p>Docker containment depends on the operator’s networking and privileges. Hercules supports configured networks and scoped targets; containers are not a complete security boundary. These demonstrations use an internal lab network and no public targets.</p></div>
      <div className="architecture-static">{phases.map(item => <div key={item.title}><h3>{item.title}</h3><p>{item.text}</p></div>)}</div>
    </div>
  </section>;
}
