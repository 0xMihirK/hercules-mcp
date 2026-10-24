import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {renderToStaticMarkup} from "react-dom/server";
import {createElement} from "react";
import {execFileSync} from "node:child_process";
import ts from "typescript";
const data=JSON.parse(await readFile(new URL("../src/showcase-content.json",import.meta.url),"utf8"));
const manifest=JSON.parse(await readFile(new URL("../assets/recordings/manifest.json",import.meta.url),"utf8"));
test("the site describes current resources and on-demand skills",async()=>{
  const facts=JSON.parse(await readFile(new URL("../src/site-facts.json",import.meta.url),"utf8"));
  const stats=await readFile(new URL("../src/components/StatBand.tsx",import.meta.url),"utf8");
  const setup=await readFile(new URL("../src/components/Setup.tsx",import.meta.url),"utf8");
  assert.equal(facts.catalog.full_tool_count,47);
  assert.equal(facts.catalog.resource_count,5);
  assert.match(stats,/PEAS · PowerUp · GTFOBins · LOLBAS/);
  assert.match(stats,/without Metasploit/);
  assert.ok(stats.indexOf("<dt>Registered MCP tools</dt>")<stats.indexOf("<dd>"));
  assert.equal(stats.match(/className="stat-cell"/g)?.length,3);
  assert.equal(stats.match(/className="stat-illustration" aria-hidden="true"/g)?.length,3);
  assert.doesNotMatch(stats,/Validated lab sessions|4 native clients · 10 investigations/);
  assert.doesNotMatch(stats,/NSE, Nuclei, PEAS/);
  assert.match(setup,/nine\s+portable agent skills/);
  assert.match(setup,/79 topic guides load on\s+demand/);
});
test("the platform row uses pinned brand marks and workspace-first copy",async()=>{
  const setup=await readFile(new URL("../src/components/Setup.tsx",import.meta.url),"utf8");
  assert.match(setup,/Run it where your work happens\./);
  assert.doesNotMatch(setup,/Same STDIO MCP host server/);
  for(const name of ["windows11-original","apple-original","linux-plain"]){
    assert.ok(setup.includes(`brand("${name}")`));
    assert.match(await readFile(new URL(`../assets/brands/${name}.svg`,import.meta.url),"utf8"),/^<svg /);
  }
});
// The showcase↔source filter check needs the Hercules package. It runs on main;
// on the standalone website branch (package absent) it is skipped, since the
// site-sync workflow already derives the committed data from the real source.
const HERCULES_AVAILABLE=(()=>{try{execFileSync("python",["-c","import hercules.output.filters"],{cwd:new URL("../../",import.meta.url),stdio:"ignore"});return true;}catch{return false;}})();
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
const {default:ScenarioPicker}=await component("../src/components/ScenarioPicker.tsx");
const {default:Architecture,roundedRoute,architectureRoutes,createArchitectureLoop}=await component("../src/components/ArchitectureScene.tsx",{'import.meta.env.BASE_URL':'"/"'});

