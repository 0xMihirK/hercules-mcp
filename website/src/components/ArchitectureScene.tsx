import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowDown, ArrowUpRight, AppleLogo, WindowsLogo, LinuxLogo, OpenAiLogo, TerminalWindow, PlugsConnected, Network, GlobeHemisphereWest, FileArchive, Code } from "@phosphor-icons/react";
gsap.registerPlugin(ScrollTrigger);
const asset=(path:string)=>import.meta.env.BASE_URL+"assets/"+path;
const phases=[
  {label:"Connection",title:"Connect your agent.",text:"Connecting makes Hercules tools available to your agent. The Docker container starts only when requested."},
  {label:"Startup",title:"Start the tools when needed.",text:"Your session starts a Kali container in Docker. The selected security tools run inside it."},
  {label:"Separate sessions",title:"Keep sessions separate.",text:"Each Hercules session manages its own container, working files, and allocated ports."},
  {label:"Stop",title:"Stop your session’s container.",text:"Hercules stops the container owned by this session. Other sessions keep their containers."}
];
export default function ArchitectureScene({reduced,paused}:{reduced:boolean;paused:boolean}){
  const root=useRef<HTMLElement>(null),[phase,setPhase]=useState(0),phaseRef=useRef(phase);phaseRef.current=phase;
  useEffect(()=>{
    if(reduced || paused || !root.current)return;
    const media=gsap.matchMedia();
    media.add("(min-width: 1024px) and (min-height: 700px)",()=>{
      const trigger=ScrollTrigger.create({trigger:root.current!.querySelector(".sandbox-scene"),start:"top top",end:"+=110%",pin:true,scrub:.6,invalidateOnRefresh:true,onUpdate:self=>{const next=Math.min(3,Math.floor(self.progress*4));if(next!==phaseRef.current){phaseRef.current=next;setPhase(next);}}});
      return()=>trigger.kill();
    });
    const entry=gsap.context(()=>gsap.from(".portable-brand",{y:16,duration:.65,stagger:.1,ease:"power3.out",scrollTrigger:{trigger:".portability",start:"top 85%",once:true}}),root);
    return()=>{entry.revert();media.revert();};
  },[reduced,paused]);
  useEffect(()=>{
    if(reduced || paused || !root.current)return;
    const context=gsap.context(()=>{
      gsap.fromTo(".request-path",{strokeDashoffset:180},{strokeDashoffset:0,duration:.85,ease:"power2.out"});
      gsap.fromTo(".lifecycle-caption",{y:10},{y:0,duration:.45,ease:"power2.out"});
      gsap.fromTo(phase>=2?".runtime-b":".runtime-a",{y:8},{y:0,duration:.6,ease:"power3.out"});
    },root);
    return()=>context.revert();
  },[phase,reduced,paused]);
  return <section id="architecture" ref={root} className="architecture chapter">
    <div className="wrap"><div className="feature-heading"><h2>Your agent.<br/>Its own tool workspace.</h2><p>Hercules connects your agent to security tools in a Docker container, a separate software environment. Each session manages its own container.</p></div>
      <div className={"sandbox-scene lifecycle-"+phase}>
        <div className="lifecycle-header"><span>Illustrated lifecycle</span><div className="lifecycle-controls" role="group" aria-label="Explore the Hercules lifecycle">{phases.map((item,i)=><button key={item.label} aria-pressed={phase===i} onClick={()=>setPhase(i)}>{item.label}</button>)}</div></div>
        <div className="architecture-flow" role="group" aria-label="Agents connect to Hercules on the host; security tools execute in separately owned Docker runtimes">
          <div className="diagram-agents"><div className="diagram-agent"><TerminalWindow size={35}/><div><h3>Your agent</h3><p>Session A</p></div></div><div className="agent-question">“Review the local website.”</div><div className="diagram-agent agent-b"><PlugsConnected size={31}/><div><h3>Another agent</h3><p>Session B</p></div></div><p className="diagram-detail">Any compatible agent, worker,<br/>or custom integration.</p></div>
          <div className="diagram-hercules"><img src={asset("lion.svg")} width="85" height="90" alt="Hercules"/><h3>Hercules MCP</h3><p>Runs on your computer.<br/>Connects your agent to the tools.</p><div className="server-lanes"><span>Session A</span><span>Session B</span></div></div>
          <div className="diagram-runtimes"><div className={"runtime-card runtime-a"+(phase===1 || phase===2?" runtime-active":"")}><div className="runtime-title"><img src={asset("brands/docker.svg")} width="37" height="37" alt="Docker"/><div><h3>Kali workspace</h3><span>Managed by session A</span></div></div><div className="runtime-tools"><span><Network size={23}/>Network tools</span><span><GlobeHemisphereWest size={23}/>Web tools</span><span><FileArchive size={23}/>Forensics</span><span><Code size={23}/>Shell + browser</span></div><p className="runtime-state">{phase===0?"Starts only when requested":phase===3?"This session’s container is stopped":"Tools run inside this container"}</p></div>
          <div className={"runtime-card runtime-b"+(phase>=2?" runtime-active":"")}><div className="runtime-title"><img src={asset("brands/docker.svg")} width="29" height="29" alt=""/><div><h3>Separate workspace</h3><span>Managed by session B</span></div></div><p>{phase>=2?"Separate container, files, and ports.":"Each session controls its own container."}</p></div></div>
          <svg className="diagram-connections" viewBox="0 0 1000 420" preserveAspectRatio="none" aria-hidden="true"><path className="request-path" d="M210 110H390M210 310H390M560 110H700M560 310H700" stroke="currentColor" strokeWidth="2" fill="none" strokeDasharray="180"/></svg><ArrowDown className="mobile-diagram-arrow" size={22} aria-hidden="true"/>
        </div>
        <div className="lifecycle-caption"><h3>{phases[phase].title}</h3><p>{phases[phase].text}</p></div>
      </div>
      <p className="sandbox-note">You control network access, permissions, and target scope. Container isolation depends on those settings.</p>
      <div className="portability"><div><h2>Use the agent<br/>you already work with.</h2><p>MCP (Model Context Protocol) lets agents call Hercules tools. Use a local STDIO connection on Windows, macOS, or Linux with Docker.</p><a className="text-link" href="https://github.com/0xMihirK/hercules-mcp#install-with-your-ai-agent">See compatible setup options <ArrowUpRight size={18}/></a></div><div className="portable-platforms"><div className="portable-os"><div className="portable-brand"><WindowsLogo size={42} weight="fill"/><span>Windows</span></div><div className="portable-brand"><AppleLogo size={42} weight="fill"/><span>macOS</span></div><div className="portable-brand"><LinuxLogo size={42} weight="fill"/><span>Linux</span></div></div><div className="portable-bridge"><img src={asset("lion.svg")} width="50" height="50" alt="Hercules"/><span>The same MCP interface</span></div><div className="portable-agents"><div className="portable-brand"><OpenAiLogo size={31}/><span>Codex</span></div><div className="portable-brand"><TerminalWindow size={31}/><span>Your agent</span></div><div className="portable-brand"><PlugsConnected size={31}/><span>Custom integrations</span></div></div><p>Other STDIO MCP clients can connect too.</p></div></div>
    </div>
  </section>;
}
