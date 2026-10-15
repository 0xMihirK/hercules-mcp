import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowRight, ArrowUpRight, Check, FunnelSimple, WarningCircle, FileText } from "@phosphor-icons/react";
gsap.registerPlugin(ScrollTrigger);
export type Measurement={tool:string;rawCharacters:number;inlineResponseCharacters:number;characterReduction:number;rawTokenEstimate:number;inlineTokenEstimate:number;outputComplete:boolean;evidenceComplete:boolean;outputFiltered:boolean;rawArtifact:string;file?:string;caseTitle?:string};
export default function EvidencePipeline({reduced,paused}:{reduced:boolean;paused:boolean}){
  const root=useRef<HTMLElement>(null);
  useEffect(()=>{
    if(reduced || paused || !root.current)return;
    const context=gsap.context(()=>{
      const timeline=gsap.timeline({scrollTrigger:{trigger:".filter-scene",start:"top 80%",end:"bottom 55%",scrub:.5}});
      timeline.to(".noise-line i",{scaleX:0,transformOrigin:"left",stagger:.12,duration:.6},0);
      timeline.fromTo(".retained-line",{x:-20},{x:0,stagger:.15,duration:.8},.3);
      timeline.fromTo(".filter-output",{y:22},{y:0,duration:1,ease:"none"},0);
    },root);
    return()=>context.revert();
  },[reduced,paused]);
  return <section id="evidence" ref={root} className="chapter wrap efficiency-section">
    <div className="feature-heading"><h2>Filter scanner noise<br/>before it reaches your agent.</h2><p>Tool-specific filters remove known banners and repeated progress messages while keeping findings and important diagnostics.</p></div>
    <div className="filter-scene">
      <div className="filter-input"><h3>Before filtering</h3><div className="output-line noise-line"><span>Scanner banners</span><i/></div><div className="output-line noise-line"><span>Repeated progress</span><i/></div><div className="output-line finding-line"><Check size={18}/><span>Findings</span></div><div className="output-line warning-line"><WarningCircle size={18}/><span>Warnings and errors</span></div><div className="output-line noise-line"><span>Routine startup messages</span><i/></div></div>
      <div className="filter-transform"><div><FunnelSimple size={46}/><span>Hercules filters</span></div><ArrowRight size={23} aria-hidden="true"/></div>
      <div className="filter-output"><h3>After filtering</h3><div className="retained-line"><Check size={23}/><div><strong>Useful findings</strong><p>Results that guide the next check.</p></div></div><div className="retained-line"><WarningCircle size={23}/><div><strong>Important diagnostics</strong><p>Warnings, failures, and limits stay visible.</p></div></div><div className="filter-benefit"><span>Fewer repeated messages to read.</span><strong>Fewer tokens spent on routine output.</strong></div></div>
    </div>
    <div className="efficiency-notes"><div><FileText size={26}/><h3>Large responses have a separate limit.</h3><p>Response-size limits are separate from filtering. Large results can be saved as files and read in smaller sections.</p></div><div><h3>Check what the result covers.</h3><p>Savings depend on the tool and its output. Hercules reports whether output was shortened and whether complete raw output is still available.</p><a className="text-link" href="https://github.com/0xMihirK/hercules-mcp#output-artifacts-sessions-and-workspaces">Read about filters and output limits <ArrowUpRight size={18}/></a></div></div>
  </section>;
}