test("architecture exposes named capabilities, accessible controls and truthful static fallback",()=>{
  const markup=renderToStaticMarkup(createElement(Architecture,{reduced:true,paused:false}));
  assert.equal((markup.match(/data-feature=/g)||[]).length,13);
  assert.equal((markup.match(/aria-controls="architecture-detail"/g)||[]).length,13);
  assert.equal((markup.match(/aria-pressed="false"/g)||[]).length,13);
  assert.match(markup,/Active \u00b7 mounted in this runtime/);
  assert.match(markup,/Retained \u00b7 available to inspect/);
  assert.match(markup,/Important diagnostics kept/);
  assert.doesNotMatch(markup,/Tools start only when requested/);
  assert.match(markup,/Your agent, equipped/);
  assert.match(markup,/Your evidence, retained/);
  assert.doesNotMatch(markup,/18MB|98\.5|AST Filter|Zero host pollution|live telemetry|sandbox-controls/);
  assert.match(markup,/Started on request/);
  assert.equal((markup.match(/<button /g)||[]).length,13);
  for(const name of ["Browser control","Recon &amp; services","Web assessment","Protocol testing","Files &amp; forensics","Reverse engineering","Exploit research","Credential testing"]) assert.ok(markup.includes(name));
  for(const [name,file] of [["Claude Code","claude.svg"],["Cursor","cursor.svg"],["Codex","codex.png"],["Hermes","hermes.png"]]) {assert.match(markup,new RegExp(`brands/${file.replace(".","\\.")}`));assert.ok(markup.includes(name));}
  assert.match(markup,/Other STDIO clients supported/);
  assert.doesNotMatch(markup,/Runtime 02|Workspace 02|never truncates|markerStart=/);
  assert.match(markup,/Select a capability to see its tools/);
  assert.match(markup,/Host MCP server/);
  assert.match(markup,/Evidence stays on your host/);
  assert.match(markup,/Previous session/);
  assert.match(markup,/map-mount-port/);
  assert.match(markup,/map-workspace-port/);
  assert.match(markup,/Workspace mount/);
  assert.match(markup,/Example job progress/);
  assert.doesNotMatch(markup,/Independent checks running|Large responses have separate size limits/);
  assert.match(markup,/Follow a request from your agent to Kali/);
  assert.match(markup,/map-runtime-unit/);
  const agent=markup.indexOf('class="map-agent"'), filter=markup.indexOf('data-feature="filter"'), hub=markup.indexOf('data-feature="hercules"'), docker=markup.indexOf('class="map-runtime-stage"');
  assert.ok(agent<hub && hub<docker && docker<filter,"request row followed by an inline return filter");
  assert.match(markup,/Part of Hercules/);
  assert.match(markup,/Horizontal Hercules connection diagram/);
  assert.match(markup,/role="region" aria-label="Architecture explanation" tabindex="0"/);
  assert.doesNotMatch(markup,/map-dispatch-link/);
  assert.doesNotMatch(markup,/scene-shell-trace/);
});
test("architecture additions describe existing capabilities without claiming a full RE service",async()=>{
  const source=await readFile(new URL("../src/components/ArchitectureScene.tsx",import.meta.url),"utf8");
  const placeholder=await readFile(new URL("../src/components/DeferredArchitecture.tsx",import.meta.url),"utf8");
  assert.match(source,/Binwalk can identify and extract embedded files/);
  assert.match(source,/not a full decompiler or reverse-engineering service/);
  assert.match(source,/Use Ncat for controlled TCP or UDP exchanges and Hping3/);
  assert.match(placeholder,/Your agent, equipped/);
  assert.match(placeholder,/Your evidence, retained/);
  for(const name of ["claude.svg","cursor.svg","codex.png","hermes.png"]) assert.ok((await readFile(new URL(`../assets/brands/${name}`,import.meta.url))).length>100,name);
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
  const targets={runtime:{opacity:1,scale:1,filter:"grayscale(0)"},rows:Array.from({length:8},()=>({opacity:1,y:0})),bars:Array.from({length:3},()=>({scaleX:0})),request:{opacity:0,strokeDashoffset:1},response:{opacity:0,strokeDashoffset:1},noise:{opacity:1,x:0}};
  let stage="ready",replacing=false,stable=0;
  const loop=createArchitectureLoop(targets,value=>stage=value,value=>replacing=value,()=>stable++);
  try{
    assert.equal(loop.duration(),15);
    loop.totalTime(1,false);assert.equal(stage,"working");assert.ok(targets.bars[0].scaleX>targets.bars[2].scaleX);
    loop.totalTime(5.6,false);assert.equal(stage,"complete");assert.ok(targets.bars.every(bar=>Math.abs(bar.scaleX-1)<.001));
    loop.totalTime(7.2,false);assert.equal(stage,"stopping");assert.equal(replacing,true);
    loop.totalTime(8.41,false);assert.equal(stage,"stopped");assert.equal(targets.runtime.opacity,0);assert.ok(targets.rows.every(row=>row.opacity===0));
    loop.totalTime(9.09,false);assert.equal(stage,"stopped");assert.equal(targets.runtime.opacity,0);
    loop.totalTime(9.35,false);assert.equal(stage,"starting");assert.ok(targets.rows.at(-1).opacity>targets.rows[0].opacity,"rows arrive in reverse order");
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
test("the right-hand picker exposes each scenario once and selects the requested investigation",()=>{
  let selected;
  const props={cases:manifest.cases,activeScenario:"browser",onSelect:id=>selected=id};
  const markup=renderToStaticMarkup(createElement(ScenarioPicker,props));
  assert.match(markup,/<aside class="scenario-picker" aria-labelledby="scenario-heading">/);
  assert.match(markup,/<h2 id="scenario-heading">Scenarios<\/h2>/);
  assert.equal((markup.match(/<button /g)||[]).length,Object.keys(manifest.cases).length);
  assert.equal((markup.match(/aria-pressed="true"/g)||[]).length,1);
  for(const scenario of Object.values(manifest.cases))assert.ok(markup.includes(scenario.title));
  const options=ScenarioPicker(props).props.children[2].props.children;
  const target=options.find(button=>button.key==="website");
  target.props.onClick();
  assert.equal(selected,"website");
  assert.doesNotMatch(markup,/Preparing the workspace|story-observations|View report/);
});
test("the scenario picker handles recordings that have not loaded",()=>{
  const markup=renderToStaticMarkup(createElement(ScenarioPicker,{cases:{},activeScenario:"",onSelect:()=>{}}));
  assert.match(markup,/role="status"/);
  assert.match(markup,/Scenarios will appear when recordings are ready/);
  assert.doesNotMatch(markup,/<button /);
});
test("the old selector row, workflow panel and session-note banner stay removed",async()=>{
  const player=await readFile(new URL("../src/components/NativePlayer.tsx",import.meta.url),"utf8");
  const app=await readFile(new URL("../src/App.tsx",import.meta.url),"utf8");
  const styles=await readFile(new URL("../src/styles.css",import.meta.url),"utf8")+await readFile(new URL("../src/showcase.css",import.meta.url),"utf8");
  assert.equal((player.match(/<ScenarioPicker /g)||[]).length,1);
  assert.ok(player.indexOf('<div className="player-recording">')<player.indexOf('<ScenarioPicker '));
  assert.match(player,/onSelect=\{switchScenario\}/);
  assert.doesNotMatch(player,/scenario-tabs|scenario-pills|SessionStory/);
  assert.doesNotMatch(app,/session-note|Explore the architecture|Tools execute in disposable local Docker labs/);
  assert.doesNotMatch(styles,/\.session-note|\.scenario-tabs|\.scenario-pills|\.session-story|\.story-/);
});
test("the scrubber and progress bar share the full recording timeline",async()=>{
  const player=await readFile(new URL("../src/components/NativePlayer.tsx",import.meta.url),"utf8");
  assert.match(player,/r\.seek=Math\.max\(r\.minimum,Math\.min\(r\.end,next\)\)/);
  assert.match(player,/className="history-scroll"[^>]+max=\{Math\.max\(minimum\+\.001,end\)\}/);
  assert.match(player,/aria-label="Recording progress" value=\{Math\.max\(0,time-minimum\)\} max=\{Math\.max\(\.001,end-minimum\)\}/);
});
test("the support link finishes the footer and names its destination",async()=>{
  const app=await readFile(new URL("../src/App.tsx",import.meta.url),"utf8");
  assert.match(app,/const support = "https:\/\/buymeacoffee\.com\/mihirkatoch"/);
  assert.ok(app.indexOf('className="footer-toast wrap"')>app.indexOf('className="site-footer-bar wrap"'));
  assert.match(app,/className="footer-toast wrap" href=\{support\} target="_blank" rel="noopener noreferrer"/);
  assert.match(app,/Buy me a beer on Buy Me a Coffee \(opens in a new tab\)/);
  assert.match(app,/aria-label="Buy me a beer on Buy Me a Coffee \(opens in a new tab\)"/);
});
test("the showcased filtering example is produced by the registered Hercules filter",{skip:HERCULES_AVAILABLE?false:"Hercules package not present (website branch)"},async()=>{
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
