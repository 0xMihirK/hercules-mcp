import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ArrowRight } from "@phosphor-icons/react/ArrowRight";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { Browser } from "@phosphor-icons/react/Browser";
import { Check } from "@phosphor-icons/react/Check";
import { Circle } from "@phosphor-icons/react/Circle";
import { Code } from "@phosphor-icons/react/Code";
import { FolderOpen } from "@phosphor-icons/react/FolderOpen";
import { HardDrives } from "@phosphor-icons/react/HardDrives";
import { LockKey } from "@phosphor-icons/react/LockKey";
import { Network } from "@phosphor-icons/react/Network";
import { Pulse } from "@phosphor-icons/react/Pulse";
import { ShieldCheck } from "@phosphor-icons/react/ShieldCheck";
import { TerminalWindow } from "@phosphor-icons/react/TerminalWindow";

const evidence=(path:string)=>import.meta.env.BASE_URL+"assets/recordings/evidence/"+path;
const demoAsset=(path:string)=>import.meta.env.BASE_URL+"assets/demos/"+path;

export type CatalogItem={
  key:string;
  category:string;
  description:string;
  mandatory:boolean;
  mcp_tools:string[];
  backend_binaries:string[];
  wordlists:string[];
  metasploit:boolean;
  browser:boolean;
  note:string;
};

export type CatalogData={
  full_tool_count:number;
  without_metasploit_tool_count:number;
  resource_count:number;
  categories:{key:string;title:string}[];
  capabilities:CatalogItem[];
};

const MCP_RESOURCES=[
  {uri:"resource://agent_skills/nse",category:"Authoring guide",title:"Custom Nmap NSE Lua authoring",when:"Loaded when installed NSE scripts cannot express an authorized protocol or check."},
  {uri:"resource://agent_skills/nuclei",category:"Authoring guide",title:"Custom Nuclei YAML template authoring",when:"Loaded when installed Nuclei templates or tags cannot express the required detection."},
  {uri:"resource://post_exploitation/linpeas",category:"Linux enumeration",title:"Embedded LinPEAS lite script",when:"Used when an authorized Linux shell needs broad local privilege-escalation enumeration."},
  {uri:"resource://post_exploitation/winpeas",category:"Windows enumeration",title:"Embedded WinPEAS lite script",when:"Used when an authorized Windows command shell needs broad local enumeration."},
  {uri:"resource://post_exploitation/powerup",category:"PowerShell follow-up",title:"PowerUp service & registry checks",when:"Used when an authorized PowerShell session needs service or registry auditing."},
  {uri:"resource://post_exploitation/gtfobins",category:"Linux reference",title:"GTFOBins binary lookup",when:"Queried when Linux evidence identifies an exact sudo, SUID, or capability-enabled binary."},
  {uri:"resource://post_exploitation/lolbas",category:"Windows reference",title:"LOLBAS binary & script lookup",when:"Queried when Windows evidence identifies an exact signed binary, script, or library."}
];

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
    },{threshold:.08});
    observer.observe(root.current);
    return()=>observer.disconnect();
  },[reduced,root]);
  useEffect(()=>{
    if(!entered||reduced||!root.current)return;
    const context=gsap.context(()=>{
      const timeline=gsap.timeline({defaults:{ease:"power3.out"}});
      timeline.fromTo(".demo-main",{y:22,opacity:0},{y:0,opacity:1,duration:.65})
        .fromTo(".demo-secondary",{y:18,opacity:0},{y:0,opacity:1,duration:.55,stagger:.1},"-=.4")
        .fromTo(".catalog-explorer",{y:20,opacity:0},{y:0,opacity:1,duration:.55},"-=.25");
    },root);
    return()=>context.revert();
  },[entered,reduced,root]);
  return visible;
}

