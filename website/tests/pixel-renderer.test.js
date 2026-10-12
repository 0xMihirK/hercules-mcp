import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import ts from "typescript";
import { createCanvas, loadImage } from "@napi-rs/canvas";

const source=(await readFile(new URL("../src/pixel-renderer.ts",import.meta.url),"utf8")).replace('"./pixel-timeline.js"',JSON.stringify(new URL("../src/pixel-timeline.js",import.meta.url).href));
const compiled=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
const {PixelRenderer,verifiedFetch}=await import("data:text/javascript;base64,"+Buffer.from(compiled).toString("base64"));
const digest=bytes=>createHash("sha256").update(bytes).digest("hex");

test("native pixels remain exact through delta updates, backward seeks and cancelled decoding",async t=>{
  const atlas=createCanvas(4,2),ctx=atlas.getContext("2d");
  ctx.fillStyle="#10171f";ctx.fillRect(0,0,2,2);
  ctx.fillStyle="#d97757";ctx.fillRect(2,0,1,2);
  ctx.fillStyle="#d7dce4";ctx.fillRect(3,0,1,2);
  const bytes=atlas.toBuffer("image/png");
  const saved={fetch:globalThis.fetch,document:globalThis.document,createImageBitmap:globalThis.createImageBitmap};
  let release,closed=0;
  globalThis.document={createElement:()=>createCanvas(1,1)};
  globalThis.fetch=async()=>new Response(bytes);
  globalThis.createImageBitmap=async blob=>{const image=await loadImage(Buffer.from(await blob.arrayBuffer()));image.close=()=>closed++;return image;};
  t.after(()=>Object.assign(globalThis,saved));
  const index={schemaVersion:3,width:2,height:2,fps:60,duration:3,sheets:[{file:"native.png",sha256:digest(bytes)}],frames:[
    {at:0,keyframe:true,patches:[[0,0,0,2,2,0,0]]},
    {at:.016,keyframe:false,patches:[[0,2,0,1,2,0,0]]},
    {at:.123,keyframe:false,patches:[[0,3,0,1,2,1,0]]},
  ]};
  const renderer=new PixelRenderer(index,"https://capture.invalid/",new AbortController().signal),visible=createCanvas(2,2);
  await renderer.paint(.123,visible);
  assert.deepEqual([...visible.getContext("2d").getImageData(0,0,2,1).data],[217,119,87,255,215,220,228,255]);
  await renderer.paint(0,visible);
  assert.deepEqual([...visible.getContext("2d").getImageData(0,0,2,1).data],[16,23,31,255,16,23,31,255]);
  renderer.dispose();assert.equal(closed,1);
  globalThis.fetch=()=>new Promise(resolve=>{release=()=>resolve(new Response(bytes));});
  const discarded=new PixelRenderer(index,"https://capture.invalid/",new AbortController().signal),before=visible.toBuffer("image/png");
  const pending=discarded.paint(.123,visible);discarded.dispose();release();
  await assert.rejects(pending,{name:"AbortError"});assert.deepEqual(visible.toBuffer("image/png"),before);
});

test("missing or modified native assets fail before any visible pixels change",async t=>{
  const saved=globalThis.fetch;t.after(()=>globalThis.fetch=saved);
  globalThis.fetch=async()=>new Response("missing",{status:404});
  await assert.rejects(verifiedFetch("https://capture.invalid/native.png","",new AbortController().signal),/failed to load/);
  globalThis.fetch=async()=>new Response("modified pixels");
  await assert.rejects(verifiedFetch("https://capture.invalid/native.png",digest("original pixels"),new AbortController().signal),/integrity/);
});

test("the first native frame appears before the rest of the session preloads",async t=>{
  const atlas=createCanvas(1,1);atlas.getContext("2d").fillStyle="#d87950";atlas.getContext("2d").fillRect(0,0,1,1);
  const bytes=atlas.toBuffer("image/png"),saved={fetch:globalThis.fetch,document:globalThis.document,createImageBitmap:globalThis.createImageBitmap};
  let release,openingRequests=0;
  const delayed=new Promise(resolve=>{release=resolve;});
  globalThis.document={createElement:()=>createCanvas(1,1)};
  globalThis.fetch=async url=>{if(url.includes("opening.png"))openingRequests++;else await delayed;return new Response(bytes);};
  globalThis.createImageBitmap=async blob=>{const image=await loadImage(Buffer.from(await blob.arrayBuffer()));image.close=()=>{};return image;};
  t.after(()=>Object.assign(globalThis,saved));
  const index={schemaVersion:3,width:1,height:1,fps:60,duration:20,sheets:[{file:"opening.png",sha256:digest(bytes)},{file:"later.png",sha256:digest(bytes)}],frames:[{at:0,keyframe:true,patches:[[0,0,0,1,1,0,0]]},{at:10,keyframe:false,patches:[[1,0,0,1,1,0,0]]}]};
  const renderer=new PixelRenderer(index,"https://capture.invalid/",new AbortController().signal),visible=createCanvas(1,1);
  await renderer.paint(0,visible);
  assert.deepEqual([...visible.getContext("2d").getImageData(0,0,1,1).data],[216,121,80,255]);
  let prepared=false;const preparation=renderer.prepare().then(()=>{prepared=true;});
  await new Promise(resolve=>setImmediate(resolve));assert.equal(prepared,false,"slow later assets do not block the visible opening");
  release();await preparation;assert.equal(openingRequests,1,"the opening atlas is reused during preload");renderer.dispose();
});

test("nonconsecutive reused atlases decode before their native frame is requested",async t=>{
  const assets=Array.from({length:9},(_,n)=>{const c=createCanvas(1,1),ctx=c.getContext("2d");ctx.fillStyle=`rgb(${n*25},0,0)`;ctx.fillRect(0,0,1,1);return c.toBuffer("image/png");});
  const saved={fetch:globalThis.fetch,document:globalThis.document,createImageBitmap:globalThis.createImageBitmap};
  let decodes=0;
  globalThis.document={createElement:()=>createCanvas(1,1)};
  globalThis.fetch=async url=>new Response(assets[Number(new URL(url).pathname.split("/").at(-1).split(".")[0])]);
  globalThis.createImageBitmap=async blob=>{decodes++;const image=await loadImage(Buffer.from(await blob.arrayBuffer()));image.close=()=>{};return image;};
  t.after(()=>Object.assign(globalThis,saved));
  const index={schemaVersion:3,width:1,height:1,fps:60,duration:1,sheets:assets.map((bytes,n)=>({file:n+".png",sha256:digest(bytes)})),frames:[
    {at:0,keyframe:true,patches:[[8,0,0,1,1,0,0]]},
    {at:.0167,keyframe:false,patches:[[2,0,0,1,1,0,0]]},
    {at:.0334,keyframe:false,patches:[[6,0,0,1,1,0,0]]},
  ]};
  const renderer=new PixelRenderer(index,"https://capture.invalid/",new AbortController().signal),visible=createCanvas(1,1);
  await renderer.prepare();await renderer.paint(0,visible);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(decodes,3,"both upcoming images warmed despite the reverse atlas order");
  await renderer.paint(.0167,visible);await renderer.paint(.0334,visible);
  assert.equal(decodes,3,"native frame transitions need no new decoding");
  assert.deepEqual([...visible.getContext("2d").getImageData(0,0,1,1).data],[150,0,0,255]);
  renderer.dispose();
});
