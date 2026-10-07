import { Terminal } from "@xterm/xterm";
import { Unicode11Addon } from "@xterm/addon-unicode11";
import "@xterm/xterm/css/xterm.css";
import { parseRecording } from "../src/recording.js";
import type { NativeManifest } from "../src/native-types";
import font from "../assets/fonts/ibm-plex-mono-latin-400.woff2?url";

const face=new FontFace("IBM Plex Mono",`url(${font})`);await face.load();document.fonts.add(face);
document.body.style.cssText="margin:24px;background:#101317;color:#edf1f5;font:16px sans-serif";
const host=document.querySelector<HTMLDivElement>("#native-frame")!;
host.style.cssText="position:relative;display:block;background:#0a0a0a;padding:0;margin-top:20px;width:max-content";
const picker=document.querySelector<HTMLSelectElement>("#recording")!, milestone=document.querySelector<HTMLSelectElement>("#milestone")!, status=document.querySelector<HTMLElement>("#status")!;
const base="/assets/preview-recordings/", manifest:NativeManifest=await (await fetch(base+"manifest.json")).json();
for(const recording of manifest.recordings){
  const option=document.createElement("option");option.value=recording.file;option.textContent=recording.file;
  option.dataset.sha256=recording.sha256;option.dataset.intro=String(recording.displayStart || 0);
  option.dataset.report=String(Math.max(0,recording.duration-1));picker.append(option);
}
let terminal:Terminal|undefined, generation=0;
async function render(){
  const id=++generation, file=picker.value, kind=milestone.value;
  status.textContent="Reconstructing native bytes";host.dataset.ready="false";
  const entry=manifest.recordings.find(r=>r.file===file)!;
  const data=parseRecording(await (await fetch(base+entry.file)).text());
  if(id!==generation)return;
  const at=kind==="intro"?entry.displayStart || 0:kind==="report"?Math.max(0,data.duration-1):(entry.chapters[kind] || 0)+2;
  terminal?.dispose();host.replaceChildren();
  terminal=new Terminal({cols:entry.columns,rows:entry.rows,fontFamily:'"IBM Plex Mono",monospace',fontSize:14,lineHeight:1,letterSpacing:0,scrollback:0,convertEol:false,allowProposedApi:true,cursorBlink:false,disableStdin:true,theme:{background:"#0a0a0a",foreground:"#eeeeee"}});
  terminal.loadAddon(new Unicode11Addon());terminal.unicode.activeVersion="11";terminal.open(host);
  const output=data.events.filter(e=>e[0]<=at).map(e=>e[2]).join("");
  await new Promise<void>(resolve=>terminal!.write(output,resolve));
  await new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve())));
  if(id!==generation)return;
  const screen=host.querySelector<HTMLElement>(".xterm-screen")!;
  host.style.width=screen.offsetWidth+"px";host.style.height=screen.offsetHeight+"px";
  host.dataset.recording=entry.file;host.dataset.sha256=entry.sha256;host.dataset.at=String(at);host.dataset.milestone=kind;host.dataset.ready="true";
  const buffer=terminal.buffer.active;
  document.querySelector("#frame-transcript")!.textContent=Array.from({length:terminal.rows},(_,y)=>buffer.getLine(buffer.viewportY+y)?.translateToString(true)||"").join("\n");
  status.textContent=`Ready: ${entry.file} · ${at.toFixed(3)} s · ${entry.columns} × ${entry.rows}`;
}
document.querySelector("#render")!.addEventListener("click",()=>render());
await render();
