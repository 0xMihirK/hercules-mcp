import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { loadImage } from "@napi-rs/canvas";
import ts from "typescript";
import { runInNewContext } from "node:vm";
import { nearViewport } from "../src/playback-loading.js";

const read = path => readFile(new URL(path, import.meta.url), "utf8");
test("sharing metadata is static, consistent, absolute and backed by a small JPEG", async () => {
  const html = await read("../index.html");
  const tags = new Map([...html.matchAll(/<meta\s+(?:name|property)="([^"]+)"\s+content="([^"]+)"\s*\/?>/g)].map(m => [m[1], m[2]]));
  const canonical = "https://0xmihirk.github.io/hercules-mcp/";
  assert.equal(tags.get("og:url"), canonical);
  assert.ok(html.includes(`<link rel="canonical" href="${canonical}"`));
  assert.equal(tags.get("og:site_name"), "Hercules MCP");
  assert.equal(tags.get("og:type"), "website");
  assert.equal(tags.get("twitter:card"), "summary_large_image");
  assert.equal(tags.get("twitter:title"), tags.get("og:title"));
  assert.equal(tags.get("og:title"), "Hercules MCP — A Kali workspace for your AI agent");
  assert.equal(tags.get("twitter:description"), tags.get("og:description"));
  assert.equal(tags.get("description"), tags.get("og:description"));
  assert.equal(tags.get("twitter:image"), tags.get("og:image"));
  assert.equal(tags.get("twitter:image:alt"), tags.get("og:image:alt"));
  assert.ok(tags.get("og:image:alt").length > 20);
  assert.equal(tags.get("og:image"), canonical + "assets/social-preview-v2.jpg");
  assert.equal(tags.get("og:image:type"), "image/jpeg");
  assert.equal(tags.get("og:image:width"), "1200");
  assert.equal(tags.get("og:image:height"), "630");
  const jpeg = await readFile(new URL("../assets/social-preview-v2.jpg", import.meta.url));
  assert.deepEqual([...jpeg.subarray(0, 3)], [255, 216, 255]);
  assert.ok(jpeg.length <= 250 * 1024);
  const image = await loadImage(jpeg);
  assert.deepEqual([image.width, image.height], [1200, 630]);
  assert.equal(createHash("sha256").update(await readFile(new URL("../assets/social-preview.png", import.meta.url))).digest("hex"), "d7a1c2fe2fd54be486ac13dc802357d6f4edfe24eb0edf75012ce4737da1faac");
});

