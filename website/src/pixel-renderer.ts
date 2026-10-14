import { frameAt } from "./pixel-timeline.js";

export type PixelIndex = {
  schemaVersion: 3; width:number; height:number; fps:number; duration:number;
  sheets:{file:string;sha256:string}[];
  frames:{at:number;patches:[number,number,number,number,number,number,number][];keyframe:boolean;sha256:string}[];
  reviewFrames?:Record<string,{at:number;file:string;sha256:string}>;
};
const COMPRESSED_LIMIT=32*1024*1024, DECODED_LIMIT=64*1024*1024;
const compressed=new Map<string,ArrayBuffer>();
let compressedBytes=0;
export function clearPixelCache(){compressed.clear();compressedBytes=0;}
export function pixelCacheStats(){return {bytes:compressedBytes,limit:COMPRESSED_LIMIT};}
function cache(sha:string,bytes:ArrayBuffer){
  if(compressed.has(sha))compressedBytes-=compressed.get(sha)!.byteLength;
  compressed.delete(sha);compressed.set(sha,bytes);compressedBytes+=bytes.byteLength;
  while(compressedBytes>COMPRESSED_LIMIT && compressed.size){const key=compressed.keys().next().value!;compressedBytes-=compressed.get(key)!.byteLength;compressed.delete(key);}
}
export async function verifiedFetch(url:string,sha:string,signal:AbortSignal):Promise<ArrayBuffer>{
  if(signal.aborted)throw new DOMException("Discarded capture","AbortError");
  const hit=compressed.get(sha);
  if(hit){compressed.delete(sha);compressed.set(sha,hit);return hit;}
  const request=new AbortController(),cancel=()=>request.abort();
  signal.addEventListener("abort",cancel,{once:true});const timeout=setTimeout(cancel,90000);
  let bytes:ArrayBuffer;
  try{
    const response=await fetch(url+(url.includes("?")?"&":"?")+"sha="+sha,{signal:request.signal});
    if(!response.ok)throw Error("Capture asset failed to load. Replay to retry.");
    bytes=await response.arrayBuffer();
  }finally{clearTimeout(timeout);signal.removeEventListener("abort",cancel);}
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)),v=>v.toString(16).padStart(2,"0")).join("");
  if(hash!==sha)throw Error("Capture integrity check failed.");
  if(signal.aborted)throw new DOMException("Discarded capture","AbortError");
  cache(sha,bytes);return bytes;
}

/** Compose original native pixels offscreen, with bounded decoding and rolling buffering. */
export class PixelRenderer {
  private work:HTMLCanvasElement;
  private context:CanvasRenderingContext2D;
  private images=new Map<number,{image:ImageBitmap;bytes:number}>();
  private imageBytes=0;
  private fetching=new Map<number,Promise<ArrayBuffer>>();
  private current=-1;
  private alive=true;
  private busy=false;
  private prefetch:Promise<void>|null=null;
  constructor(private index:PixelIndex,private base:string,private signal:AbortSignal){
    this.work=document.createElement("canvas");this.work.width=index.width;this.work.height=index.height;
    const context=this.work.getContext("2d",{alpha:false});if(!context)throw Error("Canvas2D unavailable");this.context=context;
  }
  get stats(){return {decodedBytes:this.imageBytes,decodedLimit:DECODED_LIMIT};}
  private check(){if(!this.alive || this.signal.aborted)throw new DOMException("Discarded capture","AbortError");}
  private async bytes(number:number){
    this.check();let pending=this.fetching.get(number);
    if(!pending){const asset=this.index.sheets[number];pending=verifiedFetch(this.base+asset.file,asset.sha256,this.signal);this.fetching.set(number,pending);}
    try{const bytes=await pending;this.check();return bytes;}finally{this.fetching.delete(number);}
  }
  private dependencies(from:number,to:number){
    const first=frameAt(this.index.frames,from),last=frameAt(this.index.frames,to);
    return [...new Set(this.index.frames.slice(first,last+1).flatMap(f=>f.patches.map(p=>p[0])))];
  }
  hasBuffer(from:number,to:number){return this.dependencies(from,to).every(n=>this.images.has(n) || compressed.has(this.index.sheets[n].sha256));}
  async prepare(from=0,seconds=this.index.duration){
    const needed=this.dependencies(from,Math.min(this.index.duration,from+seconds));
    for(let start=0;start<needed.length;start+=4){await Promise.all(needed.slice(start,start+4).map(n=>this.bytes(n)));this.check();}
  }
  warm(from:number,seconds=12){
    if(this.prefetch || !this.alive)return;
    this.prefetch=this.prepare(from,seconds).catch(()=>{}).finally(()=>{this.prefetch=null;});
  }
  private async sheet(number:number){
    const hit=this.images.get(number);
    if(hit){this.images.delete(number);this.images.set(number,hit);return hit.image;}
    const bytes=await this.bytes(number),header=new DataView(bytes);
    const estimate=header.byteLength>=24?header.getUint32(16)*header.getUint32(20)*4:DECODED_LIMIT;
    if(estimate>DECODED_LIMIT)throw Error("Native atlas exceeds the decoding budget");
    while(this.imageBytes+estimate>DECODED_LIMIT && this.images.size){const key=this.images.keys().next().value!,old=this.images.get(key)!;old.image.close();this.imageBytes-=old.bytes;this.images.delete(key);}
    const image=await createImageBitmap(new Blob([bytes],{type:"image/png"}),{colorSpaceConversion:"none"});
    if(!this.alive || this.signal.aborted){image.close();this.check();}
    const size=image.width*image.height*4;
    this.images.set(number,{image,bytes:size});this.imageBytes+=size;return image;
  }
  async paint(time:number,visible:HTMLCanvasElement):Promise<boolean>{
    if(!this.alive || this.busy)return false;
    const target=frameAt(this.index.frames,time);if(target===this.current)return true;
    const requested=performance.now();this.busy=true;
    try{
      let start=this.current+1;
      if(this.current<0 || target<this.current || target-this.current>180){
        start=target;while(start>0 && !this.index.frames[start].keyframe)start--;
      }
      // Consume in native patch order; seeks never hold every dependency decoded together.
      for(let i=start;i<=target;i++)for(const [n,sx,sy,w,h,dx,dy] of this.index.frames[i].patches){
        const image=await this.sheet(n);this.check();this.context.drawImage(image,sx,sy,w,h,dx,dy,w,h);
      }
      this.check();const context=visible.getContext("2d",{alpha:false});if(!context)throw Error("Canvas2D unavailable");
      if(visible.width!==this.index.width || visible.height!==this.index.height){visible.width=this.index.width;visible.height=this.index.height;}
      context.drawImage(this.work,0,0);this.current=target;
      if(visible.dataset){visible.dataset.nativeFrameAt=String(this.index.frames[target].at);visible.dataset.nativeRequestedAt=String(time);visible.dataset.nativePaintLatencyMs=String(performance.now()-requested);visible.dataset.decodedBytes=String(this.imageBytes);}
      return true;
    }finally{this.busy=false;}
  }
  dispose(){this.alive=false;for(const {image} of this.images.values())image.close();this.images.clear();this.imageBytes=0;}
}
