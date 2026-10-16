import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowRight } from "@phosphor-icons/react/ArrowRight";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { Check } from "@phosphor-icons/react/Check";
import { FunnelSimple } from "@phosphor-icons/react/FunnelSimple";
import { WarningCircle } from "@phosphor-icons/react/WarningCircle";
import specimen from "../../assets/filter-example.json";
gsap.registerPlugin(ScrollTrigger);
export type Measurement={tool:string;rawCharacters:number;inlineResponseCharacters:number;characterReduction:number;rawTokenEstimate:number;inlineTokenEstimate:number;outputComplete:boolean;evidenceComplete:boolean;outputFiltered:boolean;rawArtifact:string;file?:string;caseTitle?:string};
const kept=new Set(specimen.filtered.trimEnd().split("\n"));
export default function EvidencePipeline({reduced,paused}:{reduced:boolean;paused:boolean}){
  const root=useRef<HTMLElement>(null),[filtered,setFiltered]=useState(true);
  useEffect(()=>{
    if(reduced || paused || !root.current)return;
    setFiltered(false);
    const trigger=ScrollTrigger.create({trigger:root.current.querySelector(".filter-demonstration"),start:"top 70%",once:true,onEnter:()=>setFiltered(true)});
    return()=>trigger.kill();
  },[reduced,paused]);
  useEffect(()=>{
    if(!root.current)return;
    const context=gsap.context(()=>{
      if(reduced || paused){gsap.set(".filter-noise",{height:filtered?0:"auto",opacity:filtered?0:1});return;}
      const timeline=gsap.timeline();
      timeline.to(".filter-noise",{height:filtered?0:"auto",opacity:filtered?0:1,duration:.65,stagger:.08,ease:"power3.inOut"});
      timeline.fromTo(".filter-kept",{x:filtered?-8:0},{x:0,duration:.6,stagger:.09,ease:"power3.out"},.2);
    },root);
    return()=>context.revert();
  },[filtered,reduced,paused]);
  return <section id="evidence" ref={root} className="chapter wrap efficiency-section">
    <div className="feature-heading"><h2>Keep the finding.<br/>Lose the routine noise.</h2><p>Hercules filters known scanner chatter before it reaches your agent. Useful findings and important diagnostics remain.</p></div>
    <div className="filter-demonstration">
      <div className="filter-example"><div className="filter-example-bar"><span>{filtered?"Filtered response":"Original scanner output"}</span><button onClick={()=>setFiltered(value=>!value)}><FunnelSimple size={18}/>{filtered?"Compare original":"Apply filter"}</button></div><div className="filter-output-lines" role="group" aria-label={filtered?"Filtered scanner example":"Original scanner example"}>{specimen.raw.trimEnd().split("\n").map((line,i)=><div key={i} aria-hidden={!kept.has(line) && filtered} className={kept.has(line)?"filter-kept":"filter-noise"}><code>{line}</code></div>)}</div><p className="filter-example-note">Illustrative lab input, processed by the actual Hercules filter.</p></div>
      <div className="filter-explanation"><FunnelSimple size={42}/><h3>A shorter response.<br/>The finding stays.</h3><p>Removing routine text saves context tokens. Compare the original and filtered output: banners and timestamps disappear; the finding and warning stay visible.</p><div className="filter-keeps"><span><Check size={20}/>Finding retained</span><span><WarningCircle size={20}/>Incomplete scan disclosed</span></div><a className="text-link" href="https://github.com/0xMihirK/hercules-mcp#output-artifacts-sessions-and-workspaces">How output filtering works <ArrowUpRight size={18}/></a></div>
    </div>
    <div className="output-limit-note"><strong>Filtering and response limits do different jobs.</strong><p>Filters remove characterized noise. Separate size limits keep large responses manageable, with files available for follow-up reading. Hercules reports whether output was shortened and whether complete raw output is available.</p><ArrowRight size={22} aria-hidden="true"/></div>
  </section>;
}