test("compact catalog preserves every session, timing and verified poster without provenance bloat", async () => {
  const source = JSON.parse(await read("../assets/recordings/manifest.json"));
  const bytes = execFileSync("python", ["-c", "import json,sys; from pathlib import Path; sys.path.insert(0,'scripts'); from playback_catalog import playback_catalog; p=Path('assets/recordings'); print(json.dumps(playback_catalog(json.loads((p/'manifest.json').read_text()),p,json.loads(Path('src/showcase-content.json').read_text())),separators=(',',':')))"], { cwd: new URL("../", import.meta.url), maxBuffer: 512 * 1024 });
  const catalog = JSON.parse(bytes);
  assert.ok(bytes.length < 150 * 1024);
  assert.equal(catalog.recordings.length, 120);
  assert.equal(Object.keys(catalog.clients).length, 4);
  assert.equal(Object.keys(catalog.cases).length, 10);
  assert.equal(catalog.realTools, true);
  assert.equal(catalog.scriptedToolResults, false);
  assert.equal(catalog.playbackSpeed, source.playbackSpeed);
  assert.equal(catalog.assetDirectory, "recordings");
  for (const [i, record] of catalog.recordings.entries()) {
    const original = source.recordings[i];
    for (const key of Object.keys(record).filter(key => !["pixels", "entrance"].includes(key))) assert.deepEqual(record[key], original[key], original.file + ": " + key);
    assert.deepEqual(Object.keys(record.pixels).sort(), ["fps", "height", "index", "indexSha256", "width"]);
    for (const key of Object.keys(record.pixels)) assert.deepEqual(record.pixels[key], original.pixels[key]);
    if (record.client === "hermes") {
      const index = JSON.parse(await read("../assets/recordings/" + record.pixels.index));
      assert.equal(record.entrance.sha256, index.reviewFrames.nativeIntro.sha256);
      assert.equal(record.entrance.at, index.reviewFrames.nativeIntro.at);
      assert.equal(createHash("sha256").update(await readFile(new URL("../assets/recordings/" + record.entrance.file, import.meta.url))).digest("hex"), record.entrance.sha256);
    }
  }
  assert.doesNotMatch(bytes.toString(), /captureConfiguration|harnessSha256|recordingArchive|synchronized|reportPreview/);
  const app = await read("../src/App.tsx");
  assert.doesNotMatch(app, /manifest\.json|cache:\s*"no-store"/);
  assert.match(app, /fetch\(recordingBase \+ bootstrap.catalogFile/);
  assert.doesNotMatch(app, /asset\("lion\.svg"\)/);
  assert.match(app, /blob\/website\/website\/CAPTURE\.md/);
  const player = await read("../src/components/NativePlayer.tsx");
  assert.doesNotMatch(player, /warmEntrances|showcase-content\.json/);
  assert.match(player, /blob\/website\/website\/CAPTURE\.md/);
  const architecture = await read("../src/components/ArchitectureScene.tsx");
  assert.match(architecture, /Browser traffic is not confined/);
  assert.match(architecture, /does not enforce CSP/);
  assert.doesNotMatch(architecture, /candidate confines|validating gateway and firewall/);
  assert.ok(player.indexOf("await poster(file,sha)") < player.indexOf("await nearViewport"));
  assert.ok(player.indexOf("await nearViewport") < player.indexOf("verifiedFetch(base+source.index"));
});

test("a replacement manifest supplies its own objective while old captures retain their copy", () => {
  const code = "from pathlib import Path;import sys;sys.path.insert(0,'scripts');from playback_catalog import playback_catalog;m={'schemaVersion':3,'playbackSpeed':2.5,'realTools':True,'scriptedToolResults':False,'clients':{'claude':{'version':'fixture'}},'cases':{'network':{'title':'New','objective':'New objective'}},'recordings':[]};old={'network':{'objective':'Old objective'}};print(playback_catalog(m,Path('.'),old)['cases']['network']['objective']);del m['cases']['network']['objective'];print(playback_catalog(m,Path('.'),old)['cases']['network']['objective'])";
  const result=execFileSync("python",["-c",code],{cwd:new URL("../",import.meta.url),encoding:"utf8"});
  assert.deepEqual(result.trim().split(/\r?\n/),["New objective","Old objective"]);
});

test("offscreen playback waits, releases observers, and cancels before downloading frames", async t => {
  const previous = globalThis.IntersectionObserver;
  let callback, disconnected = 0, observed;
  globalThis.IntersectionObserver = class {
    constructor(fn, options) { callback = fn; assert.equal(options.rootMargin, "300px"); }
    observe(element) { observed = element; }
    disconnect() { disconnected++; }
  };
  t.after(() => { globalThis.IntersectionObserver = previous; });
  const element = {}, abort = new AbortController();
  let ready = false;
  const pending = nearViewport(element, abort.signal).then(() => { ready = true; });
  assert.equal(observed, element);
  callback([{ isIntersecting: false }]);
  await Promise.resolve(); assert.equal(ready, false);
  callback([{ isIntersecting: true }]);
  await pending; assert.equal(ready, true); assert.equal(disconnected, 1);
  const cancelled = new AbortController(), wait = nearViewport(element, cancelled.signal);
  cancelled.abort(); await assert.rejects(wait, { name: "AbortError" });
  await assert.rejects(nearViewport(element, cancelled.signal), { name: "AbortError" });
  delete globalThis.IntersectionObserver;
  await nearViewport(element, new AbortController().signal);
});

test("decorative worker parks while hidden and leaves headroom after expensive frames", async () => {
  const source = (await read("../src/render.worker.ts")).replace('import { createRasterRenderer } from "../renderer.js";', "");
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText.replace(/export \{\};?/, "");
  let now = 0, queued, delay, paints = 0;
  const scope = { postMessage() {} };
  const renderer = { renderAt() { now += 120; paints++; }, resize() {}, getStats() { return { averageCost: 120, timings: {} }; } };
  runInNewContext(code, { self: scope, performance: { now: () => now }, createRasterRenderer: () => renderer, setTimeout(fn, ms) { queued = fn; delay = ms; return 1; }, clearTimeout() { queued = undefined; } });
  scope.onmessage({ data: { type: "init", canvas: {}, recipe: {}, width: 100, height: 100 } });
  assert.equal(paints, 1); assert.equal(queued, undefined);
  scope.onmessage({ data: { type: "state", paused: false, reduced: false } });
  queued(); assert.equal(paints, 2); assert.equal(delay, 240);
  scope.onmessage({ data: { type: "state", paused: true, reduced: false } });
  assert.equal(queued, undefined);
  scope.onmessage({ data: { type: "state", paused: false, reduced: true } });
  assert.equal(queued, undefined); assert.equal(paints, 3);
  scope.onmessage({ data: { type: "state", paused: false, reduced: false } });
  assert.equal(typeof queued, "function");
});