function ReconVisual(){
  return <div className="recon-board" role="img" aria-label="A scoped local lab is discovered first, then its sign-in app, proxy, and HTTPS service are individually verified">
    <div className="recon-board-top"><span><Pulse size={15} aria-hidden="true"/>Discovery &amp; verification sweep</span><small>172.30.102.10 · allowlisted lab</small></div>
    <div className="recon-board-body">
      <div className="recon-scope-node">
        <svg className="recon-radar-svg" viewBox="0 0 64 64" aria-hidden="true">
          <circle cx="32" cy="32" r="28" fill="none" stroke="#4d5e69" strokeWidth="1" strokeDasharray="3 3"/>
          <circle cx="32" cy="32" r="20" fill="none" stroke="#7d6250" strokeWidth="1"/>
          <circle cx="32" cy="32" r="11" fill="#162129" stroke="#d87950" strokeWidth="1.2"/>
          <line x1="32" y1="4" x2="32" y2="60" stroke="#33424b" strokeWidth="1"/>
          <line x1="4" y1="32" x2="60" y2="32" stroke="#33424b" strokeWidth="1"/>
          <g className="radar-sweep-group">
            <path d="M32 32 L32 6 A26 26 0 0 1 54 18 Z" fill="rgba(216,121,80,0.22)"/>
            <line x1="32" y1="32" x2="32" y2="6" stroke="#f0c09e" strokeWidth="1.5"/>
          </g>
          <circle className="radar-blip" cx="45" cy="17" r="3" fill="#f0c09e"/>
          <circle cx="32" cy="32" r="3" fill="#d87950"/>
        </svg>
        <strong>Scoped local lab</strong>
        <small>3 reachable ports</small>
      </div>
      <div className="recon-routes-col" aria-hidden="true">
        <svg className="recon-routes-svg" viewBox="0 0 92 144" preserveAspectRatio="none">
          <path d="M 0 72 C 38 72, 42 24, 92 24" fill="none" stroke="#5b6b75" strokeWidth="1.5"/>
          <path d="M 0 72 L 92 72" fill="none" stroke="#5b6b75" strokeWidth="1.5"/>
          <path d="M 0 72 C 38 72, 42 120, 92 120" fill="none" stroke="#5b6b75" strokeWidth="1.5"/>
          <path className="recon-route-pulse recon-route-pulse--1" d="M 0 72 C 38 72, 42 24, 92 24" fill="none" stroke="#f0c09e" strokeWidth="2"/>
          <path className="recon-route-pulse recon-route-pulse--2" d="M 0 72 L 92 72" fill="none" stroke="#f0c09e" strokeWidth="2"/>
          <path className="recon-route-pulse recon-route-pulse--3" d="M 0 72 C 38 72, 42 120, 92 120" fill="none" stroke="#f0c09e" strokeWidth="2"/>
          <circle cx="4" cy="72" r="3.5" fill="#d87950"/>
          <circle cx="88" cy="24" r="3" fill="#f0c09e"/>
          <circle cx="88" cy="72" r="3" fill="#f0c09e"/>
          <circle cx="88" cy="120" r="3" fill="#f0c09e"/>
        </svg>
      </div>
      <div className="recon-service-stack">
        <div className="recon-service recon-service--app">
          <span className="recon-service-main"><Browser size={16} aria-hidden="true"/><code>8000</code><span>HTTP sign-in</span></span>
          <em className="recon-badge">200 OK</em>
        </div>
        <div className="recon-service recon-service--proxy">
          <span className="recon-service-main"><Network size={16} aria-hidden="true"/><code>8080</code><span>HTTP proxy</span></span>
          <em className="recon-badge">Verified</em>
        </div>
        <div className="recon-service recon-service--tls">
          <span className="recon-service-main"><ShieldCheck size={16} aria-hidden="true"/><code>8443</code><span>HTTPS TLS</span></span>
          <em className="recon-badge">CA valid</em>
        </div>
      </div>
    </div>
    <div className="recon-board-foot"><Check size={15} aria-hidden="true"/> Discovery creates leads. Service verification creates evidence.</div>
  </div>;
}

