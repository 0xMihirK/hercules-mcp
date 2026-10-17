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

// `visible` tracks the viewport so the looping keyframes stop when the section
// scrolls away; `entered` latches once so the entrance plays a single time.
function useSectionMotion(root:React.RefObject<HTMLElement|null>, reduced:boolean){
  const [visible,setVisible]=useState(reduced);
  const [entered,setEntered]=useState(reduced);
  useEffect(()=>{
    if(reduced||!root.current){setVisible(true);setEntered(true);return;}
    const observer=new IntersectionObserver(entries=>{
      const showing=entries.some(entry=>entry.isIntersecting);
      setVisible(showing);
      if(showing)setEntered(true);
    },{threshold:.12});
    observer.observe(root.current);
    return()=>observer.disconnect();
  },[reduced,root]);
  useEffect(()=>{
    if(!entered||reduced||!root.current)return;
    const context=gsap.context(()=>{
      const timeline=gsap.timeline({defaults:{ease:"power3.out"}});
      timeline.fromTo(".demo-main",{y:24,clipPath:"inset(0 0 9% 0)"},{y:0,clipPath:"inset(0 0 0 0)",duration:.7})
        .fromTo(".demo-secondary",{y:18,opacity:.35},{y:0,opacity:1,duration:.55,stagger:.12},"-=.42");
    },root);
    return()=>context.revert();
  },[entered,reduced,root]);
  return visible;
}

function ReconVisual(){
  return <div className="recon-board" role="img" aria-label="A scoped local lab is discovered first, then its sign-in app, proxy, and HTTPS service are individually verified">
    <div className="recon-board-top"><span><Pulse size={14} aria-hidden="true"/>Discovery sweep</span><small>allowlisted local lab</small></div>
    <div className="recon-board-body">
      <div className="recon-scope-node"><span className="recon-radar"><Network size={25} aria-hidden="true"/><i/></span><strong>Scoped local lab</strong><small>3 reachable services</small></div>
      <div className="recon-discovery" aria-hidden="true"><span>discover</span><i/><i/><i/></div>
      <div className="recon-service-stack">
        <div className="recon-service recon-service--app"><span><Browser size={16} aria-hidden="true"/><b>8000</b><small>sign-in</small></span><em>responded</em></div>
        <div className="recon-service recon-service--proxy"><span><Network size={16} aria-hidden="true"/><b>8080</b><small>proxy</small></span><em>response checked</em></div>
        <div className="recon-service recon-service--tls"><span><Check size={16} aria-hidden="true"/><b>8443</b><small>HTTPS</small></span><em>CA verified</em></div>
      </div>
    </div>
    <div className="recon-board-foot"><Check size={14} aria-hidden="true"/> Discovery creates leads. Verification creates evidence.</div>
  </div>;
}

function JobsVisual(){
  return <div className="demo-job-board" role="img" aria-label="A long-running background check keeps its output while the agent moves to a second lead, then returns to resume it">
    <div className="job-board-heading"><span><Pulse size={14} aria-hidden="true"/>Parallel investigation</span><span className="job-live"><i/>1 check continues</span></div>
    <div className="job-clock" aria-hidden="true"><span>start</span><i/><span>switch focus</span><i/><span>resume</span></div>
    <div className="job-lane job-lane--running"><span className="job-icon"><TerminalWindow size={19}/></span><div><strong>Long-running check</strong><small>Partial output stays available</small></div><div className="job-progress"><i/><b>running</b></div></div>
    <div className="job-handoff"><span>Agent follows a second lead while the job stays active</span><i aria-hidden="true"/></div>
    <div className="job-lane job-lane--verify"><span className="job-icon"><Browser size={19}/></span><div><strong>Targeted browser check</strong><small>Result narrows the return path</small></div><div className="job-progress"><i/><b>verified</b></div></div>
    <div className="job-board-foot"><Check size={15}/> Return to the same log with its earlier output intact.</div>
  </div>;
}

function WorkspacesVisual(){
  return <div className="demo-workspace-compare" role="img" aria-label="Two connected clients each own a Hercules runtime and workspace, separated by a boundary">
    <div className="session-pod session-pod--a"><div className="session-pod-head"><TerminalWindow size={17}/><span>Client A<small>connected</small></span><Circle className="runtime-led" weight="fill" size={8}/></div><div className="session-path"><div><HardDrives size={17}/><span>Kali runtime<small>started on request</small></span></div><i/><div><FolderOpen size={17}/><span>Workspace A<small>report and evidence</small></span></div></div></div>
    <div className="workspace-separator" aria-hidden="true"><i/><span>session boundary</span><i/></div>
    <div className="session-pod session-pod--b"><div className="session-pod-head"><TerminalWindow size={17}/><span>Client B<small>connected</small></span><Circle className="runtime-led" weight="fill" size={8}/></div><div className="session-path"><div><HardDrives size={17}/><span>Kali runtime<small>own lifecycle</small></span></div><i/><div><FolderOpen size={17}/><span>Workspace B<small>files and history</small></span></div></div></div>
  </div>;
}

