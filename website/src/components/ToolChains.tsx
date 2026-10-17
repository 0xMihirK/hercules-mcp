import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ArrowRight } from "@phosphor-icons/react/ArrowRight";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { Browser } from "@phosphor-icons/react/Browser";
import { Check } from "@phosphor-icons/react/Check";
import { Circle } from "@phosphor-icons/react/Circle";
import { FolderOpen } from "@phosphor-icons/react/FolderOpen";
import { HardDrives } from "@phosphor-icons/react/HardDrives";
import { Network } from "@phosphor-icons/react/Network";
import { Pulse } from "@phosphor-icons/react/Pulse";
import { TerminalWindow } from "@phosphor-icons/react/TerminalWindow";

const evidence=(path:string)=>import.meta.env.BASE_URL+"assets/recordings/evidence/"+path;
const demoAsset=(path:string)=>import.meta.env.BASE_URL+"assets/demos/"+path;

function useSectionMotion(root:React.RefObject<HTMLElement|null>, reduced:boolean){
  const [visible,setVisible]=useState(reduced);
  useEffect(()=>{
    if(reduced||!root.current){setVisible(true);return;}
    const observer=new IntersectionObserver(entries=>{
      if(entries.some(entry=>entry.isIntersecting)){setVisible(true);observer.disconnect();}
    },{threshold:.12});
    observer.observe(root.current);
    return()=>observer.disconnect();
  },[reduced,root]);
  useEffect(()=>{
    if(!visible||reduced||!root.current)return;
    const context=gsap.context(()=>{
      const timeline=gsap.timeline({defaults:{ease:"power3.out"}});
      timeline.fromTo(".demo-main",{y:24,clipPath:"inset(0 0 9% 0)"},{y:0,clipPath:"inset(0 0 0 0)",duration:.7})
        .fromTo(".demo-secondary",{y:18,opacity:.35},{y:0,opacity:1,duration:.55,stagger:.12},"-=.42")
        .fromTo(".demo-wire",{scaleX:0},{scaleX:1,duration:.5,stagger:.09,transformOrigin:"left center"},"-=.35");
    },root);
    return()=>context.revert();
  },[visible,reduced,root]);
  return visible;
}

function ReconVisual(){
  return <div className="demo-recon-map" role="img" aria-label="A scoped lab maps to three reachable services: an app, an HTTP proxy, and a TLS endpoint, followed by response and certificate checks">
    <div className="recon-origin"><Network size={24} aria-hidden="true"/><span>Scoped lab<br/>3 services</span></div>
    <div className="recon-branches" aria-hidden="true"><i className="demo-wire"/><i className="demo-wire"/><i className="demo-wire"/></div>
    <div className="recon-services">
      <div><span><Browser size={17} aria-hidden="true"/>8000 · Sign-in</span><small>health checked</small></div>
      <div><span><Network size={17} aria-hidden="true"/>8080 · Proxy</span><small>response checked</small></div>
      <div><span><Check size={17} aria-hidden="true"/>8443 · HTTPS</span><small>lab CA verified</small></div>
    </div>
  </div>;
}

function JobsVisual(){
  return <div className="demo-job-board" role="img" aria-label="One long-running background check keeps its partial output while the agent verifies another lead">
    <div className="job-board-heading"><span>Work keeps moving</span><span className="job-live"><i/>1 background check</span></div>
    <div className="job-lane"><span className="job-icon"><TerminalWindow size={19}/></span><div><strong>Long-running check</strong><small>Partial output stays available</small></div><div className="job-progress"><i className="demo-wire"/><b>resume</b></div></div>
    <div className="job-lane"><span className="job-icon"><Browser size={19}/></span><div><strong>Agent follows another lead</strong><small>Then narrows and checks the result</small></div><div className="job-progress"><i className="demo-wire"/><b>verify</b></div></div>
    <div className="job-board-foot"><Check size={15}/> The original job log remains available.</div>
  </div>;
}

function WorkspacesVisual(){
  return <div className="demo-workspace-compare" role="img" aria-label="Two connected agents have separate Hercules runtimes and workspaces; stopping one leaves the other running">
    <div className="workspace-column">
      <div className="workspace-client"><span className="workspace-client-icon"><TerminalWindow size={18}/></span><span>Client A<small>Hercules connection</small></span><i className="demo-wire"/></div>
      <div className="workspace-runtime"><HardDrives size={19}/><span>Runtime A<small>Started on request</small></span><Circle className="runtime-led" weight="fill" size={9}/></div>
      <div className="workspace-files"><FolderOpen size={18}/><span>Workspace A<small>Report and evidence remain</small></span></div>
    </div>
    <div className="workspace-separator" aria-hidden="true"><span>separate sessions</span></div>
    <div className="workspace-column">
      <div className="workspace-client"><span className="workspace-client-icon"><TerminalWindow size={18}/></span><span>Client B<small>Hercules connection</small></span><i className="demo-wire"/></div>
      <div className="workspace-runtime"><HardDrives size={19}/><span>Runtime B<small>Independent lifecycle</small></span><Circle className="runtime-led" weight="fill" size={9}/></div>
      <div className="workspace-files"><FolderOpen size={18}/><span>Workspace B<small>Own files and history</small></span></div>
    </div>
  </div>;
}