function JobsVisual(){
  return <div className="demo-job-board" role="img" aria-label="A long-running background check keeps its output while the agent moves to a second lead, then returns to resume it">
    <div className="job-board-heading"><span><Pulse size={15} aria-hidden="true"/>Parallel job orchestration</span><span className="job-live"><i/>job_8f2a active</span></div>
    <div className="job-lanes">
      <div className="job-lane job-lane--running">
        <div className="job-lane-top">
          <span className="job-icon"><TerminalWindow size={17}/></span>
          <div className="job-lane-title"><strong>Long-running scan</strong><small>Buffered output stays readable</small></div>
          <span className="job-status-pill is-running">Running</span>
        </div>
        <div className="job-bar-track" aria-hidden="true"><i className="job-bar-fill job-bar-fill--stream"/></div>
      </div>
      <div className="job-fork-row" aria-hidden="true">
        <svg className="job-fork-svg" viewBox="0 0 320 26" preserveAspectRatio="none">
          <path d="M 26 0 L 26 13 L 160 13 L 160 26" fill="none" stroke="#d87950" strokeWidth="1.5" strokeDasharray="3 3"/>
          <path d="M 278 26 L 278 13 L 304 13 L 304 0" fill="none" stroke="#8596a2" strokeWidth="1.5"/>
          <circle cx="26" cy="4" r="3" fill="#d87950"/>
          <circle cx="160" cy="22" r="3" fill="#f0c09e"/>
          <circle cx="304" cy="4" r="3" fill="#f0c09e"/>
        </svg>
        <span>Agent pivots to verify a fast lead while background job continues</span>
      </div>
      <div className="job-lane job-lane--verify">
        <div className="job-lane-top">
          <span className="job-icon"><Browser size={17}/></span>
          <div className="job-lane-title"><strong>Targeted HTTP &amp; browser check</strong><small>Confirms live route &amp; narrows scope</small></div>
          <span className="job-status-pill is-verified">Verified</span>
        </div>
        <div className="job-bar-track" aria-hidden="true"><i className="job-bar-fill job-bar-fill--done"/></div>
      </div>
    </div>
    <div className="job-board-foot"><Check size={15} aria-hidden="true"/> Reconnect to the background job with its earlier output intact.</div>
  </div>;
}

function WorkspacesVisual(){
  return <div className="demo-workspace-compare" role="img" aria-label="Two connected clients each own a Hercules runtime and workspace, separated by a boundary">
    <div className="session-pod session-pod--a">
      <div className="session-pod-head">
        <TerminalWindow size={18}/>
        <div><strong>Client A · Claude Code</strong><small>STDIO session a81f · Port set 15553</small></div>
        <span className="session-state-tag"><Circle className="runtime-led" weight="fill" size={8}/>Active</span>
      </div>
      <div className="session-pipeline">
        <div className="session-node"><HardDrives size={18}/><div><b>Kali container A</b><small>Started on request</small></div></div>
        <div className="session-wire" aria-hidden="true"><i/><ArrowRight size={14}/></div>
        <div className="session-node"><FolderOpen size={18}/><div><b>Workspace A</b><small>Reports &amp; raw evidence</small></div></div>
      </div>
    </div>
    <div className="workspace-separator" aria-hidden="true">
      <i/>
      <span className="separator-badge"><LockKey size={14}/>Isolated PID, ports &amp; mounts</span>
      <i/>
    </div>
    <div className="session-pod session-pod--b">
      <div className="session-pod-head">
        <TerminalWindow size={18}/>
        <div><strong>Client B · Codex</strong><small>STDIO session c39d · Port set 15554</small></div>
        <span className="session-state-tag"><Circle className="runtime-led" weight="fill" size={8}/>Active</span>
      </div>
      <div className="session-pipeline">
        <div className="session-node"><HardDrives size={18}/><div><b>Kali container B</b><small>Independent lifecycle</small></div></div>
        <div className="session-wire" aria-hidden="true"><i/><ArrowRight size={14}/></div>
        <div className="session-node"><FolderOpen size={18}/><div><b>Workspace B</b><small>Separate files &amp; logs</small></div></div>
      </div>
    </div>
  </div>;
}

