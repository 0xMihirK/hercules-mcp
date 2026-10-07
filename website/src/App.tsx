import { useEffect, useState } from "react";
import { ArrowDown, ArrowUpRight, Pause, Play } from "@phosphor-icons/react";
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
  const [manifest,setManifest]=useState<NativeManifest|null>(bootstrap.schemaVersion===2 ? bootstrap as unknown as NativeManifest : null);
  const recordingBase=asset(`${bootstrap.assetDirectory}/`);
  const measuredRecording=manifest?.recordings.find(r=>r.scenario==="services" && r.client==="claude" && r.columns===120);
  const measured=measuredRecording?.metrics.find(m=>m.tool==="searchsploit" && m.rawCharacters>0);
  const measurement=measured ? {...measured,caseTitle:manifest?.cases.services.title,file:measuredRecording?.artifacts.find(a=>a.path===measured.rawArtifact)?.file} : null;
  useEffect(()=>{
    if(typeof fetch!=="function")return;
    const controller=new AbortController();
    fetch(recordingBase+"manifest.json",{signal:controller.signal}).then(r=>{if(!r.ok)throw Error("Native manifest unavailable");return r.json();}).then(data=>{if(data.schemaVersion===2 && data.realTools && !data.scriptedToolResults)setManifest(data);}).catch(()=>{});
    return()=>controller.abort();
  },[recordingBase]);
  return <div className={`site${paused || reduced?" motion-off":""}`}>
    <Background paused={paused} reduced={reduced}/><div className="background-scrim"/>
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="site-header wrap"><a href="#main" className="brand"><img src={asset("lion.png")} width="30" height="30" alt=""/>hercules<span>/ mcp</span></a><nav aria-label="Main"><a href="#agents">Agents</a><a href="#tools">Tool chains</a><a href="#architecture">Architecture</a><a href="#install">Setup</a></nav><a className="header-github" href={github}>GitHub <ArrowUpRight size={16} aria-hidden="true"/></a></header>
    <main id="main">
      <section className="hero wrap" aria-labelledby="hero-title"><h1 id="hero-title">A Kali workspace<br/>for your <em>AI agent.</em></h1><div className="hero-description"><p>Connect your agent to real security tools.<br/>Keep the runtime explicit.<br/>Keep the evidence yours.</p><div className="hero-actions"><a className="button primary" href="#install">Install with your agent <ArrowUpRight size={18} aria-hidden="true"/></a><a className="button secondary" href={github}>Explore the source <ArrowUpRight size={18} aria-hidden="true"/></a></div></div></section>
      <section id="agents" className="agents-section wrap" aria-labelledby="agents-title"><div className="agent-heading"><div><h2 id="agents-title">Hercules works with your agent.</h2><p className="recording-provenance">Native UI recordings · scripted examples</p></div><p>Connect any agent, worker, or custom integration that supports STDIO MCP. Run Hercules on Windows, macOS, or Linux with Docker. These four clients are examples.</p></div><NativePlayer manifest={manifest} base={recordingBase} reduced={reduced} paused={paused}/><div className="session-note"><p>Real Hercules tools execute in disposable local labs. Model responses and investigation decisions are scripted. No public targets are contacted.</p><a href="#tools">Follow the tool chains <ArrowDown size={18} aria-hidden="true"/></a></div></section>
      <ToolChains catalog={facts.catalog}/>
      <ArchitectureScene reduced={reduced} paused={paused}/>
      <EvidencePipeline reduced={reduced} paused={paused} measurement={measurement} base={recordingBase}/>
      <Setup prompt={facts.installationPrompt}/>
    </main>
    <footer className="site-footer wrap"><a href="#main" className="brand"><img src={asset("lion.png")} width="26" height="26" alt=""/>hercules<span>/ mcp</span></a><p>Run with permission. Keep the evidence.</p><div><a href={github}>Source <ArrowUpRight size={16}/></a><a href={`${github}/blob/main/website/CAPTURE.md`}>Recording provenance</a><a href={`${github}/blob/main/LICENSE`}>License</a></div></footer>
    <button className="motion-control" aria-label={paused?"Resume site motion":"Pause site motion"} aria-pressed={paused} onClick={()=>setPaused(v=>!v)}>{paused?<Play size={18} aria-hidden="true"/>:<Pause size={18} aria-hidden="true"/>}<span>{paused?"Resume site motion":"Pause site motion"}</span></button>
  </div>;
}
