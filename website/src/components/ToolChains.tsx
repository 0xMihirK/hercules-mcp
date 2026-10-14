import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowRight, ArrowUpRight, Check, GlobeHemisphereWest, Network, FileArchive, FileImage, Fingerprint, FileText, MagnifyingGlass, X } from "@phosphor-icons/react";
import { stories } from "./SessionStory";
gsap.registerPlugin(ScrollTrigger);
const asset=(path:string)=>import.meta.env.BASE_URL+"assets/"+path;
export default function ToolChains({reduced,paused}:{reduced:boolean;paused:boolean}){
  const root=useRef<HTMLElement>(null);
  useEffect(()=>{
    if(reduced || paused || !root.current)return;
    const context=gsap.context(()=>{
      gsap.from(".capability", {y:28,duration:.8,stagger:.12,ease:"power3.out",scrollTrigger:{trigger:root.current,start:"top 85%",once:true}});
      gsap.fromTo(".network-link",{strokeDashoffset:180},{strokeDashoffset:0,duration:2.2,ease:"power2.out",scrollTrigger:{trigger:".network-map",start:"top 85%",once:true}});
      gsap.from(".clue-step",{y:18,stagger:.18,duration:.6,scrollTrigger:{trigger:".clue-trail",start:"top 85%",once:true}});
    },root);
    return()=>context.revert();
  },[reduced,paused]);
  return <section id="tools" ref={root} className="chapter wrap capabilities-section">
    <div className="feature-heading"><h2>One workspace.<br/>Many ways to investigate.</h2><p>Follow a question through discovery, verification, and a report someone else can understand.</p></div>
    <div className="capability-gallery">
      <article className="capability capability-network"><div className="capability-title"><Network size={28}/><h3>Map a network.</h3></div><p>Discover exposed services, confirm what responds, and build a useful inventory.</p>
        <div className="network-map" role="img" aria-label="A local lab connection is checked for web services and certificate behavior."><svg viewBox="0 0 600 240" aria-hidden="true"><path className="network-link" d="M95 120H235L370 50H500M235 120H500M235 120L370 190H500" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="180"/></svg><div className="map-origin"><GlobeHemisphereWest size={37}/><span>Local lab</span></div><div className="map-hub"><MagnifyingGlass size={27}/><span>Verify</span></div><div className="map-endpoints"><span>Reachable services</span><span>Website response</span><span>Certificate check</span></div></div>
        <div className="capability-outcome"><Check size={18}/><span>A verified inventory, with evidence.</span></div>
      </article>
      <article className="capability capability-web"><div className="capability-title"><GlobeHemisphereWest size={28}/><h3>Review a website.</h3></div><p>Cross-check suspicious behavior in the browser. Keep the finding; reject the false positive.</p><div className="website-review" aria-label="Illustrated website investigation, based on the local lab"><div className="review-address"><GlobeHemisphereWest size={17}/><span>Local website</span><MagnifyingGlass size={17}/></div><div className="review-question">Two leads.<br/><strong>Which one holds up?</strong></div><div className="review-verdict"><Check size={20}/><div><strong>Debug access confirmed</strong><span>Independent request + browser check</span></div></div><div className="review-verdict rejected"><X size={20}/><div><strong>Backup route ruled out</strong><span>The suspected page does not exist</span></div></div></div><div className="verification-pair"><span><Check size={17}/>Evidence cross-checked</span><span><X size={17}/>False positive rejected</span></div></article>
      <article className="capability capability-ctf"><div className="capability-title"><Fingerprint size={28}/><h3>Follow the hidden layers.</h3></div><p>A challenge takes more than one tool. Let each clue change what you inspect next.</p><div className="clue-trail">{[{icon:Network,label:"Packet clues"},{icon:FileImage,label:"Carrier file"},{icon:FileArchive,label:"Hidden archive"},{icon:Fingerprint,label:"Verified flag"}].map(({icon:Icon,label},i)=><div className="clue-step" key={label}><Icon size={36}/><span>{label}</span>{i<3 && <ArrowRight size={18} aria-hidden="true"/>}</div>)}</div><p className="clue-decision"><X size={17}/>Wrong key and decoy rejected.<Check size={17}/>Answer checked against its checksum.</p></article>
      <article className="capability capability-report"><div className="capability-title"><FileText size={28}/><h3>Leave a clear report.</h3></div><div className="report-sample"><span>Website assessment</span><h4>What was confirmed.<br/>What was ruled out.</h4><p>{stories.website.summary}</p><div><span><Check size={17}/>Confirmed debug endpoint</span><span><X size={17}/>Backup route rejected</span></div></div><a className="text-link" href={asset("recordings/evidence/claude-website-120/reports/website.html")} target="_blank" rel="noreferrer">View the local lab report <ArrowUpRight size={18}/></a></article>
    </div>
    <a className="catalog-source text-link" href="https://github.com/0xMihirK/hercules-mcp#capabilities-and-mcp-surface">Explore all capabilities in the documentation <ArrowUpRight size={18}/></a>
  </section>;
}
