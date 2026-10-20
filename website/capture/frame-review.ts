import { PixelRenderer,verifiedFetch,type PixelIndex } from "../src/pixel-renderer";
import { PlaybackClock,frameAt } from "../src/pixel-timeline.js";
import type { NativeManifest } from "../src/native-types";
document.body.style.cssText="margin:24px;background:#101317;color:#edf1f5;font:16px sans-serif";
const host=document.querySelector<HTMLDivElement>("#native-frame")!;
host.style.cssText="display:flex;flex-wrap:wrap;gap:24px;margin-top:20px";
const picker=document.querySelector<HTMLSelectElement>("#recording")!,milestone=document.querySelector<HTMLSelectElement>("#milestone")!,status=document.querySelector<HTMLElement>("#status")!;
const base="/assets/preview-recordings/",manifest:NativeManifest=await (await fetch(base+"manifest.json",{cache:"no-store"})).json();
for(const recording of manifest.recordings){const option=document.createElement("option");option.value=recording.file;option.textContent=recording.file;picker.append(option);}
let generation=0,controller:AbortController|undefined,renderer:PixelRenderer|undefined;
async function render(){
  const id=++generation;controller?.abort();renderer?.dispose();controller=new AbortController();
  status.textContent="Loading independent native capture";host.dataset.ready="false";
  const entry=manifest.recordings.find(r=>r.file===picker.value)!;
  if(!entry.pixels)throw Error("Independent native graphical capture missing");
  const url=base+entry.pixels.index;
  const index:PixelIndex & {reviewFrames:Record<string,{at:number;file:string;sha256:string}>}=JSON.parse(new TextDecoder().decode(await verifiedFetch(url,entry.pixels.indexSha256,controller.signal)));
  const kind=milestone.value==="intro"?"startup":milestone.value==="report"?"completed":milestone.value,review=index.reviewFrames[kind];
  if(!review)throw Error("Native milestone unavailable");
  const assets=new URL(".",new URL(url,location.href)).href,canvas=document.createElement("canvas");
  renderer=new PixelRenderer(index,assets,controller.signal);await renderer.paint(review.at,canvas);
  if(id!==generation)return;
  const independent=document.createElement("img");independent.src=assets+review.file;independent.alt="Independent native graphical master frame";
  await independent.decode();if(id!==generation)return;
  host.replaceChildren(canvas,independent);host.dataset.ready="true";host.dataset.at=String(review.at);host.dataset.sha256=entry.pixels.indexSha256;
  const verification=canvas.getContext("2d")!.getImageData(0,0,index.width,index.height).data,comparison=document.createElement("canvas");
  comparison.width=index.width;comparison.height=index.height;const context=comparison.getContext("2d")!;context.drawImage(independent,0,0);
  const native=context.getImageData(0,0,index.width,index.height).data;
  const exact=verification.length===native.length && verification.every((value,i)=>value===native[i]);
  host.dataset.pixelExact=String(exact);status.textContent=(exact?"Pixel exact":"PIXEL MISMATCH")+": "+entry.file+" · "+review.at.toFixed(3)+" s · "+index.width+" × "+index.height+" pixels. Left: player. Right: independent native master.";
  document.querySelector("#frame-transcript")!.textContent=await (await fetch(base+entry.transcript)).text();
}
document.querySelector("#render")!.addEventListener("click",()=>{render().catch(error=>{status.textContent=String(error);});});
document.querySelector<HTMLButtonElement>("#timing")!.addEventListener("click",async()=>{
  const button=document.querySelector<HTMLButtonElement>("#timing")!,result=document.querySelector<HTMLElement>("#timing-status")!;
  button.disabled=true;result.textContent="Preparing original native frame assets";
  const abort=new AbortController();let player:PixelRenderer|undefined;
  try{
    const entry=manifest.recordings.find(r=>r.file===picker.value)!,url=base+entry.pixels!.index;
    const source:PixelIndex=JSON.parse(new TextDecoder().decode(await verifiedFetch(url,entry.pixels!.indexSha256,abort.signal)));
    player=new PixelRenderer(source,new URL(".",new URL(url,location.href)).href,abort.signal);await player.prepare();
    const kind=milestone.value==="intro"?"startup":milestone.value==="report"?"completed":milestone.value;
    const reviews=(source as PixelIndex & {reviewFrames:Record<string,{at:number}>}).reviewFrames;
    const canvas=document.createElement("canvas"),start=reviews[kind]?.at ?? entry.displayStart ?? 0,clock=new PlaybackClock(start);
    await player.paint(start,canvas);host.replaceChildren(canvas);result.textContent="Measuring native presentation at 1×";
    let maximum=0,paints=0,mismatches=0,lateness=0;
    await new Promise<void>((resolve,reject)=>{
      const tick=async(now:number)=>{
        try{
          const target=clock.tick(now,document.hidden,source.duration),before=canvas.dataset.nativeFrameAt;
          await player!.paint(target,canvas);
          if(canvas.dataset.nativeFrameAt!==before){paints++;maximum=Math.max(maximum,Number(canvas.dataset.nativePaintLatencyMs));}
          if(Number(canvas.dataset.nativeFrameAt)!==source.frames[frameAt(source.frames,target)].at)mismatches++;
          const actual=clock.tick(performance.now(),document.hidden,source.duration),displayed=frameAt(source.frames,Number(canvas.dataset.nativeFrameAt));
          const next=source.frames[displayed+1]?.at;
          if(next!==undefined && actual>next)lateness=Math.max(lateness,(actual-next)*1000);
          if(target-start>=15 || target>=source.duration){resolve();return;}
          requestAnimationFrame(next=>{tick(next).catch(reject);});
        }catch(error){reject(error);}
      };
      requestAnimationFrame(next=>{tick(next).catch(reject);});
    });
    result.dataset.paints=String(paints);result.dataset.mismatches=String(mismatches);result.dataset.maximumPaintLatencyMs=String(maximum);result.dataset.maximumPresentationLatenessMs=String(lateness);
    result.textContent=`${paints} native frame changes; ${mismatches} timestamp-selection mismatches; maximum paint latency ${maximum.toFixed(2)} ms; maximum presentation lateness ${lateness.toFixed(2)} ms. One capture frame: ${(1000/source.fps).toFixed(2)} ms.`;
  }catch(error){result.textContent=String(error);}finally{abort.abort();player?.dispose();button.disabled=false;}
});
await render();