export default function ToolChains({reduced}:{reduced:boolean}){
  const root=useRef<HTMLElement>(null);
  const video=useRef<HTMLVideoElement>(null);
  const visible=useSectionMotion(root,reduced);
  const [videoFailed,setVideoFailed]=useState(false);
  useEffect(()=>{
    const element=video.current;
    if(!element||reduced||videoFailed)return;
    let inView=false;
    const sync=()=>{if(inView&&!document.hidden)void element.play().catch(()=>{});else element.pause();};
    const observer=new IntersectionObserver(entries=>{inView=entries[0]?.isIntersecting??false;sync();},{threshold:.05});
    observer.observe(element);
    document.addEventListener("visibilitychange",sync);
    return()=>{observer.disconnect();document.removeEventListener("visibilitychange",sync);element.pause();};
  },[reduced,videoFailed]);
  return <section id="tools" ref={root} className={`chapter wrap capabilities-section${visible?" is-visible":""}`} aria-labelledby="capability-title">
    <div className="feature-heading capability-heading"><h2 id="capability-title">From page to proof.</h2><p>See how an agent can inspect a real web app, map a lab, keep long checks moving, and separate workspaces.</p></div>
    <div className="capability-gallery">
      <article className="demo-card demo-main demo-browser" aria-labelledby="juice-title">
          <div className="demo-card-topline"><span className="demo-status"><i/>Real browser session</span><span>Juice Shop · private lab</span></div>
        <div className="juice-browser-frame">
          <div className="juice-browser-bar"><div className="browser-dots" aria-hidden="true"><i/><i/><i/></div><span>Local test app</span><span className="browser-local-chip">Docker network</span></div>
          <div className="juice-video-stage">
            {!reduced&&!videoFailed
              ? <video ref={video} key="juice-session" aria-label="Looping recording of Hercules driving a local OWASP Juice Shop browser walkthrough" src={demoAsset("juice-shop-session.mp4")} muted loop playsInline preload="metadata" poster={demoAsset("juice-shop-poster.png")} onError={()=>setVideoFailed(true)}/>
              : <img src={demoAsset("juice-shop-poster.png")} alt="Juice Shop confirms the Score Board challenge is solved, with 1 of 186 challenges completed" width="1280" height="600"/>}
            <span className="juice-recording-stamp"><i/>Real Hercules browser capture · 2.5×</span>
          </div>
        </div>
        <div className="demo-browser-copy">
          <div><h3 id="juice-title">Solve a challenge. Verify it in the app.</h3><p>Hercules maps and checks the local service, then opens Juice Shop’s hidden Score Board in a real CloakBrowser session. The app confirms the challenge and updates progress to 1 of 186. A screenshot and report are retained; the narration is scripted.</p></div>
          <div className="juice-proof-steps" aria-label="Walkthrough stages"><span><b>01</b> Start a private lab</span><ArrowRight size={15}/><span><b>02</b> Find the hidden board</span><ArrowRight size={15}/><span><b>03</b> Confirm it is solved</span></div>
        </div>
        <details className="demo-transcript"><summary>What the recording shows</summary><p>The app runs on a private Docker network with no published port. Hercules starts its own Kali runtime when asked, drives the browser through MCP, and writes a report that remains readable after the runtime stops. <a href={demoAsset("juice-shop-walkthrough.md")} target="_blank" rel="noreferrer">Read the verified walkthrough.</a> <a href={demoAsset("juice-shop-session.mp4")} target="_blank" rel="noreferrer">Open the full-size recording.</a></p></details>
        <p className="browser-limitation">CloakBrowser reduces common automation signals; it does not guarantee CAPTCHA or bot-detection bypass.</p>
      </article>

      <article className="demo-card demo-secondary demo-recon" aria-labelledby="recon-title">
        <div className="demo-card-topline"><span className="demo-kicker">Controlled target</span><Network size={19} aria-hidden="true"/></div>
        <ReconVisual/>
        <div className="demo-copy"><h3 id="recon-title">Map first. Then verify.</h3><p>Resolve a lab, discover its reachable services, and check the responses. An open port is a lead, not a finding.</p><a href={evidence("claude-network-120/reports/network.html")} target="_blank" rel="noreferrer">Read the verified inventory <ArrowUpRight size={16}/></a></div>
      </article>

      <article className="demo-card demo-secondary demo-parallel" aria-labelledby="parallel-title">
        <div className="demo-card-topline"><span className="demo-kicker">Background work</span><Pulse size={19} aria-hidden="true"/></div>
        <JobsVisual/>
        <div className="demo-copy"><h3 id="parallel-title">Keep the investigation moving.</h3><p>Send a long check to the background, then verify another lead. Review partial output, resume with a narrower check, and return to the same job log.</p><a href={evidence("claude-recovery-120/reports/recovery.html")} target="_blank" rel="noreferrer">See a recovered investigation <ArrowUpRight size={16}/></a></div>
      </article>

      <article className="demo-card demo-secondary demo-workspaces" aria-labelledby="workspaces-title">
        <div className="demo-card-topline"><span className="demo-kicker">Independent client sessions</span><HardDrives size={19} aria-hidden="true"/></div>
        <WorkspacesVisual/>
        <div className="demo-copy"><h3 id="workspaces-title">Separate work. Separate workspaces.</h3><p>Each connected client owns its Hercules runtime and workspace. Stop one runtime without merging the other client’s files or history.</p></div>
      </article>
    </div>
    <div className="capability-footnote"><p>Examples run against disposable local labs. Hercules returns real tool results; the investigation narration is scripted.</p><a className="text-link" href="https://github.com/0xMihirK/hercules-mcp#capabilities-and-mcp-surface">Explore the complete tool catalog <ArrowUpRight size={18}/></a></div>
  </section>;
}
