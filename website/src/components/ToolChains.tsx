import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ArrowRight } from "@phosphor-icons/react/ArrowRight";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { Check } from "@phosphor-icons/react/Check";
import { GlobeHemisphereWest } from "@phosphor-icons/react/GlobeHemisphereWest";
import { Network } from "@phosphor-icons/react/Network";
import { FileArchive } from "@phosphor-icons/react/FileArchive";
import { Fingerprint } from "@phosphor-icons/react/Fingerprint";
import { FileText } from "@phosphor-icons/react/FileText";
import { LockKey } from "@phosphor-icons/react/LockKey";
import { X } from "@phosphor-icons/react/X";
import { Hourglass } from "@phosphor-icons/react/Hourglass";
const asset=(path:string)=>import.meta.env.BASE_URL+"assets/recordings/evidence/"+path;
const services=[
  {label:"Website",port:"8000",icon:GlobeHemisphereWest},
  {label:"Slow endpoint",port:"8080",icon:Hourglass},
  {label:"HTTPS service",port:"8443",icon:LockKey}
];
const examples=[
  {id:"web",label:"Review a website",icon:GlobeHemisphereWest,title:"Check what really happens.",description:"Open a local website, exercise its sign-in flow, and check both the successful and rejected paths.",steps:["Open the website","Try both sign-in paths","Verify the result"],report:"claude-browser-120/reports/browser.html"},
  {id:"network",label:"Map a network",icon:Network,title:"Turn a target into a service map.",description:"Discover reachable services, inspect their responses, and verify what is actually running.",steps:["Resolve the local address","Discover scoped services","Check web and TLS responses"],report:"claude-network-120/reports/network.html"},
  {id:"ctf",label:"Solve a challenge",icon:Fingerprint,title:"Follow the clues. Test the answer.",description:"Solve a capture-the-flag puzzle by combining packet analysis, file extraction, and cryptographic checks.",steps:["Read the packet clues","Unlock the hidden archive","Reject the decoy and verify the flag"],report:"claude-forensics-120/reports/forensics.html"},
  {id:"report",label:"Write a report",icon:FileText,title:"Make the findings useful.",description:"Bring independent checks together in a readable report, with confirmed observations, rejected leads, and a clear scope.",steps:["Reconcile the observations","Separate findings from false leads","Explain the scope and limits"],report:"claude-website-120/reports/website.html"}
];
export default function ToolChains({reduced,paused}:{reduced:boolean;paused:boolean}){
  const [selected,setSelected]=useState(0),root=useRef<HTMLElement>(null);
  const example=examples[selected];
  useEffect(()=>{
    if(reduced || paused || !root.current)return;
    const context=gsap.context(()=>{
      gsap.fromTo(".capability-visual",{clipPath:"inset(0 0 8% 0)",y:12},{clipPath:"inset(0 0 0% 0)",y:0,duration:.55,ease:"power3.out"});
      if(selected===1)gsap.fromTo(".service-links i",{scaleX:0},{scaleX:1,transformOrigin:"left center",duration:.55,stagger:.12,ease:"power3.out"});
    },root);
    return()=>context.revert();
  },[selected,reduced,paused]);
  return <section id="tools" ref={root} className="chapter wrap capabilities-section">
    <div className="feature-heading"><h2>From the first clue<br/>to a clear answer.</h2><p>One investigation can bring together network scans, browser checks, file analysis, and reporting.</p></div>
    <div className="capability-tabs" role="tablist" aria-label="Investigation examples">{examples.map((item,i)=><button key={item.id} id={"capability-"+item.id} role="tab" aria-selected={selected===i} aria-controls="capability-panel" tabIndex={selected===i?0:-1} onClick={()=>setSelected(i)} onKeyDown={event=>{
      if(!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;
      event.preventDefault();const next=event.key==="Home"?0:event.key==="End"?3:(i+(event.key==="ArrowRight"?1:3))%4;
      setSelected(next);(event.currentTarget.parentElement?.children[next] as HTMLButtonElement)?.focus();
    }}><item.icon size={22} aria-hidden="true"/>{item.label}</button>)}</div>
    <div id="capability-panel" role="tabpanel" aria-labelledby={"capability-"+example.id} className={"capability-feature case-"+example.id}>
      <div className="capability-overview"><h3>{example.title}</h3><p>{example.description}</p><ol>{example.steps.map(step=><li key={step}><Check size={18} aria-hidden="true"/>{step}</li>)}</ol><a className="text-link" href={asset(example.report)} target="_blank" rel="noreferrer">Read the local lab report <ArrowUpRight size={18}/></a></div>
      <div key={example.id} className="capability-visual">
        {example.id==="web" && <figure className="browser-proof"><div className="proof-browser-bar"><GlobeHemisphereWest size={17}/><span>Local lab · signed-in screen</span></div><a className="browser-screenshot" href={asset("claude-browser-120/browser/review/artifacts/dashboard.png")} target="_blank" rel="noreferrer" aria-label="View the complete browser capture"><img src={asset("claude-browser-120/browser/review/artifacts/dashboard.png")} alt="Actual local lab dashboard after successful sign-in" width="1280" height="599" loading="lazy"/></a><figcaption>Screenshot excerpt · select to view the complete capture.</figcaption><div className="browser-checks"><div><Check size={23}/><span>Valid sign-in<strong>Dashboard reached</strong></span></div><div><X size={23}/><span>Incorrect password<strong>Access rejected</strong></span></div></div></figure>}
        {example.id==="network" && <div className="service-map" role="group" aria-label="The local lab exposes three scoped services: a website, a slow endpoint, and HTTPS."><div className="service-diagram"><div className="service-origin"><Network size={36} aria-hidden="true"/><strong>Local lab</strong></div><div className="service-links" aria-hidden="true"><i/><i/><i/></div><div className="service-endpoints">{services.map(service=><div key={service.port}><span className="service-name"><service.icon size={20} aria-hidden="true"/>{service.label}</span><small>Port <b>{service.port}</b></small></div>)}</div></div><p>Open services are leads. Further checks establish what they do.</p></div>}
        {example.id==="ctf" && <div className="challenge-proof"><div className="challenge-route"><span className="challenge-step"><span className="challenge-symbol"><Network size={27} aria-hidden="true"/></span><span>Packet clues</span></span><span className="challenge-link" aria-hidden="true"><i/><ArrowRight size={18}/></span><span className="challenge-step"><span className="challenge-symbol"><LockKey size={27} aria-hidden="true"/></span><span>Encrypted file</span></span><span className="challenge-link" aria-hidden="true"><i/><ArrowRight size={18}/></span><span className="challenge-step"><span className="challenge-symbol"><FileArchive size={27} aria-hidden="true"/></span><span>Hidden archive</span></span></div><p className="challenge-clue">The packet order supplies the key.</p><div className="verified-flag"><Fingerprint size={38}/><div><span>Flag verified against its checksum</span><code>HERCULES&#123;packet_to_carrier_to_verified_evidence&#125;</code></div></div><p className="challenge-rejected"><X size={18}/>Wrong key and decoy rejected.</p></div>}
        {example.id==="report" && <article className="report-proof" aria-label="Readable summary of the recorded website report"><div className="report-proof-header"><FileText size={28}/><span>Local website assessment</span></div><h4>One confirmed finding.<br/>One rejected lead.</h4><dl><div><dt><Check size={18}/>Confirmed</dt><dd>Debug data is exposed and independently confirmed in the browser.</dd></div><div><dt><X size={18}/>Ruled out</dt><dd>The suspected backup page returns 404.</dd></div><div><dt>Scope</dt><dd>A disposable local lab. No public target was contacted.</dd></div></dl></article>}
      </div>
    </div>
    <div className="capability-footnote"><p>These examples use real Hercules tools in local labs. Model decisions and reports are scripted.</p><a className="text-link" href="https://github.com/0xMihirK/hercules-mcp#capabilities-and-mcp-surface">Complete tool catalog <ArrowUpRight size={18}/></a></div>
  </section>;
}
