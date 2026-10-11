import { useEffect, useRef, useState } from "react";
import { ArrowsInSimple, ArrowsOutSimple, DownloadSimple, Pause, Play, ArrowCounterClockwise } from "@phosphor-icons/react";
import { ShuffleBag, recordingGeometry, mapMilestoneTime } from "../recording.js";
import { PlaybackClock,sessionEnd } from "../pixel-timeline.js";
import { PixelRenderer, verifiedFetch, type PixelIndex } from "../pixel-renderer";
import { clients, type Client, type NativeManifest, type NativeRecording } from "../native-types";
import CapturedPoster from "./CapturedPoster";

export default function NativePlayer({ manifest, base, reduced, paused }: { manifest: NativeManifest | null; base: string; reduced: boolean; paused: boolean }) {
  const [client,setClient]=useState<Client>("claude"),[scenario,setScenario]=useState(""),[columns,setColumns]=useState(120),[replay,setReplay]=useState(0);
  const [explicitPause,setExplicitPause]=useState(false),[allowMotion,setAllowMotion]=useState(false),[expanded,setExpanded]=useState(false),[ready,setReady]=useState(false),[error,setError]=useState(""),[time,setTime]=useState(0),[rail,setRail]=useState("findings");
  const [presentation,setPresentation]=useState<{width:number;height:number}|null>(null);
  const stage=useRef<HTMLDivElement>(null),viewport=useRef<HTMLDivElement>(null),host=useRef<HTMLDivElement>(null),openButton=useRef<HTMLButtonElement>(null),generation=useRef(0),bag=useRef<ShuffleBag<string>|null>(null),elapsed=useRef(0),previous=useRef<NativeRecording|null>(null),restart=useRef(true),visible=useRef(false);
  const flags=useRef({explicitPause,reduced,allowMotion,paused,expanded});flags.current={explicitPause,reduced,allowMotion,paused,expanded};
  const retained=useRef<HTMLCanvasElement|null>(null);
  const recording=manifest?.recordings.find(r=>r.client===client && r.scenario===scenario && r.columns===columns);
  const currentCase=manifest?.cases[scenario];
  useEffect(()=>{
    if(!manifest || scenario)return;
    const ids=Object.keys(manifest.cases).filter(id=>manifest.recordings.some(r=>r.scenario===id && r.pixels));
    if(!ids.length)return;
    bag.current=new ShuffleBag(ids);setScenario(bag.current.next());
  },[manifest,scenario]);
  useEffect(()=>{
    if(!viewport.current || !stage.current)return;
    const observer=new ResizeObserver(([entry])=>setColumns(recordingGeometry(entry.contentRect.width)));
    observer.observe(viewport.current);
    const intersection=new IntersectionObserver(([entry])=>{visible.current=entry.isIntersecting;},{threshold:.03});intersection.observe(stage.current);
    return()=>{observer.disconnect();intersection.disconnect();};
  },[]);
  useEffect(()=>{
    if(!expanded)return;
    const overflow=document.body.style.overflow;document.body.style.overflow="hidden";openButton.current?.focus();
    return()=>{document.body.style.overflow=overflow;openButton.current?.focus();};
  },[expanded]);
  useEffect(()=>{
    const id=++generation.current,abort=new AbortController();
    let renderer:PixelRenderer|undefined,frame=0,canvas:HTMLCanvasElement|undefined,lastUpdate=0;
    const valid=()=>generation.current===id && !abort.signal.aborted;
    const clock=new PlaybackClock(elapsed.current);
    const suspend=()=>clock.suspend();document.addEventListener("visibilitychange",suspend);
    setReady(false);setError("");
    if(!manifest)return()=>{abort.abort();document.removeEventListener("visibilitychange",suspend);};
    if(manifest.schemaVersion!==3 || !recording?.pixels || !manifest.realTools || manifest.scriptedToolResults){
      setError(manifest.clients[client]?.unavailable || "Independent native pixel capture is awaiting fidelity validation.");
      return()=>{abort.abort();document.removeEventListener("visibilitychange",suspend);};
    }
    const metadata=recording,pixels=recording.pixels;
    async function initialize(){
      try{
        const bytes=await verifiedFetch(base+pixels!.index,pixels!.indexSha256,abort.signal);
        const source:PixelIndex=JSON.parse(new TextDecoder().decode(bytes));
        const end=sessionEnd(source.duration,metadata.chapters.report);
        if(source.schemaVersion!==3 || source.width!==pixels!.width || source.height!==pixels!.height || source.fps!==60)throw Error("Invalid native pixel capture profile");
        if(!valid() || !host.current)return;
        renderer=new PixelRenderer(source,new URL(".",new URL(base+pixels!.index,location.href)).href,abort.signal);
        await renderer.prepare();if(!valid())return;
        canvas=document.createElement("canvas");canvas.className="native-canvas";canvas.setAttribute("role","img");canvas.setAttribute("aria-label","Actual captured "+client+" terminal. Transcript available below.");
        const target=reduced && !flags.current.allowMotion ? metadata.completedStillAt ?? metadata.duration-1 : restart.current || !previous.current || previous.current.scenario!==metadata.scenario || previous.current.client!==metadata.client ? metadata.displayStart || 0 : mapMilestoneTime(elapsed.current,previous.current.chapters,metadata.chapters,metadata.duration,previous.current.duration);
        if(!await renderer.paint(target,canvas) || !valid())return;
        // Only a decoded complete native frame replaces the previous display.
        retained.current?.remove();host.current.replaceChildren(canvas);retained.current=canvas;
        setPresentation({width:source.width,height:source.height});setReady(true);setTime(target);
        elapsed.current=clock.time=target;restart.current=false;previous.current=metadata;
        const tick=async(now:number)=>{
          if(!valid())return;
          const f=flags.current,stopped=f.explicitPause || f.paused || (f.reduced && !f.allowMotion) || document.hidden || (!visible.current && !f.expanded);
          elapsed.current=clock.tick(now,stopped,end);
          if(!await renderer!.paint(elapsed.current,canvas!) || !valid())return;
          if(now-lastUpdate>100){setTime(elapsed.current);lastUpdate=now;}
          if(elapsed.current>=end && !stopped){restart.current=true;elapsed.current=0;setTime(0);const next=bag.current?.next();if(next===scenario)setReplay(v=>v+1);else if(next)setScenario(next);return;}
          frame=requestAnimationFrame(next=>{tick(next).catch(fail);});
        };
        frame=requestAnimationFrame(next=>{tick(next).catch(fail);});
      }catch(cause){fail(cause);}
    }
    function fail(cause:unknown){
      if(valid()){
        setError(cause instanceof Error && cause.message.includes("integrity")?cause.message:"The captured terminal pixels could not load. Replay to retry, or read the transcript.");clock.suspend();
        // A cold renderer failure falls back to this capture's completed still.
        // Keep its evidence synchronized; retained playback keeps its own time.
        if(!retained.current){const at=metadata.completedStillAt ?? metadata.duration;elapsed.current=at;setTime(at);}
      }
    }
    initialize();
    return()=>{abort.abort();cancelAnimationFrame(frame);renderer?.dispose();document.removeEventListener("visibilitychange",suspend);};
  },[recording?.pixels?.indexSha256,client,scenario,columns,replay,base,reduced]);
  const findings=recording?.synchronized.filter(item=>item.at<=time && (!item.phase || item.phase==="investigation")) || [];
  const reportReady=recording && time>=(recording.reportAvailableAt || recording.chapters.report || recording.duration);
  const availableFiles=recording?.artifacts.filter(a=>(!a.path.startsWith("challenge/") || scenario==="forensics") && (!a.path.startsWith("reports/") || a.path==="reports/evidence-index.json") && time>=(a.availableAt ?? recording.duration)) || [];
  const switchAgent=(next:Client)=>{if(next===client)return;restart.current=true;elapsed.current=0;setTime(0);setClient(next);};
  const togglePause=()=>{if(reduced && !allowMotion){restart.current=true;elapsed.current=0;setTime(0);setReplay(v=>v+1);setAllowMotion(true);setExplicitPause(false);}else setExplicitPause(v=>!v);};
  const replayCase=()=>{restart.current=true;elapsed.current=0;setTime(0);if(reduced)setAllowMotion(true);setReplay(v=>v+1);};
  const stopped=paused || explicitPause || reduced && !allowMotion;
  const hasPresentation=Boolean(presentation || recording?.pixels);
  return <div className="native-player" data-native-ready={ready} data-client={client} data-case={scenario} data-columns={columns} data-recording-sha={recording?.sha256}>
    <div className="agent-tabs" role="tablist" aria-label="Example agent">{clients.map(({id,name},i)=><button key={id} id={`agent-${id}`} aria-controls="native-session" role="tab" aria-selected={client===id} tabIndex={client===id?0:-1} onClick={()=>switchAgent(id)} onKeyDown={e=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(e.key)){e.preventDefault();const n=e.key==="Home"?0:e.key==="End"?3:(i+(e.key==="ArrowRight"?1:3))%4;switchAgent(clients[n].id);(e.currentTarget.parentElement?.children[n] as HTMLButtonElement)?.focus();}}}>{name}<span>{manifest?.clients[id]?.version || ""}</span></button>)}</div>
    <div className="player-layout">
      <div ref={stage} className={`native-stage${expanded?" is-expanded":""}`} role={expanded?"dialog":undefined} aria-modal={expanded?true:undefined} aria-label={expanded?`${clients.find(c=>c.id===client)?.name} recording`:undefined} onKeyDown={e=>{if(expanded && e.key==="Escape")setExpanded(false);if(expanded && e.key==="Tab"){const targets=stage.current?.querySelectorAll<HTMLElement>('button:not(:disabled),a[href]');if(targets?.length){const first=targets[0],last=targets[targets.length-1];if(e.shiftKey && document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey && document.activeElement===last){e.preventDefault();first.focus();}}}}}>
        <div className="player-prompt"><span>Prompt</span><p>{currentCase?.prompt || "Loading validated local investigations…"}</p></div>
        <div ref={viewport} id="native-session" role="tabpanel" aria-labelledby={`agent-${client}`} aria-busy={!ready && !error} className={`native-viewport${hasPresentation?"":" is-unavailable"}`} style={{aspectRatio:presentation?presentation.width+"/"+presentation.height:recording?.pixels?recording.pixels.width+"/"+recording.pixels.height:undefined}}><div ref={host} className="native-host" />{!ready && !retained.current && recording && <CapturedPoster base={base} opening={recording.still && recording.stillSha256?{file:recording.still,sha256:recording.stillSha256}:undefined} completed={recording.completedStill && recording.completedStillSha256?{file:recording.completedStill,sha256:recording.completedStillSha256}:undefined} preferCompleted={Boolean(error || reduced && !allowMotion)} label={`Captured native ${client} interface`}/>} {error && <div className="recording-error" role="alert"><p>{error}</p>{recording?.transcript && <a href={base+recording.transcript}>Read the captured transcript</a>}</div>}{!ready && !error && <span className="recording-loading" role="status">Loading the {clients.find(c=>c.id===client)?.name} recording…</span>}</div>
        <div className="player-controls"><div><button disabled={paused} title={paused?"Resume site motion to play this recording":undefined} aria-label={paused?"Recording paused with site motion":stopped?"Play recording":"Pause recording"} onClick={togglePause}>{stopped?<Play size={21}/>:<Pause size={21}/>}</button><button aria-label="Replay this case" onClick={replayCase}><ArrowCounterClockwise size={21}/></button><button ref={openButton} aria-label={expanded?"Close enlarged recording":"Enlarge recording"} onClick={()=>setExpanded(v=>!v)}>{expanded?<ArrowsInSimple size={21}/>:<ArrowsOutSimple size={21}/>}</button></div><span>{currentCase?.title} <span className="playback-speed">Recorded · 1×</span></span>{recording?.transcript && <a href={base+recording.transcript} download aria-label="Download recording transcript"><DownloadSimple size={20}/><span>Transcript</span></a>}</div>
        <progress aria-label="Recording progress" value={time} max={sessionEnd(recording?.duration || 1,recording?.chapters.report)}/>
      </div>
      <aside className="evidence-rail"><div className="rail-tabs" role="tablist" aria-label="Session evidence">{["findings","files","report"].map((tab,i)=><button key={tab} id={`evidence-${tab}`} role="tab" aria-controls="session-evidence" aria-selected={rail===tab} tabIndex={rail===tab?0:-1} onClick={()=>setRail(tab)} onKeyDown={e=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(e.key)){e.preventDefault();const tabs=["findings","files","report"],n=e.key==="Home"?0:e.key==="End"?2:(i+(e.key==="ArrowRight"?1:2))%3;setRail(tabs[n]);(e.currentTarget.parentElement?.children[n] as HTMLButtonElement)?.focus();}}}>{tab}</button>)}</div><div id="session-evidence" className="rail-content" role="tabpanel" aria-labelledby={`evidence-${rail}`}>
        {rail==="findings" && <><h3>{currentCase?.title || "Local lab investigation"}</h3><p className="rail-explanation">Actual result excerpts, synchronized to verified tool calls.</p>{findings.length?<ol className="findings-list">{findings.slice(-3).map(item=><li key={item.at}><code>{item.tool}</code><p className="observed-excerpt">{item.observation}</p></li>)}</ol>:<p>The native session will establish scope and explicitly start its runtime before investigating.</p>}</>}
        {rail==="files" && <><h3>Evidence files</h3>{recording && <div><a className="text-link" href={base+(recording.rawAnsi || recording.file)} download>Download untouched ANSI output</a><a className="text-link" href={base+(recording.recordingArchive?.file || recording.file)} download>Download timestamped recording{recording.recordingArchive ? " (.zip)" : ""}</a></div>}<p>Actual workspace artifacts from this capture.</p>{availableFiles.length?<ul className="artifact-list">{availableFiles.map(a=><li key={a.file}><a href={base+a.file} download={a.path.split("/").at(-1)}>{a.path}<span>{a.bytes.toLocaleString()} bytes</span></a></li>)}</ul>:<p className="pending-evidence">Files appear as their tool calls complete and their presence is verified.</p>}</>}
        {rail==="report" && <><h3>Report preview</h3>{reportReady?<><pre className="report-excerpt">{recording!.reportPreview}</pre><a className="text-link" href={base+recording!.reportHtml} target="_blank" rel="noreferrer">Open the actual HTML report</a><a className="text-link" href={base+recording!.report} download><DownloadSimple size={18}/>Download Markdown</a></>:<p>The report will appear after the native session has verified its evidence.</p>}</>}
      </div><div className="rail-summary"><span>{recording?`${recording.columns} × ${recording.rows} native cells`:"Native capture"}</span><p>Real tools · disposable local lab<br />Scripted model decisions</p></div></aside>
    </div>
  </div>;
}
