import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowRight } from "@phosphor-icons/react/ArrowRight";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { AppleLogo } from "@phosphor-icons/react/AppleLogo";
import { WindowsLogo } from "@phosphor-icons/react/WindowsLogo";
import { LinuxLogo } from "@phosphor-icons/react/LinuxLogo";
import { TerminalWindow } from "@phosphor-icons/react/TerminalWindow";
import { Network } from "@phosphor-icons/react/Network";
import { GlobeHemisphereWest } from "@phosphor-icons/react/GlobeHemisphereWest";
import { FileArchive } from "@phosphor-icons/react/FileArchive";
import { Code } from "@phosphor-icons/react/Code";
gsap.registerPlugin(ScrollTrigger);
const asset=(path:string)=>import.meta.env.BASE_URL+"assets/"+path;
const phases=[
  {label:"Connect",title:"Connected. Tools are not running yet.",text:"Your agent can see the Hercules tools. The Kali container stays stopped until the agent explicitly starts it."},
  {label:"Start tools",title:"Start a workspace when the work begins.",text:"Hercules starts your session’s Kali container. Security tools execute inside that software environment."},
  {label:"Separate sessions",title:"A separate container for each session.",text:"Another agent gets its own Hercules session, container, working files, and allocated ports."},
  {label:"Stop tools",title:"Stop your container. Other sessions continue.",text:"Hercules stops the container owned by this session. The other session keeps control of its own container."}
];
function Connection({label,docker=false}:{label:string;docker?:boolean}){return <div className={"flow-connection"+(docker?" docker-connection":"")} aria-hidden="true"><span>{label}</span><i><b className="connection-packet"/></i><ArrowRight size={18}/></div>;}
export default function ArchitectureScene({reduced,paused}:{reduced:boolean;paused:boolean}){
  const root=useRef<HTMLElement>(null),scene=useRef<HTMLDivElement>(null),[phase,setPhase]=useState(0);
  useEffect(()=>{
    if(reduced || paused || !root.current)return;
    const context=gsap.context(()=>{
      gsap.fromTo(".connection-packet",{xPercent:-100},{xPercent:520,duration:1.1,ease:"power2.out",scrollTrigger:{trigger:scene.current,start:"top 80%",once:true}});
      if(phase===1 || phase===2)gsap.fromTo(".runtime-capability",{clipPath:"inset(0 0 100% 0)",y:5},{clipPath:"inset(0 0 0% 0)",y:0,duration:.45,stagger:.06,ease:"power3.out"});
    },root);
    return()=>context.revert();
  },[phase,reduced,paused]);
  const running=phase===1 || phase===2;
  return <section id="architecture" ref={root} className="chapter architecture" aria-labelledby="architecture-title">
    <div className="wrap"><div className="feature-heading feature-heading--split"><h2 id="architecture-title">Kali in a container.<br/>A separate workspace.</h2><p>Hercules runs on your computer. Its security tools run in a session-owned Kali Docker container.</p></div>
      <div ref={scene} className={"sandbox-demonstration phase-"+phase}>
        <div className="sandbox-controls" role="group" aria-label="Explore the illustrated session lifecycle">{phases.map((item,i)=><button key={item.label} aria-pressed={phase===i} onClick={()=>setPhase(i)}>{item.label}</button>)}</div>
        <div className="software-flow" role="group" aria-label="Your agent connects to Hercules on your computer. Hercules manages a separate Kali Docker container containing the security tools.">
          <div className="agent-request"><TerminalWindow size={35} aria-hidden="true"/><h3>Your agent</h3><p>Claude, Codex, or your own integration.</p><blockquote>Review this website.</blockquote><span>You choose the task and scope.</span></div>
          <Connection label="STDIO MCP"/>
          <div className="hercules-bridge"><img src={asset("lion.svg")} width="82" height="90" alt=""/><h3>Hercules</h3><p>Connects your agent.<br/>Manages the runtime.</p><span>Runs on your computer</span></div>
          <Connection label="Starts on request" docker/>
          <div className={"tool-container"+(running?" is-running":"")}>
            <header><img src={asset("brands/docker.svg")} width="49" height="49" alt="Docker"/><div><h3>Kali Linux</h3><p>Docker container · session A</p></div></header>
            <div className="runtime-capabilities"><div className="runtime-capability"><Network size={24}/><span>Network<small>Hosts and services</small></span></div><div className="runtime-capability"><GlobeHemisphereWest size={24}/><span>Web<small>Requests and browsers</small></span></div><div className="runtime-capability"><FileArchive size={24}/><span>Forensics<small>Files and challenges</small></span></div><div className="runtime-capability"><Code size={24}/><span>Shell<small>Tools working together</small></span></div></div>
            <footer><span className="container-status">{running?"Running for session A":"Container stopped"}</span><span>Separate from your host tools</span></footer>
          </div>
        </div>
        <div className="second-session">{phase>=2?<div className="secondary-flow"><span><TerminalWindow size={20}/>Another agent</span><ArrowRight size={18} aria-hidden="true"/><span>Hercules session B</span><ArrowRight size={18} aria-hidden="true"/><span><img src={asset("brands/docker.svg")} width="25" height="25" alt=""/>Container B · running</span></div>:<p>Another session gets its own container, working files, and allocated ports.</p>}</div>
        <div className="sandbox-caption" aria-live="polite"><h3>{phases[phase].title}</h3><p>{phases[phase].text}</p></div>
      </div>
      <p className="sandbox-scope">You control networking, permissions, and target scope. Container isolation depends on those settings.</p>
      <div className="portability-band"><div><h3>Bring your agent.<br/>Choose your system.</h3><p>Any agent, worker, or custom integration with STDIO MCP support can connect. MCP means Model Context Protocol.</p><a className="text-link" href="https://github.com/0xMihirK/hercules-mcp#install-with-your-ai-agent">See setup options <ArrowUpRight size={18}/></a></div><div className="platform-line"><span><WindowsLogo size={38} weight="fill"/>Windows</span><span><AppleLogo size={38} weight="fill"/>macOS</span><span><LinuxLogo size={38} weight="fill"/>Linux</span><p>Same Hercules. Docker on each system.</p></div></div>
    </div>
  </section>;
}
