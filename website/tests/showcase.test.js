import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {renderToStaticMarkup} from "react-dom/server";
import {createElement} from "react";
import {execFileSync} from "node:child_process";
import ts from "typescript";
const data=JSON.parse(await readFile(new URL("../src/showcase-content.json",import.meta.url),"utf8"));
const manifest=JSON.parse(await readFile(new URL("../assets/recordings/manifest.json",import.meta.url),"utf8"));
async function component(path,replacements={}){
  let source=await readFile(new URL(path,import.meta.url),"utf8");
  for(const [from,to] of Object.entries(replacements))source=source.replace(from,to);
  const code=ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText
    .replaceAll('"react/jsx-runtime"',JSON.stringify(import.meta.resolve("react/jsx-runtime")))
    .replaceAll('"react"',JSON.stringify(import.meta.resolve("react")))
    .replaceAll('"gsap"',JSON.stringify(import.meta.resolve("gsap")))
    .replace(/"(@phosphor-icons\/react(?:\/[^"]+)?)"/g,(_,specifier)=>JSON.stringify(import.meta.resolve(specifier)));
  return import("data:text/javascript;base64,"+Buffer.from(code).toString("base64"));
}
const {default:Story}=await component("../src/components/SessionStory.tsx",{'import content from "../showcase-content.json";':"const content="+JSON.stringify(data)+";"});
const {default:Architecture,roundedRoute,architectureRoutes,createArchitectureLoop}=await component("../src/components/ArchitectureScene.tsx",{'import.meta.env.BASE_URL':'"/"'});

