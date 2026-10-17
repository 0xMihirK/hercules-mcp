import { useEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { ArrowsInSimple } from "@phosphor-icons/react/ArrowsInSimple";
import { ArrowsOutSimple } from "@phosphor-icons/react/ArrowsOutSimple";
import { Pause } from "@phosphor-icons/react/Pause";
import { Play } from "@phosphor-icons/react/Play";
import { ArrowCounterClockwise } from "@phosphor-icons/react/ArrowCounterClockwise";
import { ShuffleBag, recordingGeometry, mapMilestoneTime } from "../recording.js";
import { PlaybackClock, sessionEnd, PLAYBACK_RATE } from "../pixel-timeline.js";
import { PixelRenderer, verifiedFetch, type PixelIndex } from "../pixel-renderer";
import { clients, type Client, type NativeManifest, type NativeRecording } from "../native-types";
import CapturedPoster from "./CapturedPoster";
import SessionStory, {stories} from "./SessionStory";
import SessionTranscript from "./SessionTranscript";

type Recording=NativeManifest["recordings"][number];
type Runtime={renderer:PixelRenderer|null;canvas:HTMLCanvasElement;clock:PlaybackClock;end:number;maximum:number;minimum:number;seek:number|null;record:Recording};
const key=(r:NativeRecording)=>r.client+"/"+r.scenario+"/"+r.columns;
export default function NativePlayer({manifest,base,reduced,paused}:{manifest:NativeManifest|null;base:string;reduced:boolean;paused:boolean}){
  const [client,setClient]=useState<Client>("claude"),[scenario,setScenario]=useState(""),[columns,setColumns]=useState<number|null>(null),[replay,setReplay]=useState(0);
  const [explicitPause,setExplicitPause]=useState(false),[allowMotion,setAllowMotion]=useState(false),[expanded,setExpanded]=useState(false);
  const [committed,setCommitted]=useState<Recording|null>(null),[ready,setReady]=useState(false),[fallback,setFallback]=useState(false),[loading,setLoading]=useState(false),[buffering,setBuffering]=useState(false),[error,setError]=useState(""),[time,setTime]=useState(0),[maximum,setMaximum]=useState(0);
  const stage=useRef<HTMLDivElement>(null),viewport=useRef<HTMLDivElement>(null),host=useRef<HTMLDivElement>(null),openButton=useRef<HTMLButtonElement>(null);
  const generation=useRef(0),bag=useRef<ShuffleBag<string>|null>(null),visible=useRef(false),runtime=useRef<Runtime|null>(null),retained=useRef<HTMLCanvasElement|null>(null),restart=useRef(true),initialSeek=useRef<number|null>(null);
  const flags=useRef({explicitPause,allowMotion,reduced,paused,expanded});flags.current={explicitPause,allowMotion,reduced,paused,expanded};
  const requested=manifest?.recordings.find(r=>r.client===client && r.scenario===scenario && r.columns===columns);
  const shown=manifest?.recordings.find(r=>committed && key(r)===key(committed)) || committed;
  const currentCase=manifest?.cases[shown?.scenario || ""],shownClient=shown?.client || client;
  const seek=(next:number)=>{
    const r=runtime.current;if(!r)return;
    r.seek=Math.max(r.minimum,Math.min(r.maximum,next));r.clock.suspend();setExplicitPause(true);if(!r.renderer){initialSeek.current=r.seek;restart.current=false;setAllowMotion(true);}
  };
  const seekRef=useRef(seek);seekRef.current=seek;
  useEffect(()=>{
    if(!manifest || scenario)return;
    const ids=Object.keys(manifest.cases).filter(id=>manifest.recordings.some(r=>r.scenario===id && r.pixels));
    if(ids.length){bag.current=new ShuffleBag(ids);setScenario(bag.current.next());}
  },[manifest,scenario]);
  useEffect(()=>{
    if(!stage.current)return;
    let timer:ReturnType<typeof setTimeout>;
    const resize=new ResizeObserver(()=>{
      if(flags.current.expanded)return;
      clearTimeout(timer);timer=setTimeout(()=>{if(!flags.current.expanded)setColumns(recordingGeometry(stage.current!.getBoundingClientRect().width));},150);
    });resize.observe(stage.current);
    const intersection=new IntersectionObserver(([entry])=>{visible.current=entry.isIntersecting;},{threshold:.03});intersection.observe(stage.current);
    return()=>{clearTimeout(timer);resize.disconnect();intersection.disconnect();};
  },[]);
  useEffect(()=>{
    if(!expanded)return;
    const overflow=document.body.style.overflow;document.body.style.overflow="hidden";openButton.current?.focus();
    return()=>{document.body.style.overflow=overflow;openButton.current?.focus();};
  },[expanded]);
  useEffect(()=>{
    const element=viewport.current;if(!element)return;let touchY=0;
    const wheel=(event:WheelEvent)=>{
      const r=runtime.current;if(!r || Math.abs(event.deltaY)<Math.abs(event.deltaX))return;
      const current=r.seek ?? r.clock.time,unit=event.deltaMode===1?18:event.deltaMode===2?element.clientHeight:1;
      const next=Math.max(r.minimum,Math.min(r.maximum,current+event.deltaY*unit/12));
      if(next===current)return;
      event.preventDefault();seekRef.current(next);
    };
    const start=(event:TouchEvent)=>{touchY=event.touches[0]?.clientY || 0;};
    const move=(event:TouchEvent)=>{
      if(!flags.current.explicitPause || !runtime.current)return;
      const y=event.touches[0]?.clientY ?? touchY,delta=touchY-y;touchY=y;
      const r=runtime.current,current=r.seek ?? r.clock.time,next=Math.max(r.minimum,Math.min(r.maximum,current+delta/8));
      if(next===current)return;
      event.preventDefault();seekRef.current(next);
    };
    element.addEventListener("wheel",wheel,{passive:false});element.addEventListener("touchstart",start,{passive:true});element.addEventListener("touchmove",move,{passive:false});
    return()=>{element.removeEventListener("wheel",wheel);element.removeEventListener("touchstart",start);element.removeEventListener("touchmove",move);};
  },[]);
  useEffect(()=>{
    if(!requested?.pixels || !manifest || !columns)return;
    const id=++generation.current,abort=new AbortController(),record=requested,source=record.pixels!,previous=runtime.current;
    let renderer:PixelRenderer|null=null,frame=0,canvas:HTMLCanvasElement|null=null,transition:Animation|undefined,lastUpdate=0;
    const valid=()=>generation.current===id && !abort.signal.aborted;
    const clock=new PlaybackClock(0,PLAYBACK_RATE);
    let minimum=record.displayStart || 0;
    let target=initialSeek.current ?? (reduced && !allowMotion ? record.completedStillAt ?? record.duration-1 : !restart.current && previous && previous.record.client===record.client && previous.record.scenario===record.scenario ? mapMilestoneTime(previous.clock.time,previous.record.chapters,record.chapters,record.duration,previous.record.duration) : minimum);
    const end=sessionEnd(record.duration,record.chapters.report);
    const stopped=()=>{const f=flags.current;return f.explicitPause || f.paused || f.reduced && !f.allowMotion || document.hidden || !visible.current && !f.expanded;};
    setLoading(true);setBuffering(false);setError("");
    const suspend=()=>clock.suspend();document.addEventListener("visibilitychange",suspend);
    function commit(){
      if(!valid() || !canvas || !host.current)return;
      const outgoing=retained.current;
      if(outgoing && !flags.current.reduced && !flags.current.paused){
        outgoing.setAttribute("aria-hidden","true");host.current.replaceChildren(outgoing,canvas);
        transition=canvas.animate([{opacity:0},{opacity:1}],{duration:200,easing:"cubic-bezier(.16,1,.3,1)"});
        transition.finished.then(()=>outgoing.remove()).catch(()=>{});
      }else host.current.replaceChildren(canvas);
      retained.current=canvas;clock.time=target;clock.suspend();
      const known=!restart.current && previous && previous.record.client===record.client && previous.record.scenario===record.scenario ? mapMilestoneTime(previous.maximum,previous.record.chapters,record.chapters,record.duration,previous.record.duration) : target;
      runtime.current={renderer,canvas,clock,end,minimum,maximum:Math.max(target,Math.min(end,known)),seek:null,record};
      initialSeek.current=null;flushSync(()=>{setCommitted(record);setTime(target);setMaximum(runtime.current!.maximum);setReady(true);setLoading(false);setFallback(false);});restart.current=false;
      canvas.dataset.commitLatencyMs=String(performance.now()-requestedAt);
    }
    const requestedAt=performance.now();
    async function poster(file:string,sha:string){
      const bytes=await verifiedFetch(base+file,sha,abort.signal);
      const bitmap=await createImageBitmap(new Blob([bytes],{type:"image/png"}),{colorSpaceConversion:"none"});
      if(!valid()){bitmap.close();return;}
      canvas=document.createElement("canvas");canvas.className="native-canvas";canvas.width=source.width;canvas.height=source.height;
      canvas.setAttribute("role","img");canvas.setAttribute("aria-label","Actual captured "+record.client+" terminal");
      try{const context=canvas.getContext("2d",{alpha:false});if(!context)throw Error("Canvas2D unavailable");context.drawImage(bitmap,0,0);}finally{bitmap.close();}
    }
    // Warming these small static assets does not advance a paused recording.
    async function warmEntrances(completed=false){
      for(const other of manifest!.recordings.filter(r=>r.scenario===record.scenario && r.columns===record.columns && r.client!==record.client)){
        if(!valid())return;
        try{
          if(completed && other.completedStill && other.completedStillSha256){await verifiedFetch(base+other.completedStill,other.completedStillSha256,abort.signal);continue;}
          let intro:{file:string;sha256:string}|undefined;
          if(other.pixels){const bytes=await verifiedFetch(base+other.pixels.index,other.pixels.indexSha256,abort.signal);if(other.client==="hermes")intro=JSON.parse(new TextDecoder().decode(bytes)).reviewFrames?.nativeIntro;}
          if(intro && other.pixels)await verifiedFetch(base+other.pixels.index.replace(/[^/]+$/,intro.file),intro.sha256,abort.signal);
          else if(other.still && other.stillSha256)await verifiedFetch(base+other.still,other.stillSha256,abort.signal);
        }catch{return;}
      }
    }
    async function initialize(){
      try{
        if(!manifest!.realTools || manifest!.scriptedToolResults)throw Error("A validated native recording is unavailable.");
        const staticView=reduced && !allowMotion;
        const opening=target===minimum;
        if(staticView && record.completedStill && record.completedStillSha256){
          await poster(record.completedStill,record.completedStillSha256);if(!valid())return;commit();void warmEntrances(true);return;
        }
        const bytes=await verifiedFetch(base+source.index,source.indexSha256,abort.signal);
        const index:PixelIndex=JSON.parse(new TextDecoder().decode(bytes));
        if(index.schemaVersion!==3 || index.width!==source.width || index.height!==source.height || index.fps!==60)throw Error("Invalid capture profile");
        if(!valid())return;
        // Hermes' verified entrance retains its complete native title. Later
        // startup screens can naturally scroll the tall banner out of view.
        const intro=record.client==="hermes"?index.reviewFrames?.nativeIntro:undefined;
        if(intro){minimum=Math.max(minimum,intro.at);target=opening?minimum:Math.max(minimum,target);}
        if(opening){
          const file=intro?source.index.replace(/[^/]+$/,intro.file):record.still;
          const sha=intro?.sha256 || record.stillSha256;
          if(file && sha)try{await poster(file,sha);if(!valid())return;commit();void warmEntrances();}catch{if(!valid())return;}
        }
        renderer=new PixelRenderer(index,new URL(".",new URL(base+source.index,location.href)).href,abort.signal);
        if(!canvas){canvas=document.createElement("canvas");canvas.className="native-canvas";canvas.setAttribute("role","img");canvas.setAttribute("aria-label","Actual captured "+record.client+" terminal");}
        await renderer.paint(target,canvas);if(!valid())return;
        if(!opening || !retained.current || retained.current!==canvas)commit();
        if(runtime.current?.canvas===canvas)runtime.current.renderer=renderer;
        if(!stopped()){setBuffering(true);await renderer.prepare(target,5);if(!valid())return;setBuffering(false);}
        const tick=async(now:number)=>{
          if(!valid() || !runtime.current)return;
          const r=runtime.current;
          if(r.seek!==null){
            const next=r.seek;r.seek=null;clock.suspend();setBuffering(true);
            await renderer!.paint(next,canvas!);if(!valid())return;
            clock.time=next;setTime(next);setBuffering(false);
          }else if(!stopped()){
            if(!renderer!.hasBuffer(clock.time,Math.min(end,clock.time+5))){
              clock.suspend();setBuffering(true);await renderer!.prepare(clock.time,5);if(!valid())return;setBuffering(false);now=performance.now();
            }
            const before=clock.time;clock.tick(now,false,end);
            try{await renderer!.paint(clock.time,canvas!);}catch(cause){clock.time=before;throw cause;}
            if(!valid())return;
            r.maximum=Math.max(r.maximum,clock.time);renderer!.warm(clock.time,12);
          }else clock.suspend();
          if(now-lastUpdate>100){setTime(clock.time);setMaximum(r.maximum);lastUpdate=now;}
          if(clock.time>=end && !stopped()){
            restart.current=true;const next=bag.current?.next();if(next===scenario)setReplay(v=>v+1);else if(next)setScenario(next);return;
          }
          frame=requestAnimationFrame(next=>{tick(next).catch(fail);});
        };
        frame=requestAnimationFrame(next=>{tick(next).catch(fail);});
      }catch(cause){fail(cause);}
    }
    async function fail(cause:unknown){
      if(!valid())return;
      if(!retained.current && record.completedStill && record.completedStillSha256){
        try{await poster(record.completedStill,record.completedStillSha256);if(!valid())return;commit();const at=record.completedStillAt ?? end;clock.time=at;if(runtime.current)runtime.current.maximum=at;setTime(at);setMaximum(at);}catch{}
      }
      if(!valid())return;
      clock.suspend();setLoading(false);setBuffering(false);if(!retained.current)setFallback(true);
      setError(cause instanceof Error && cause.message.includes("integrity")?cause.message:"This recording could not load. Select Replay to try again.");
    }
    initialize();
    return()=>{abort.abort();cancelAnimationFrame(frame);renderer?.dispose();transition?.cancel();for(const child of host.current?.children || [])if(child!==retained.current)child.remove();document.removeEventListener("visibilitychange",suspend);};
  },[requested?.pixels?.indexSha256,client,scenario,columns,replay,base,reduced,allowMotion]);
  const switchAgent=(next:Client)=>{if(next===client)return;restart.current=true;setClient(next);};
  const togglePause=()=>{if(error){restart.current=true;setReplay(v=>v+1);}else if(reduced && !allowMotion){restart.current=true;setAllowMotion(true);setExplicitPause(false);}else setExplicitPause(v=>!v);};
  const replayCase=()=>{restart.current=true;if(reduced)setAllowMotion(true);setReplay(v=>v+1);};
  const stopped=Boolean(error) || paused || explicitPause || reduced && !allowMotion;
  const minimum=runtime.current && shown && key(runtime.current.record)===key(shown)?runtime.current.minimum:shown?.displayStart || 0;
  return <div className="native-player" data-native-ready={ready} data-client={shownClient} data-requested-client={client} data-case={shown?.scenario || scenario} data-columns={shown?.columns || columns} data-recording-sha={shown?.sha256} data-playback-rate={PLAYBACK_RATE}>
    <div className="agent-tabs" role="tablist" aria-label="Example agent">{clients.map(({id,name},i)=><button key={id} id={"agent-"+id} aria-controls="native-session" role="tab" aria-selected={client===id} tabIndex={client===id?0:-1} onClick={()=>switchAgent(id)} onKeyDown={e=>{if(["ArrowLeft","ArrowRight","Home","End"].includes(e.key)){e.preventDefault();const n=e.key==="Home"?0:e.key==="End"?3:(i+(e.key==="ArrowRight"?1:3))%4;switchAgent(clients[n].id);(e.currentTarget.parentElement?.children[n] as HTMLButtonElement)?.focus();}}}>{name}<span>{manifest?.clients[id]?.version || ""}</span></button>)}</div>
    <div className="player-layout">
      <div className="player-recording">
      <div ref={stage} className={"native-stage"+(expanded?" is-expanded":"")} role={expanded?"dialog":undefined} aria-modal={expanded?true:undefined} aria-label={expanded?clients.find(c=>c.id===shownClient)?.name+" recording":undefined} onKeyDown={e=>{
        if(expanded && e.key==="Escape")setExpanded(false);
        if(expanded && e.key==="Tab"){const targets=stage.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input,a[href],[tabindex="0"]');if(targets?.length){const first=targets[0],last=targets[targets.length-1];if(e.shiftKey && document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey && document.activeElement===last){e.preventDefault();first.focus();}}}
      }}>
        <div className="player-prompt"><span>{clients.find(c=>c.id===shownClient)?.name || "Native recording"}</span><p>{stories[shown?.scenario || ""]?.objective || "Preparing a local investigation…"}</p></div>
        <p id="native-session-help" className="sr-only">Scroll up to review earlier captured screens. Play resumes from that point. On touch screens, pause first.</p>
        <div ref={viewport} id="native-session" role="tabpanel" aria-label={clients.find(c=>c.id===shownClient)?.name+" recorded terminal history"} aria-busy={buffering || loading} tabIndex={0} aria-describedby="native-session-help" className={"native-viewport"+(explicitPause?" is-reviewing":"")} style={{aspectRatio:shown?.pixels?shown.pixels.width+"/"+shown.pixels.height:"120/28"}} onKeyDown={e=>{
          const r=runtime.current;if(!r)return;
          const steps:Record<string,number>={ArrowUp:-2,ArrowDown:2,PageUp:-12,PageDown:12};
          if(e.key in steps){e.preventDefault();seek((r.seek ?? r.clock.time)+steps[e.key]);}
          if(e.key==="Home" || e.key==="End"){e.preventDefault();seek(e.key==="Home"?r.minimum:r.maximum);}
        }}><div ref={host} className="native-host"/>
          {fallback && !retained.current && requested && <CapturedPoster base={base} opening={requested.still && requested.stillSha256?{file:requested.still,sha256:requested.stillSha256}:undefined} completed={requested.completedStill && requested.completedStillSha256?{file:requested.completedStill,sha256:requested.completedStillSha256}:undefined} preferCompleted={true} label={"Captured native "+requested.client+" interface"} onReady={file=>{if(file!==requested.completedStill && file!==requested.still)return;setCommitted(requested);const at=file===requested.completedStill?requested.completedStillAt ?? requested.duration:requested.displayStart || 0;setTime(at);setMaximum(at);setReady(true);}}/>}
          {!retained.current && !fallback && <div className="recording-loading" role="status">Loading the captured interface…</div>}
        </div>
        <div className="recording-history"><span>Recorded history</span><input className="history-scroll" type="range" min={minimum} max={Math.max(minimum+.001,maximum)} disabled={maximum<=minimum || !runtime.current?.renderer} step={1/60} value={Math.max(minimum,Math.min(maximum,time))} aria-label="Recorded terminal history" aria-valuetext={Math.round(time)+" seconds into the recording"} onChange={e=>seek(Number(e.target.value))}/></div>
        <div className="player-controls"><div><button disabled={paused || !ready} aria-label={stopped?"Play recording":"Pause recording"} onClick={togglePause}>{stopped?<Play size={21}/>:<Pause size={21}/>}</button><button aria-label="Replay this case" onClick={replayCase}><ArrowCounterClockwise size={21}/></button><button ref={openButton} aria-label={expanded?"Close enlarged recording":"Enlarge recording"} onClick={()=>setExpanded(v=>!v)}>{expanded?<ArrowsInSimple size={21}/>:<ArrowsOutSimple size={21}/>}</button></div><span>{currentCase?.title || "Local investigation"}<span className="playback-speed">Recorded · {PLAYBACK_RATE}×</span></span><span className="history-hint">{stopped?"Scroll to review history":<><span className="desktop-history-hint">Scroll up to review</span><span className="touch-history-hint">Pause to review history</span></>}</span></div>
        {(loading || buffering || error) && <p className="player-status" role={error?"alert":"status"}>{error || (loading?"Switching to "+clients.find(c=>c.id===client)?.name+"…":"Loading the next frames…")}{error && <a href="https://github.com/0xMihirK/hercules-mcp/blob/main/website/CAPTURE.md">About these recordings</a>}</p>}
        <progress aria-label="Recording progress" value={time} max={sessionEnd(shown?.duration || 1,shown?.chapters.report)}/>
      </div>
      <SessionTranscript key={shown?.transcript || "loading"} url={shown?.transcript?base+shown.transcript:undefined}/>
      </div>
      <SessionStory recording={shown || null} time={time} base={base} title={currentCase?.title || ""}/>
    </div>
  </div>;
}
