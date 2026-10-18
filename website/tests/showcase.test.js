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
const {default:Architecture}=await component("../src/components/ArchitectureScene.tsx",{'import.meta.env.BASE_URL':'"/"'});

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
  assert.match(markup,/Start on request/);
  assert.equal((markup.match(/<button /g)||[]).length,11);
  for(const name of ["CloakBrowser","Nmap","Nuclei","SQLMap","Binwalk","Metasploit","Hydra","John the Ripper"]) assert.ok(markup.includes(name));
  assert.match(markup,/map-runtime-unit/);
  const agent=markup.indexOf('class="map-agent"'), filter=markup.indexOf('data-feature="filter"'), hub=markup.indexOf('data-feature="hercules"'), docker=markup.indexOf('class="map-runtime-stage"');
  assert.ok(agent<filter && filter<hub && hub<docker,"agent → output filter → Hercules → Docker");
  assert.match(markup,/Filters returned output/);
  assert.match(markup,/Horizontal Hercules connection diagram/);
  assert.doesNotMatch(markup,/map-dispatch-link/);
  assert.doesNotMatch(markup,/scene-shell-trace/);
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