export default function ToolChains({reduced,paused}:{reduced:boolean;paused:boolean}){
  const root=useRef<HTMLElement>(null);
  const video=useRef<HTMLVideoElement>(null);
  const visible=useSectionMotion(root,reduced);
  const [videoFailed,setVideoFailed]=useState(false);
  useEffect(()=>{
    const element=video.current;
    if(!element||reduced||paused||videoFailed)return;
    let inView=false;
    const sync=()=>{if(inView&&!document.hidden)void element.play().catch(()=>{});else element.pause();};
    const observer=new IntersectionObserver(entries=>{inView=entries[0]?.isIntersecting??false;sync();},{threshold:.05});
    observer.observe(element);
    document.addEventListener("visibilitychange",sync);
    return()=>{observer.disconnect();document.removeEventListener("visibilitychange",sync);element.pause();};
  },[reduced,paused,videoFailed]);
  return <section id="tools" ref={root} className={`chapter wrap capabilities-section${visible?" is-visible":""}`} aria-labelledby="capability-title">
    <div className="feature-heading capability-heading feature-heading--rule"><h2 id="capability-title">From page to proof.</h2><p>See how an agent can inspect a real web app, map a lab, keep long checks moving, and separate workspaces.</p></div>
    <div className="capability-gallery">
      <article className="demo-card demo-main demo-browser" aria-labelledby="juice-title">
          <div className="demo-card-topline"><span className="demo-status"><i/>Real browser session</span><span>Juice Shop · private lab</span></div>
        <div className="juice-browser-frame">
          <div className="juice-browser-bar"><div className="browser-dots" aria-hidden="true"><i/><i/><i/></div><span>Local test app</span><span className="browser-local-chip">Docker network</span></div>
          <div className="juice-video-stage">
            {!reduced&&!paused&&!videoFailed
              ? <video ref={video} key="juice-session" aria-label="Looping recording of Hercules driving a local OWASP Juice Shop browser walkthrough" src={demoAsset("juice-shop-session.mp4")} muted loop playsInline preload="metadata" poster={demoAsset("juice-shop-poster.png")} onError={()=>setVideoFailed(true)}/>
              : <img src={demoAsset("juice-shop-poster.png")} alt="Juice Shop confirms Login Admin and Score Board, with 2 of 186 challenges completed" width="1280" height="600"/>}
          </div>
          <span className="juice-recording-stamp"><i/>Edited local-lab capture · 2.5×</span>
        </div>
        <div className="demo-browser-copy">
          <div><h3 id="juice-title">Test a local challenge. Keep the proof.</h3><p>Hercules checks the private service, follows the login path in CloakBrowser, and writes the report. Juice Shop confirms Login Admin and Score Board. The narration is scripted.</p></div>
          <div className="juice-proof-steps" role="group" aria-label="Walkthrough stages">
            <span className="proof-step"><b>Private lab</b><small>network ready</small></span><ArrowRight size={15}/>
            <span className="proof-step"><b>Browser check</b><small>login path tested</small></span><ArrowRight size={15}/>
            <span className="proof-step"><b>Verified result</b><small>report retained</small></span>
          </div>
        </div>
        <details className="demo-transcript"><summary>What the recording shows</summary><p>The app runs on a private Docker network with no published port. Hercules starts its own Kali runtime when asked, drives the browser through MCP, and writes a report that remains readable after the runtime stops. <a href={demoAsset("juice-shop-walkthrough.md")} target="_blank" rel="noreferrer">Read the verified walkthrough.</a> <a href={demoAsset("juice-shop-session.mp4")} target="_blank" rel="noreferrer">Open the full-size recording.</a></p></details>
        <p className="browser-limitation">CloakBrowser reduces common automation signals; it does not guarantee CAPTCHA or bot-detection bypass.</p>
        <div className="demo-outcome"><div className="demo-outcome-count">2<span>/ 186</span></div><div><strong><Check size={16} aria-hidden="true"/>Two local challenges verified</strong><p>Juice Shop’s own challenge tracker confirms Login Admin and Score Board.</p><a href={demoAsset("juice-shop-walkthrough.md")} target="_blank" rel="noreferrer">Read the walkthrough <ArrowUpRight size={15} aria-hidden="true"/></a></div></div>
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
