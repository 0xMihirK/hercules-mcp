import { useEffect, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { Unicode11Addon } from "@xterm/addon-unicode11";
import "@xterm/xterm/css/xterm.css";
import { ArrowsInSimple, ArrowsOutSimple, DownloadSimple, Pause, Play, ArrowCounterClockwise } from "@phosphor-icons/react";
import { parseRecording, RecordingCursor, RecordingWriter, ShuffleBag, recordingGeometry, mapMilestoneTime } from "../recording.js";
import { clients, type Client, type NativeManifest, type NativeRecording } from "../native-types";

const cache = new Map<string,ReturnType<typeof parseRecording>>();
const metricAsset = (base: string, file: string) => base + file;
export default function NativePlayer({ manifest, base, reduced, paused }: { manifest: NativeManifest | null; base: string; reduced: boolean; paused: boolean }) {
  const [client,setClient] = useState<Client>("claude"), [scenario,setScenario] = useState(""), [columns,setColumns] = useState(120), [replay,setReplay] = useState(0);
  const [explicitPause,setExplicitPause] = useState(false), [allowMotion,setAllowMotion] = useState(false), [expanded,setExpanded] = useState(false), [ready,setReady] = useState(false), [error,setError] = useState(""), [time,setTime] = useState(0), [rail,setRail] = useState("findings");
  const stage=useRef<HTMLDivElement>(null), viewport=useRef<HTMLDivElement>(null), host=useRef<HTMLDivElement>(null), openButton=useRef<HTMLButtonElement>(null), generation=useRef(0), bag=useRef<ShuffleBag<string> | null>(null), elapsed=useRef(0), previous=useRef<NativeRecording | null>(null), restart=useRef(true), visible=useRef(false);
  const flags=useRef({explicitPause,reduced,allowMotion,paused,expanded}); flags.current={explicitPause,reduced,allowMotion,paused,expanded};
  const retained=useRef<{terminal:Terminal;slot:HTMLDivElement}|null>(null);
  useEffect(()=>()=>{retained.current?.terminal.dispose();retained.current?.slot.remove();retained.current=null;},[]);
  const recording=manifest?.recordings.find(r=>r.client===client && r.scenario===scenario && r.columns===columns);
  const currentCase=manifest?.cases[scenario];
  useEffect(() => {
    if(!manifest || scenario) return;
    const ids=Object.keys(manifest.cases).filter(id=>!manifest.developmentOnly || manifest.recordings.some(r=>r.client==="claude" && r.scenario===id));
    if(!ids.length)return;
    bag.current=new ShuffleBag(ids);
    const available=manifest.recordings.find(r=>r.client==="claude");
    setScenario(manifest.developmentOnly && available ? available.scenario : bag.current.next());
  },[manifest,scenario]);
  useEffect(() => {
    if(!viewport.current || !stage.current) return;
    const observer=new ResizeObserver(([entry])=>setColumns(recordingGeometry(entry.contentRect.width)));
    observer.observe(viewport.current);
    const intersection=new IntersectionObserver(([entry])=>{visible.current=entry.isIntersecting;},{threshold:.03});intersection.observe(stage.current);
    return()=>{observer.disconnect();intersection.disconnect();};
  },[]);
  useEffect(() => {
    if(!expanded) return;
    const overflow=document.body.style.overflow;document.body.style.overflow="hidden";
    openButton.current?.focus();
    return()=>{document.body.style.overflow=overflow;openButton.current?.focus();};
  },[expanded]);
  useEffect(() => {
    const id=++generation.current, abort=new AbortController();
    let terminal:Terminal|undefined, slot:HTMLDivElement|undefined, writer:RecordingWriter|undefined, cursor:RecordingCursor|undefined, observer:ResizeObserver|undefined, frame=0, last:number|null=null, lastUpdate=0;
    const valid=()=>generation.current===id && !abort.signal.aborted;
    const resetClock=()=>{last=null;}; document.addEventListener("visibilitychange",resetClock);
    setReady(false);setError("");
    if(!manifest || !scenario)return()=>{abort.abort();document.removeEventListener("visibilitychange",resetClock);};
    if(!recording || !manifest?.realTools || manifest.scriptedToolResults) {
      retained.current?.terminal.dispose();retained.current?.slot.remove();retained.current=null;
      setError(manifest?.clients[client]?.unavailable || "This native recording is awaiting capture validation.");
      return()=>{abort.abort();document.removeEventListener("visibilitychange",resetClock);};
    }
    const metadata=recording;
    async function initialize(){
      try {
        await document.fonts.load('14px "IBM Plex Mono"');await document.fonts.ready;
        let source=cache.get(metadata.sha256);
        if(!source){
          const response=await fetch(base+metadata.file,{signal:abort.signal});if(!response.ok) throw Error("The recording could not be loaded. Replay to retry.");
          const bytes=await response.arrayBuffer();
          const digest=await crypto.subtle.digest("SHA-256",bytes);const hash=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,"0")).join("");
          if(hash!==metadata.sha256) throw Error("Recording integrity check failed. Replay to retry.");
          source=parseRecording(new TextDecoder().decode(bytes));cache.set(metadata.sha256,source);
        }
        if(!valid() || !host.current || !viewport.current) return;
        terminal=new Terminal({cols:metadata.columns,rows:metadata.rows,fontFamily:'"IBM Plex Mono", monospace',fontSize:14,lineHeight:1,letterSpacing:0,scrollback:0,convertEol:false,disableStdin:true,allowTransparency:false,allowProposedApi:true,cursorBlink:false,theme:{background:"#0a0a0a",foreground:"#eeeeee"}});
        const unicode=new Unicode11Addon();terminal.loadAddon(unicode);terminal.unicode.activeVersion="11";
        slot=document.createElement("div");slot.className="native-mount preparing";host.current.append(slot);terminal.open(slot);
        cursor=new RecordingCursor(source);writer=new RecordingWriter(cursor,(output:string,done:()=>void)=>terminal!.write(output,done));
        const target=reduced && !flags.current.allowMotion ? metadata.completedStillAt ?? Math.max(metadata.displayStart || 0,metadata.duration-1) : restart.current || !previous.current || previous.current.scenario!==metadata.scenario || previous.current.client!==metadata.client ? metadata.displayStart || 0 : mapMilestoneTime(elapsed.current,previous.current.chapters,metadata.chapters,metadata.duration,previous.current.duration);
        elapsed.current=target;restart.current=false;
        if(!await writer.seekTo(target) || !valid())return;
        const resize=()=>{
          if(!slot || !terminal || !viewport.current || !valid())return;
          const screen=terminal.element?.querySelector<HTMLElement>(".xterm-screen");const width=screen?.offsetWidth || metadata.columns*8.4, height=screen?.offsetHeight || metadata.rows*16.8;
          const limit=flags.current.expanded ? Math.max(180,innerHeight-245)/height : Infinity;
          const scale=Math.min(viewport.current.clientWidth/width,limit);
          slot.style.width=width+"px";slot.style.height=height+"px";slot.style.transform=`scale(${scale})`;
          viewport.current.style.height=Math.ceil(height*scale)+"px";
        };
        resize();observer=new ResizeObserver(resize);observer.observe(viewport.current);
        // A write callback confirms the VT buffer, not the DOM renderer. Wait for
        // xterm's render event and a painted frame before discarding the old view.
        // An offscreen terminal waits here until visible; cancellation releases it.
        const painted=await new Promise<boolean>(resolve=>{
          let paintFrame=0;
          const finish=(result:boolean)=>{subscription.dispose();cancelAnimationFrame(paintFrame);abort.signal.removeEventListener("abort",cancel);resolve(result);};
          const cancel=()=>finish(false);
          const subscription=terminal!.onRender(()=>{
            subscription.dispose();
            paintFrame=requestAnimationFrame(()=>{paintFrame=requestAnimationFrame(()=>finish(valid()));});
          });
          abort.signal.addEventListener("abort",cancel,{once:true});
          terminal!.refresh(0,metadata.rows-1);
        });
        if(!painted || !valid())return;
        resize();
        // Reconstruct offscreen, then swap atomically. The previous frame remains
        // visible during font loading, fetch and serialized reconstruction.
        retained.current?.terminal.dispose();retained.current?.slot.remove();
        retained.current={terminal,slot};slot.classList.remove("preparing");setReady(true);setTime(target);previous.current=metadata;
        const tick=(now:number)=>{
          if(!valid())return;
          const f=flags.current;const stopped=f.explicitPause || f.paused || (f.reduced && !f.allowMotion) || document.hidden || (!visible.current && !f.expanded);
          if(stopped)last=null;
          else {if(last!==null)elapsed.current=Math.min(source!.duration,elapsed.current+Math.min(.25,(now-last)/1000));last=now;writer!.writeAt(elapsed.current);}
          if(now-lastUpdate>120){setTime(elapsed.current);lastUpdate=now;}
          if(cursor!.finished && !writer!.pending && !stopped){restart.current=true;const next=bag.current!.next();if(next===scenario)setReplay(v=>v+1);else setScenario(next);return;}
          frame=requestAnimationFrame(tick);
        };frame=requestAnimationFrame(tick);
      }catch(error){
        if(valid()){
          terminal?.dispose();slot?.remove();
          setError(error instanceof Error && error.message.startsWith("Recording integrity") ? error.message : "The native recording could not be displayed. Select Replay to retry, or read the captured transcript.");
        }
      }
    }
    initialize();
    return()=>{abort.abort();cancelAnimationFrame(frame);observer?.disconnect();writer?.cancel();if(retained.current?.terminal!==terminal){terminal?.dispose();slot?.remove();}document.removeEventListener("visibilitychange",resetClock);};
  },[recording?.sha256,client,scenario,columns,replay,base,reduced]);
  const findings=recording?.synchronized.filter(item=>item.at<=time) || [];
  const reportReady=recording && time>=(recording.reportAvailableAt || recording.chapters.report || recording.duration);
  const availableFiles=recording?.artifacts.filter(a=>a.path.startsWith("artifacts/") && time>=(a.availableAt ?? recording.duration)) || [];
  const switchAgent=(next:Client)=>{if(next===client)return;restart.current=true;elapsed.current=0;setTime(0);setClient(next);};
  const togglePause=()=>{if(reduced && !allowMotion){restart.current=true;elapsed.current=0;setTime(0);setReplay(v=>v+1);setAllowMotion(true);setExplicitPause(false);}else setExplicitPause(v=>!v);};
  const replayCase=()=>{restart.current=true;elapsed.current=0;setTime(0);if(reduced)setAllowMotion(true);setReplay(v=>v+1);};
  const stopped=explicitPause || reduced && !allowMotion;
  return <div className="native-player" data-native-ready={ready} data-client={client} data-case={scenario} data-columns={columns} data-recording-sha={recording?.sha256}>
    <div className="agent-tabs" role="tablist" aria-label="Example agent">{clients.map(({id,name},i)=><button key={id} id={`agent-${id}`} aria-controls="native-session" role="tab" aria-selected={client===id} tabIndex={client===id?0:-1} onClick={()=>switchAgent(id)} onKeyDown={e=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(e.key)){e.preventDefault();const n=e.key==="Home"?0:e.key==="End"?3:(i+(e.key==="ArrowRight"?1:3))%4;switchAgent(clients[n].id);(e.currentTarget.parentElement?.children[n] as HTMLButtonElement)?.focus();}}}>{name}<span>{manifest?.clients[id]?.version || ""}</span></button>)}</div>
    <div className="player-layout">
      <div ref={stage} className={`native-stage${expanded?" is-expanded":""}`} role={expanded?"dialog":undefined} aria-modal={expanded?true:undefined} aria-label={expanded?`${clients.find(c=>c.id===client)?.name} recording`:undefined} onKeyDown={e=>{if(expanded && e.key==="Escape")setExpanded(false);if(expanded && e.key==="Tab"){const targets=stage.current?.querySelectorAll<HTMLElement>('button,a[href]');if(targets?.length){const first=targets[0],last=targets[targets.length-1];if(e.shiftKey && document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey && document.activeElement===last){e.preventDefault();first.focus();}}}}}>
        <div className="player-prompt"><span>Prompt</span><p>{currentCase?.prompt || "Loading validated local investigations…"}</p></div>
        <div ref={viewport} id="native-session" role="tabpanel" aria-labelledby={`agent-${client}`} className="native-viewport" style={{aspectRatio:`${columns*8.4}/${(columns===120?36:28)*19}`}}><div ref={host} className="native-host" />{!ready && (recording?.still || recording?.completedStill) && <img className="native-still" src={metricAsset(base,((error || reduced && !allowMotion) && recording.completedStill) || recording.still || recording.completedStill!)} alt={`Captured native ${client} interface`} />}{error && <div className="recording-error"><p>{error}</p>{recording?.transcript && <a href={base+recording.transcript}>Read the captured transcript</a>}</div>}{!ready && !error && <span className="recording-loading">Loading the captured native frame…</span>}</div>
        <div className="player-controls"><div><button aria-label={stopped?"Play recording":"Pause recording"} onClick={togglePause}>{stopped?<Play size={21}/>:<Pause size={21}/>}</button><button aria-label="Replay this case" onClick={replayCase}><ArrowCounterClockwise size={21}/></button><button ref={openButton} aria-label={expanded?"Close enlarged recording":"Enlarge recording"} onClick={()=>setExpanded(v=>!v)}>{expanded?<ArrowsInSimple size={21}/>:<ArrowsOutSimple size={21}/>}</button></div><span>{currentCase?.title} <span className="playback-speed">Recorded · 1×</span></span>{recording?.transcript && <a href={base+recording.transcript} download aria-label="Download recording transcript"><DownloadSimple size={20}/><span>Transcript</span></a>}</div>
        <progress aria-label="Recording progress" value={time} max={recording?.duration || 1}/>
      </div>
      <aside className="evidence-rail"><div className="rail-tabs" role="tablist" aria-label="Session evidence">{["findings","files","report"].map((tab,i)=><button key={tab} id={`evidence-${tab}`} role="tab" aria-controls="session-evidence" aria-selected={rail===tab} tabIndex={rail===tab?0:-1} onClick={()=>setRail(tab)} onKeyDown={e=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(e.key)){e.preventDefault();const tabs=["findings","files","report"],n=e.key==="Home"?0:e.key==="End"?2:(i+(e.key==="ArrowRight"?1:2))%3;setRail(tabs[n]);(e.currentTarget.parentElement?.children[n] as HTMLButtonElement)?.focus();}}}>{tab}</button>)}</div><div id="session-evidence" className="rail-content" role="tabpanel" aria-labelledby={`evidence-${rail}`}>
        {rail==="findings" && <><h3>{currentCase?.title || "Local lab investigation"}</h3><p className="rail-explanation">Actual result excerpts, synchronized to verified tool calls.</p>{findings.length?<ol className="findings-list">{findings.slice(-3).map(item=><li key={item.at}><code>{item.tool}</code><p className="observed-excerpt">{item.observation}</p></li>)}</ol>:<p>The native session will establish scope and explicitly start its runtime before investigating.</p>}</>}
        {rail==="files" && <><h3>Evidence files</h3><p>Actual workspace artifacts from this capture.</p>{availableFiles.length?<ul className="artifact-list">{availableFiles.map(a=><li key={a.file}><a href={base+a.file} download>{a.path}<span>{a.bytes.toLocaleString()} bytes</span></a></li>)}</ul>:<p className="pending-evidence">Files appear as their tool calls complete and their presence is verified.</p>}</>}
        {rail==="report" && <><h3>Report preview</h3>{reportReady?<><pre className="report-excerpt">{recording!.reportPreview}</pre><a className="text-link" href={base+recording!.reportHtml} target="_blank" rel="noreferrer">Open the actual HTML report</a><a className="text-link" href={base+recording!.report} download><DownloadSimple size={18}/>Download Markdown</a></>:<p>The report will appear after the native session has verified its evidence.</p>}</>}
      </div><div className="rail-summary"><span>{recording?`${recording.columns} × ${recording.rows} native cells`:"Native capture"}</span><p>Real tools · disposable local lab<br />Scripted model decisions</p></div></aside>
    </div>
  </div>;
}