test("architecture exposes named capabilities, accessible controls and truthful static fallback",()=>{
  const markup=renderToStaticMarkup(createElement(Architecture,{reduced:true,paused:false}));
  assert.equal((markup.match(/data-feature=/g)||[]).length,11);
  assert.equal((markup.match(/aria-controls="architecture-detail"/g)||[]).length,11);
  assert.equal((markup.match(/aria-pressed="false"/g)||[]).length,11);
  assert.match(markup,/Active \u00b7 mounted in this runtime/);
  assert.match(markup,/Retained \u00b7 available to inspect/);
  assert.match(markup,/Important diagnostics kept/);
  assert.match(markup,/Tools start only when requested/);
  assert.doesNotMatch(markup,/18MB|98\.5|AST Filter|Zero host pollution|live telemetry|sandbox-controls/);
  assert.match(markup,/Started on request/);
  assert.equal((markup.match(/<button /g)||[]).length,11);
  for(const name of ["Browser control","Recon &amp; services","Web assessment","Files &amp; forensics","Exploit research","Credential testing"]) assert.ok(markup.includes(name));
  assert.doesNotMatch(markup,/Runtime 02|Workspace 02|never truncates|markerStart=/);
  assert.match(markup,/Select a capability to see its tools/);
  assert.match(markup,/Host MCP server/);
  assert.match(markup,/Stored on your host/);
  assert.match(markup,/Previous session/);
  assert.match(markup,/map-mount-port/);
  assert.match(markup,/map-workspace-port/);
  assert.match(markup,/Workspace mount/);
  assert.match(markup,/Example job progress/);
  assert.doesNotMatch(markup,/Independent checks running|Large responses have separate size limits/);
  assert.match(markup,/Give your agent security tools in a Docker workspace/);
  assert.match(markup,/map-runtime-unit/);
  const agent=markup.indexOf('class="map-agent"'), filter=markup.indexOf('data-feature="filter"'), hub=markup.indexOf('data-feature="hercules"'), docker=markup.indexOf('class="map-runtime-stage"');
  assert.ok(agent<hub && hub<docker && docker<filter,"request row followed by an inline return filter");
  assert.match(markup,/Part of Hercules/);
  assert.match(markup,/Horizontal Hercules connection diagram/);
  assert.match(markup,/role="region" aria-label="Architecture explanation" tabindex="0"/);
  assert.doesNotMatch(markup,/map-dispatch-link/);
  assert.doesNotMatch(markup,/scene-shell-trace/);
});
test("return routing is one rounded channel through the filter, with left-facing horizontal arrows",()=>{
  const ports={agent:{x:200,y:80},hub:{x:270,y:80},dispatch:{x:550,y:80},docker:{x:620,y:80},agentReturn:{x:200,y:190},filter:{x:270,y:340},filterInput:{x:550,y:340},result:{x:620,y:400},mount:{x:990,y:430},workspace:{x:990,y:480}};
  const routes=architectureRoutes(ports);
  assert.equal((routes.response.match(/M/g)||[]).length,1,"return channel must not branch");
  assert.match(routes.response,/^M620,400/);
  assert.match(routes.response,/L200,190$/);
  assert.ok(routes.response.includes("Q"),"orthogonal bends are rounded");
  assert.equal((routes.request.match(/M/g)||[]).length,2);
  assert.equal(routes.arrows.length,2);
  for(const arrow of routes.arrows){assert.equal(arrow.y,340);assert.ok(arrow.x>200 && arrow.x<620);}
  assert.doesNotMatch(routes.response,/NaN|Infinity/);
  assert.equal(roundedRoute([{x:0,y:0},{x:0,y:0},{x:10,y:0}]),"M0,0 L10,0");
  assert.equal(roundedRoute([]),"");
  const tight=roundedRoute([{x:0,y:0},{x:2,y:0},{x:2,y:2}]);
  assert.equal(tight,"M0,0 L1,0 Q2,0 2,1 L2,2","radius is bounded by available space");
});
test("the actual 15-second GSAP loop stops before arrival and preserves the empty-slot interval",()=>{
  const targets={runtime:{opacity:1,scale:1,filter:"grayscale(0)"},rows:Array.from({length:6},()=>({opacity:1,y:0})),bars:Array.from({length:3},()=>({scaleX:0})),request:{opacity:0,strokeDashoffset:1},response:{opacity:0,strokeDashoffset:1},noise:{opacity:1,x:0}};
  let stage="ready",replacing=false,stable=0;
  const loop=createArchitectureLoop(targets,value=>stage=value,value=>replacing=value,()=>stable++);
  try{
    assert.equal(loop.duration(),15);
    loop.totalTime(1,false);assert.equal(stage,"working");assert.ok(targets.bars[0].scaleX>targets.bars[2].scaleX);
    loop.totalTime(5.6,false);assert.equal(stage,"complete");assert.ok(targets.bars.every(bar=>Math.abs(bar.scaleX-1)<.001));
    loop.totalTime(7.2,false);assert.equal(stage,"stopping");assert.equal(replacing,true);
    loop.totalTime(8.41,false);assert.equal(stage,"stopped");assert.equal(targets.runtime.opacity,0);assert.ok(targets.rows.every(row=>row.opacity===0));
    loop.totalTime(9.09,false);assert.equal(stage,"stopped");assert.equal(targets.runtime.opacity,0);
    loop.totalTime(9.35,false);assert.equal(stage,"starting");assert.ok(targets.rows[5].opacity>targets.rows[0].opacity,"rows arrive in reverse order");
    loop.totalTime(10.81,false);assert.equal(stage,"ready");assert.equal(replacing,false);assert.equal(stable,1);assert.equal(targets.runtime.opacity,1);assert.equal(targets.runtime.scale,1);assert.ok(targets.bars.every(bar=>bar.scaleX===0));
    loop.totalTime(15.1,false);assert.equal(stage,"request");
  }finally{loop.kill();}
});
test("every presentation beat uses a real completed call and an existing artifact",()=>{
  assert.deepEqual(Object.keys(data).sort(),Object.keys(manifest.cases).sort());
  for(const r of manifest.recordings){
    const story=data[r.scenario];assert.ok(story.objective.length<150);
    for(const beat of story.beats){assert.ok(beat.afterCall>=1 && beat.afterCall<=r.synchronized.length);if(beat.artifact)assert.ok(r.artifacts.some(a=>a.path===beat.artifact),r.file+" "+beat.artifact);}
  }
});
test("the real companion component gates discoveries, screenshots and verified reports",()=>{
  const r=manifest.recordings.find(r=>r.client==="claude" && r.scenario==="website" && r.columns===120);
  const render=time=>renderToStaticMarkup(createElement(Story,{recording:r,time,base:"/assets/recordings/",title:"Website assessment"}));
  const first=data.website.beats[0],at=r.synchronized[first.afterCall-1].at;
  assert.ok(!render(at-.01).includes(first.finding));assert.ok(render(at+.01).includes(first.finding));
  const report=r.reportAvailableAt;assert.ok(!render(report-.01).includes("View report"));assert.ok(render(report+.01).includes("View report"));
  // Raw JSON browser captures are not used as marketing imagery.
  assert.ok(!render(report+1).includes("debug.png"));
  const browser=manifest.recordings.find(r=>r.client==="claude" && r.scenario==="browser" && r.columns===120);
  const picture=browser.artifacts.find(a=>a.path.includes("dashboard.png"));
  const browserRender=time=>renderToStaticMarkup(createElement(Story,{recording:browser,time,base:"/assets/recordings/",title:"Browser workflow review"}));
  assert.ok(!browserRender(picture.availableAt-.01).includes('alt="Verified local dashboard"'));
  assert.ok(browserRender(picture.availableAt+.01).includes('alt="Verified local dashboard"'));
  assert.doesNotMatch(render(report+1),/nuclei_run|scriptedObservation|output_complete|matcher-status/);
});
test("the showcased filtering example is produced by the registered Hercules filter",async()=>{
  const specimen=JSON.parse(await readFile(new URL("../assets/filter-example.json",import.meta.url),"utf8"));
  const actual=execFileSync("python",["-c","import json,sys;from hercules.output.filters import filter_nikto;s=json.load(sys.stdin);print(json.dumps(filter_nikto(s['raw'])))"],{cwd:new URL("../../",import.meta.url),input:JSON.stringify(specimen),encoding:"utf8"});
  assert.equal(JSON.parse(actual),specimen.filtered);
  assert.ok(specimen.filtered.includes("WARNING: Scan was incomplete"));
  assert.ok(specimen.filtered.includes("Debug data is visible"));
  assert.ok(!specimen.filtered.includes("Start Time:"));
  assert.ok(!specimen.filtered.includes("End Time:"));
});
test("browser story preserves success before the independent rejected-password check",()=>{
  const story=data.browser;assert.equal(story.beats[1].afterCall,9);assert.equal(story.beats[2].afterCall,10);
  assert.match(story.beats[1].finding,/successful/);assert.match(story.beats[2].finding,/incorrect password/);
});
