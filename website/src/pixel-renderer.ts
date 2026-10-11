import { frameAt } from "./pixel-timeline.js";

export type PixelIndex = {
  schemaVersion: 3; width:number; height:number; fps:number; duration:number;
  sheets:{file:string;sha256:string}[];
  frames:{at:number;patches:[number,number,number,number,number,number,number][];keyframe:boolean;sha256:string}[];
};

export async function verifiedFetch(url:string,sha:string,signal:AbortSignal):Promise<ArrayBuffer>{
  const request=new AbortController(),cancel=()=>request.abort();
  if(signal.aborted)request.abort();else signal.addEventListener("abort",cancel,{once:true});
  const timeout=setTimeout(cancel,90000);
  let bytes:ArrayBuffer;
  try{
    const response=await fetch(url+(url.includes("?")?"&":"?")+"sha="+sha,{signal:request.signal});if(!response.ok)throw Error("Capture asset failed to load. Replay to retry.");
    bytes=await response.arrayBuffer();
  }finally{clearTimeout(timeout);signal.removeEventListener("abort",cancel);}
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)),v=>v.toString(16).padStart(2,"0")).join("");
  if(hash!==sha)throw Error("Capture integrity check failed. Replay to retry.");
  return bytes;
}

/** Draw only original graphical pixels. Keep partially decoded frames offscreen. */
export class PixelRenderer {
  private work:HTMLCanvasElement;
  private context:CanvasRenderingContext2D;
  private images=new Map<number,{image:ImageBitmap;used:number}>();
  private bytes=new Map<number,ArrayBuffer>();
  private decoding=new Map<number,Promise<ImageBitmap>>();
  private current=-1;
  private alive=true;
  private busy=false;
  constructor(private index:PixelIndex,private base:string,private signal:AbortSignal){
    this.work=document.createElement("canvas");this.work.width=index.width;this.work.height=index.height;
    const context=this.work.getContext("2d",{alpha:false});if(!context)throw Error("Canvas2D unavailable");this.context=context;
  }
  async prepare(){
    // Fetch compressed frames before starting the native clock. Keep decoded
    // image memory bounded separately so asset latency cannot slow animations.
    for(let start=0;start<this.index.sheets.length;start+=4){
      await Promise.all(this.index.sheets.slice(start,start+4).map(async(asset,offset)=>{
        const bytes=await verifiedFetch(this.base+asset.file,asset.sha256,this.signal);
        if(this.alive && !this.signal.aborted)this.bytes.set(start+offset,bytes);
      }));
      if(!this.alive || this.signal.aborted)throw new DOMException("Discarded capture","AbortError");
    }
  }
  private async sheet(number:number){
    const cached=this.images.get(number);if(cached){cached.used=performance.now();return cached.image;}
    let promise=this.decoding.get(number);
    if(!promise){
      const asset=this.index.sheets[number];
      promise=(this.bytes.has(number)?Promise.resolve(this.bytes.get(number)!):verifiedFetch(this.base+asset.file,asset.sha256,this.signal)).then(bytes=>createImageBitmap(new Blob([bytes],{type:"image/png"}),{colorSpaceConversion:"none"})).then(image=>{
        if(!this.alive){image.close();throw new DOMException("Discarded capture","AbortError");}
        this.images.set(number,{image,used:performance.now()});return image;
      });this.decoding.set(number,promise);
    }
    try{return await promise;}finally{this.decoding.delete(number);}
  }
  async paint(time:number,visible:HTMLCanvasElement):Promise<boolean>{
    if(!this.alive || this.busy)return false;
    const target=frameAt(this.index.frames,time);if(target===this.current)return true;
    const requested=performance.now();
    this.busy=true;
    try{
      let start=this.current+1;
      if(this.current<0 || target<this.current || this.index.frames[target].at-this.index.frames[this.current].at>1){
        start=target;while(start>0 && !this.index.frames[start].keyframe)start--;
      }
      const needed=[...new Set(this.index.frames.slice(start,target+1).flatMap(frame=>frame.patches.map(p=>p[0])))];
      await Promise.all(needed.map(n=>this.sheet(n)));
      if(!this.alive || this.signal.aborted)return false;
      for(let i=start;i<=target;i++)for(const [sheet,sx,sy,w,h,dx,dy] of this.index.frames[i].patches){
        this.context.drawImage(this.images.get(sheet)!.image,sx,sy,w,h,dx,dy,w,h);
      }
      const context=visible.getContext("2d",{alpha:false});if(!context)throw Error("Canvas2D unavailable");
      if(visible.width!==this.index.width || visible.height!==this.index.height){visible.width=this.index.width;visible.height=this.index.height;}
      context.drawImage(this.work,0,0);this.current=target;
      if(visible.dataset){visible.dataset.nativeFrameAt=String(this.index.frames[target].at);visible.dataset.nativeRequestedAt=String(time);visible.dataset.nativePaintLatencyMs=String(performance.now()-requested);}
      // Bound decoded atlas memory. A future seek reconstructs from a native
      // keyframe; evicted image bitmaps can be fetched and decoded again.
      const old=[...this.images].filter(([n])=>!needed.includes(n)).sort((a,b)=>a[1].used-b[1].used);
      while(this.images.size>8 && old.length){const [n,item]=old.shift()!;item.image.close();this.images.delete(n);}
      // Shared tiles can refer to any earlier atlas. Warm the next required
      // images after eviction, rather than guessing consecutive file numbers.
      const upcoming=new Set<number>(),capacity=Math.max(0,2-this.decoding.size);
      for(let i=target+1;i<Math.min(this.index.frames.length,target+121) && upcoming.size<capacity;i++){
        for(const [n] of this.index.frames[i].patches){
          if(!this.images.has(n) && !this.decoding.has(n))upcoming.add(n);
          if(upcoming.size===capacity)break;
        }
      }
      for(const n of upcoming)this.sheet(n).catch(()=>{});
      return true;
    }finally{this.busy=false;}
  }
  dispose(){this.alive=false;for(const {image} of this.images.values())image.close();this.images.clear();this.bytes.clear();}
}
