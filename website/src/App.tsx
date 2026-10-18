import { useEffect, useState } from "react";
import { ArrowDown } from "@phosphor-icons/react/ArrowDown";
import { Pause } from "@phosphor-icons/react/Pause";
import { Play } from "@phosphor-icons/react/Play";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useReducedMotion } from "./lib/use-reduced-motion";
import Background from "./components/Background";
import NativePlayer from "./components/NativePlayer";
import ToolChains from "./components/ToolChains";
import ArchitectureScene from "./components/ArchitectureScene";
import EvidencePipeline from "./components/EvidencePipeline";
import Setup from "./components/Setup";
import facts from "./site-facts.json";
import bootstrap from "./bootstrap.json";
import type { NativeManifest } from "./native-types";

const github="https://github.com/0xMihirK/hercules-mcp";
const asset=(name:string)=>`${import.meta.env.BASE_URL}assets/${name}`;
export default function App(){
  const reduced=useReducedMotion(),[paused,setPaused]=useState(false);
  const [manifest,setManifest]=useState<NativeManifest|null>(bootstrap.schemaVersion===3 ? bootstrap as unknown as NativeManifest : null);
  const recordingBase=asset(`${bootstrap.assetDirectory}/`);
  useEffect(()=>{
    let frame=0,live=true;
    const refresh=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{if(live)ScrollTrigger.refresh();});};
    // Native geometries and expanded chains change the sections preceding
    // the pinned scene. Refresh its measured positions after those changes.
    const observer=new ResizeObserver(refresh);
    for(const element of document.querySelectorAll("#agents,#tools"))observer.observe(element);
    document.fonts.ready.then(()=>{if(live)refresh();});
    return()=>{live=false;observer.disconnect();cancelAnimationFrame(frame);};
  },[]);
  useEffect(()=>{
    if(typeof fetch!=="function")return;
    const controller=new AbortController();
    fetch(recordingBase+"manifest.json",{signal:controller.signal,cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Native manifest unavailable");return r.json();}).then(data=>{if(data.schemaVersion===3 && data.realTools && !data.scriptedToolResults)setManifest(data);}).catch(()=>{});
    return()=>controller.abort();
  },[recordingBase]);
  return <div className={`site${paused || reduced?" motion-off":""}`}>
    <Background paused={paused} reduced={reduced}/><div className="background-scrim"/>
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="site-header wrap">
      <a href="#main" className="brand"><img src={asset("lion.svg")} width="30" height="30" alt=""/>hercules<span>/ mcp</span></a>
      <nav aria-label="Main"><a href="#agents">Agents</a><a href="#tools">Capabilities</a><a href="#architecture">How it works</a><a href="#evidence">Evidence</a><a href="#install">Setup</a></nav>
      <div className="header-actions">
        <button className="motion-control" aria-pressed={paused} aria-label={paused?"Resume page motion":"Pause page motion"} onClick={()=>setPaused(value=>!value)}>{paused?<Play size={16} aria-hidden="true"/>:<Pause size={16} aria-hidden="true"/>}<span>{paused?"Resume motion":"Pause motion"}</span></button>
        <a className="header-github" href={github}>GitHub <ArrowUpRight size={16} aria-hidden="true"/></a>
      </div>
    </header>
    <main id="main">
      <section className="hero wrap" aria-labelledby="hero-title">
        <div className="hero-top">
          <div className="hero-copy">
            <h1 id="hero-title">A Kali workspace<br/>for your <em>AI agent.</em></h1>
            <p className="hero-lede">Connect terminal-capable agents to {facts.catalog.full_tool_count} structured offensive-security tools, CloakBrowser automation, and Metasploit RPC inside an explicitly started, session-owned Kali Docker container—with bounded inline output and retained host workspace evidence.</p>
          </div>
          <div className="hero-actions">
            <a className="button primary" href="#install">Install with your agent <ArrowUpRight size={18} aria-hidden="true"/></a>
            <a className="button secondary" href={github}>Explore the source <ArrowUpRight size={18} aria-hidden="true"/></a>
          </div>
        </div>
        <dl className="hero-telemetry" aria-label="Hercules MCP architecture summary">
          <div><dd><strong>{facts.catalog.full_tool_count}</strong><span>{facts.catalog.without_metasploit_tool_count} with SKIP_METASPLOIT</span></dd><dt>Registered MCP tools</dt></div>
          <div><dd><strong>{facts.catalog.capabilities.length}</strong><span>Across {facts.catalog.categories.length} security domains</span></dd><dt>Capability bundles</dt></div>
          <div><dd><strong>{facts.catalog.resource_count}</strong><span>NSE, Nuclei, PEAS, GTFOBins, LOLBAS</span></dd><dt>Agent resources</dt></div>
          <div><dd><strong>120</strong><span>4 native clients · 10 investigations</span></dd><dt>Validated lab sessions</dt></div>
        </dl>
      </section>
      <section id="agents" className="agents-section wrap" aria-labelledby="agents-title"><div className="agent-heading"><div><h2 id="agents-title">Hercules works with your agent.</h2><p className="recording-provenance">Native UI recordings · real tool execution · scripted model prompts</p></div><p>Connect any agent, worker, or custom integration that supports STDIO MCP. Run Hercules on Windows, macOS, or Linux with Docker. Switch clients or pick any of the ten local-lab investigations below.</p></div><NativePlayer manifest={manifest} base={recordingBase} reduced={reduced} paused={paused}/><div className="session-note"><p>Tools execute in disposable local Docker labs and return real results. Model responses and decisions are scripted. No public targets are contacted.</p><a href="#tools">Explore the capabilities <ArrowDown size={18} aria-hidden="true"/></a></div></section>
      <ToolChains catalog={facts.catalog} reduced={reduced} paused={paused}/>
      <ArchitectureScene reduced={reduced} paused={paused}/>
      <EvidencePipeline reduced={reduced} paused={paused}/>
      <Setup prompt={facts.installationPrompt}/>
    </main>
    <footer className="site-footer wrap"><a href="#main" className="brand"><img src={asset("lion.svg")} width="26" height="26" alt=""/>hercules<span>/ mcp</span></a><p>Built for authorized security testing.</p><div><a href={github}>Source <ArrowUpRight size={16}/></a><a href={`${github}/blob/main/website/CAPTURE.md`}>About the recordings <ArrowUpRight size={16}/></a><a href={`${github}/blob/main/LICENSE`}>License <ArrowUpRight size={16}/></a></div></footer>
  </div>;
}
