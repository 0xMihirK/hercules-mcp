import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import xterm from "@xterm/xterm";
import { parseRecording, RecordingCursor } from "../src/recording.js";
const root=new URL("../assets/recordings/",import.meta.url);
const versions={claude:"2.1.292",codex:"0.160.1",opencode:"1.18.35",hermes:"0.21.5"};
const hash=bytes=>createHash("sha256").update(bytes).digest("hex");
const manifest=async()=>JSON.parse(await readFile(new URL("manifest.json",root),"utf8"));
const write=(terminal,bytes)=>new Promise(resolve=>terminal.write(bytes,resolve));
function imageFormat(bytes,file){
  const png=bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10]));
  const jpeg=bytes.subarray(0,3).equals(Buffer.from([255,216,255]));
  assert.ok(png || jpeg,"actual browser screenshot signature");
  assert.ok(file.endsWith(png ? ".png" : ".jpg"),"extension matches preserved capture bytes");
}
function cells(terminal){const b=terminal.buffer.active;return {x:b.cursorX,y:b.cursorY,rows:Array.from({length:terminal.rows},(_,y)=>{const line=b.getLine(b.viewportY+y);return Array.from({length:terminal.cols},(_,x)=>{const c=line.getCell(x);return [c.getChars(),c.getWidth(),c.getFgColorMode(),c.getFgColor(),c.getBgColorMode(),c.getBgColor()];});})};}

test("120 sessions preserve pinned clients, bytes and real-tool provenance",async()=>{
  const m=await manifest();assert.equal(m.schemaVersion,2);assert.equal(m.developmentOnly,false);
  assert.equal(m.nativeUI,true);assert.equal(m.realTools,true);assert.equal(m.scriptedModel,true);assert.equal(m.scriptedToolResults,false);
  assert.equal(m.accountAccess,false);assert.equal(m.externalNetwork,false);assert.equal(m.playbackSpeed,1);
  const catalog=await readFile(new URL("../capture/lab-cases.json",import.meta.url),"utf8");assert.equal(hash(catalog.replace(/\r\n/g,"\n")),m.caseCatalogSha256);
  assert.equal(Object.keys(m.cases).length,10);assert.equal(m.recordings.length,120);const seen=new Set();
  for(const r of m.recordings){
    const bytes=await readFile(new URL(r.file,root)),source=parseRecording(bytes.toString("utf8"));
    assert.equal(hash(bytes),r.sha256,r.file);assert.equal(r.version,versions[r.client]);assert.equal(source.header.clientVersion,r.version);
    assert.equal(source.header.realTools,true);assert.equal(source.header.fixture,false);assert.ok([48,80,120].includes(r.columns));
    assert.deepEqual([source.header.width,source.header.height],[r.columns,r.columns===120?36:28]);assert.ok(source.events.length>10);
    assert.ok(r.displayStart>=0 && r.displayStart<r.chapters.query);assert.ok(source.events.some(([at])=>at===r.displayStart));
    assert.ok(r.duration>=r.chapters.report+6,"six-second completion hold");assert.ok(r.tools.length>=8 && r.tools.length<=16);
    assert.equal(r.tools[0],"system_start_container");assert.equal(r.tools.at(-1),"system_stop_container");assert.ok(r.tools.includes("workspace_write_file"));
    assert.equal(hash(await readFile(new URL(r.transcript,root))),r.transcriptSha256);
    const still=await readFile(new URL(r.still,root));assert.equal(hash(still),r.stillSha256);imageFormat(still,r.still);
    assert.equal(r.stillAt,r.displayStart);assert.match(r.stillRenderer,/captured ANSI/);assert.ok(r.synchronized.every(f=>!f.scriptedObservation && f.at<=r.duration));
    const completed=await readFile(new URL(r.completedStill,root));assert.equal(hash(completed),r.completedStillSha256);imageFormat(completed,r.completedStill);assert.equal(r.completedStillAt,r.duration-1);
    const report=await readFile(new URL(r.report,root),"utf8");assert.match(report,/Verified observations/);assert.match(report,/scripted/);assert.match(report,/No public target/);
    assert.ok(r.artifacts.every(a=>a.availableAt>=0 && a.availableAt<=r.duration));
    const key=`${r.client}/${r.scenario}/${r.columns}`;assert.ok(!seen.has(key));seen.add(key);
  }
  for(const client of Object.keys(versions))for(const scenario of Object.keys(m.cases))for(const cols of [120,80,48])assert.ok(seen.has(`${client}/${scenario}/${cols}`));
});

test("public evidence hashes and CTF checksums match actual artifacts",async()=>{
  const m=await manifest(),checked=new Set();
  for(const r of m.recordings){
    for(const a of r.artifacts){if(checked.has(a.file))continue;const bytes=await readFile(new URL(a.file,root));assert.equal(bytes.length,a.bytes);assert.equal(hash(bytes),a.sha256,a.file);checked.add(a.file);}
    if(r.scenario==="forensics"){const a=r.artifacts.find(a=>a.path==="artifacts/forensics/verification.json"),proof=JSON.parse(await readFile(new URL(a.file,root),"utf8"));assert.equal(proof.checksum_match,true);assert.equal(proof.decoy_match,false);assert.equal(hash(proof.flag),proof.sha256);}
    for(const metric of r.metrics){assert.equal(metric.rawTokenEstimate,Math.ceil(metric.rawCharacters/4));assert.equal(metric.inlineTokenEstimate,Math.ceil(metric.inlineResponseCharacters/4));assert.equal(metric.characterReduction,metric.rawCharacters ? Math.round(1000*(1-metric.inlineResponseCharacters/metric.rawCharacters))/10 : 0);}
  }
});

test("native startup, MCP, task and report cells survive catch-up in all grids",async()=>{
  const m=await manifest();
  for(const r of m.recordings.filter(r=>r.scenario==="network")){
    const source=parseRecording(await readFile(new URL(r.file,root),"utf8")),options={cols:r.columns,rows:r.rows,scrollback:0,convertEol:false};
    const sequential=new xterm.Terminal(options),cursor=new RecordingCursor(source);
    try{for(const at of [r.displayStart,r.chapters.mcp+4,r.chapters.investigation+3,r.duration]){
      // Replay the same bounded catch-up batches used by the browser clock.
      // Every byte remains ordered; compare full cells at each native milestone.
      while(cursor.index<source.events.length && source.events[cursor.index][0]<=at)await write(sequential,cursor.drain(Math.min(at,source.events[cursor.index][0]+.25)));
      const fresh=new xterm.Terminal(options);
      try{await write(fresh,new RecordingCursor(source).drain(at));assert.deepEqual(cells(fresh),cells(sequential),`${r.file} at ${at}`);assert.ok(cells(fresh).rows.some(row=>row.some(([text])=>text.trim())),"nonempty native frame");}finally{fresh.dispose();}
    }}finally{sequential.dispose();}
  }
});