export default function ToolChains({catalog,reduced,paused}:{catalog:CatalogData;reduced:boolean;paused:boolean}){
  const root=useRef<HTMLElement>(null);
  const video=useRef<HTMLVideoElement>(null);
  const visible=useSectionMotion(root,reduced);
  const [videoFailed,setVideoFailed]=useState(false);
  const [selectedCategory,setSelectedCategory]=useState<string>("all");
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

  const filteredBundles=selectedCategory==="all"
    ? catalog.capabilities
    : catalog.capabilities.filter(item=>item.category===selectedCategory);

  return <section id="tools" ref={root} className={`chapter wrap capabilities-section${visible?" is-visible":""}`} aria-labelledby="capability-title">
    <div className="feature-heading feature-heading--split capability-heading">
      <div><h2 id="capability-title">From page to proof.</h2></div>
      <p>See how an agent inspects a real web application in CloakBrowser, maps an allowlisted lab, orchestrates background jobs, and isolates concurrent workspaces.</p>
    </div>
    <div className="capability-gallery">
      <article className="demo-card demo-main demo-browser" aria-labelledby="juice-title">
        <div className="demo-card-topline"><span className="demo-status"><i/>Real CloakBrowser session</span><span>OWASP Juice Shop · private Docker lab</span></div>
        <div className="juice-browser-frame">
          <div className="juice-browser-bar">
            <div className="browser-dots" aria-hidden="true"><i/><i/><i/></div>
            <span className="browser-url">http://172.30.78.10:3000/#/login</span>
            <span className="browser-local-chip">Edited local-lab capture · 2.5×</span>
          </div>
          <div className="juice-video-stage">
            {!reduced&&!paused&&!videoFailed
              ? <video ref={video} key="juice-session" aria-label="Looping recording of Hercules driving a local OWASP Juice Shop browser walkthrough" src={demoAsset("juice-shop-session.mp4")} muted loop playsInline preload="metadata" poster={demoAsset("juice-shop-poster.png")} onError={()=>setVideoFailed(true)}/>
              : <img src={demoAsset("juice-shop-poster.png")} alt="Juice Shop confirms Login Admin and Score Board, with 2 of 186 challenges completed" width="1280" height="600"/>}
          </div>
        </div>
        <div className="demo-browser-copy">
          <div>
            <h3 id="juice-title">Test a local challenge. Keep the proof.</h3>
            <p>Hercules discovers the private service on port 3000, drives CloakBrowser through the authentication flow, captures screenshot proof, and writes the structured report. Juice Shop confirms Login Admin and Score Board. Model narration is scripted.</p>
          </div>
          <div className="juice-proof-steps" role="group" aria-label="Walkthrough stages">
            <div className="proof-step"><b>Private lab</b><small>172.30.78.10:3000 ready</small></div>
            <ArrowRight size={16} aria-hidden="true"/>
            <div className="proof-step"><b>Browser check</b><small>Login path verified</small></div>
            <ArrowRight size={16} aria-hidden="true"/>
            <div className="proof-step"><b>Verified result</b><small>Host report retained</small></div>
          </div>
        </div>
        <details className="demo-transcript"><summary>What the recording shows</summary><p>The target application runs on a private Docker network with no published host port. Hercules starts its Kali runtime on request, drives CloakBrowser through MCP across 28 tool calls, and writes a Markdown and HTML report that remains in the host workspace after the container stops. <a href={demoAsset("juice-shop-walkthrough.md")} target="_blank" rel="noreferrer">Read the verified walkthrough.</a> <a href={demoAsset("juice-shop-session.mp4")} target="_blank" rel="noreferrer">Open the full-size recording.</a></p></details>
        <p className="browser-limitation">CloakBrowser reduces common automation signals; it does not guarantee CAPTCHA or bot-detection bypass.</p>
        <div className="demo-outcome">
          <div className="demo-outcome-count">2<span>/ 186</span></div>
          <div>
            <strong><Check size={16} aria-hidden="true"/>Two local training challenges verified</strong>
            <p>Juice Shop’s built-in challenge tracker confirms Login Admin and Score Board.</p>
            <a href={demoAsset("juice-shop-walkthrough.md")} target="_blank" rel="noreferrer">Read the walkthrough <ArrowUpRight size={15} aria-hidden="true"/></a>
          </div>
        </div>
      </article>

      <article className="demo-card demo-secondary demo-recon" aria-labelledby="recon-title">
        <div className="demo-card-topline"><span className="demo-kicker">Controlled target scope</span><Network size={19} aria-hidden="true"/></div>
        <ReconVisual/>
        <div className="demo-copy"><h3 id="recon-title">Map first. Then verify.</h3><p>Resolve an allowlisted lab, discover reachable ports, and inspect actual HTTP and TLS responses before reporting. An open port is a lead, not a finding.</p><a href={evidence("claude-network-120/reports/network.html")} target="_blank" rel="noreferrer">Read the verified inventory <ArrowUpRight size={16}/></a></div>
      </article>

      <article className="demo-card demo-secondary demo-parallel" aria-labelledby="parallel-title">
        <div className="demo-card-topline"><span className="demo-kicker">Asynchronous background jobs</span><Pulse size={19} aria-hidden="true"/></div>
        <JobsVisual/>
        <div className="demo-copy"><h3 id="parallel-title">Keep the investigation moving.</h3><p>Launch long-running scans in the background while verifying another lead in parallel. Inspect partial output at any point and return to the same job log.</p><a href={evidence("claude-recovery-120/reports/recovery.html")} target="_blank" rel="noreferrer">See a recovered investigation <ArrowUpRight size={16}/></a></div>
      </article>

      <article className="demo-card demo-secondary demo-workspaces" aria-labelledby="workspaces-title">
        <div className="demo-card-topline"><span className="demo-kicker">Concurrent multi-agent isolation</span><HardDrives size={19} aria-hidden="true"/></div>
        <div className="demo-workspaces-body">
          <WorkspacesVisual/>
          <div className="demo-copy demo-copy--workspaces">
            <h3 id="workspaces-title">Separate work. Separate workspaces.</h3>
            <p>Each connected STDIO client owns its Hercules session, Kali container, auto-allocated loopback ports, and host workspace directory. Stopping one session cleans up only its owned container without touching another client’s active jobs or retained files.</p>
          </div>
        </div>
      </article>
    </div>

    <div className="catalog-explorer" aria-labelledby="catalog-explorer-title">
      <div className="catalog-explorer-head">
        <div>
          <h3 id="catalog-explorer-title">Complete MCP tool &amp; capability catalog</h3>
          <p>One catalog governs both the binaries built into the Kali Docker image and the MCP tool schemas advertised to your agent—keeping unused schemas out of the model’s context window.</p>
        </div>
        <div className="catalog-profile-pills" aria-label="Capability profiles">
          <span><b>{catalog.full_tool_count}</b> tools (Full profile)</span>
          <span><b>{catalog.without_metasploit_tool_count}</b> tools (SKIP_METASPLOIT)</span>
          <span><b>{catalog.resource_count}</b> MCP resources</span>
        </div>
      </div>

      <div className="catalog-filter-bar" role="tablist" aria-label="Filter capabilities by security domain">
        <button type="button" role="tab" aria-selected={selectedCategory==="all"} onClick={()=>setSelectedCategory("all")}>
          All bundles <span>{catalog.capabilities.length}</span>
        </button>
        {catalog.categories.map(cat=>{
          const count=catalog.capabilities.filter(c=>c.category===cat.key).length;
          return <button key={cat.key} type="button" role="tab" aria-selected={selectedCategory===cat.key} onClick={()=>setSelectedCategory(cat.key)}>
            {cat.title} <span>{count}</span>
          </button>;
        })}
        <button type="button" role="tab" aria-selected={selectedCategory==="resources"} onClick={()=>setSelectedCategory("resources")}>
          MCP Resources <span>{catalog.resource_count}</span>
        </button>
      </div>

      {selectedCategory==="resources" ? (
        <div className="catalog-grid catalog-grid--resources" role="region" aria-label="MCP Resources">
          {MCP_RESOURCES.map(res=><div key={res.uri} className="catalog-bundle-card is-resource">
            <div className="bundle-card-top">
              <strong>{res.title}</strong>
              <span className="bundle-tag">{res.category}</span>
            </div>
            <code className="resource-uri">{res.uri}</code>
            <p className="bundle-resource-desc">{res.when}</p>
          </div>)}
        </div>
      ) : (
        <div className="catalog-grid" role="region" aria-label="Capability bundles">
          {filteredBundles.map(item=><div key={item.key} className={`catalog-bundle-card${item.mandatory?" is-mandatory":""}`}>
            <div className="bundle-card-top">
              <div>
                <strong>{item.description}</strong>
                <span className="bundle-key">bundle: {item.key}</span>
              </div>
              <span className={`bundle-tag${item.mandatory?" is-core":""}`}>{item.mandatory?"Core · Mandatory":catalog.categories.find(c=>c.key===item.category)?.title || item.category}</span>
            </div>
            <div className="bundle-tools" aria-label="Registered MCP tools">
              {item.mcp_tools.map(tool=><code key={tool}><Code size={12} aria-hidden="true"/>{tool}</code>)}
            </div>
            <div className="bundle-meta">
              <span><b>Kali binaries:</b> {item.backend_binaries.join(", ")}</span>
              {item.wordlists.length>0 && <span><b>Wordlists:</b> {item.wordlists.join(", ")}</span>}
            </div>
          </div>)}
        </div>
      )}
    </div>

    <div className="capability-footnote"><p>Demonstrations execute against disposable local labs. Hercules returns real tool results; model investigation narration is scripted.</p><a className="text-link" href="https://github.com/0xMihirK/hercules-mcp#capabilities-and-mcp-surface">View documentation on GitHub <ArrowUpRight size={18}/></a></div>
  </section>;
}
