import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { gzipSync } from "node:zlib";
import { createHash } from "node:crypto";

const dist = new URL("../dist/", import.meta.url);
const html = await readFile(new URL("index.html", dist), "utf8");
const llms = await readFile(new URL("llms.txt", dist), "utf8");
const markdown = await readFile(new URL("index.md", dist), "utf8");
const installPrompt = await readFile(new URL("install.txt", dist), "utf8");
assert.match(html, /AI agents: installation and runtime guidance is at https:\/\/0xmihirk\.github\.io\/hercules-mcp\/llms\.txt/);
assert.match(html, /rel="alternate" type="text\/markdown" href="\.\/index\.md"/);
assert.match(llms, /system_start_container[\s\S]*system_stop_container/);
assert.match(markdown, /^# Hercules MCP\n/);
assert.match(markdown, /https:\/\/github\.com\/0xMihirK\/hercules-mcp\/blob\/main\/install\.md/);
assert.match(installPrompt, /prebuilt image \(recommended\) or local build/);
assert.match(markdown, /--image-source prebuilt/);
const scripts = (await readdir(new URL("assets/", dist))).filter(file => file.endsWith(".js"));
let total = 0;
for (const file of scripts) total += gzipSync(await readFile(new URL("assets/" + file, dist))).length;
assert.ok(total <= 160 * 1024, `All website JavaScript exceeds 160 KiB gzip: ${total} bytes`);
assert.match(html, /og:image:width" content="1200"/);
assert.match(html, /og:image:height" content="630"/);
const bootstrap = JSON.parse(await readFile(new URL("../src/bootstrap.json", import.meta.url), "utf8"));
assert.equal(bootstrap.recordings.length, 0, "Playback records must not be embedded in JavaScript");
const catalogBytes = await readFile(new URL(`assets/${bootstrap.assetDirectory}/${bootstrap.catalogFile}`, dist));
assert.equal(bootstrap.catalogFile, `playback-${createHash("sha256").update(catalogBytes).digest("hex").slice(0, 16)}.json`);
const catalog = JSON.parse(catalogBytes);
assert.equal(catalog.recordings.length, 120);
assert.equal(Object.keys(catalog.cases).length, 10);
assert.equal(Object.keys(catalog.clients).length, 4);
for (const match of html.matchAll(/<link[^>]+rel="preload"[^>]+href="([^"]+)"/g)) {
  const path = match[1];
  assert.ok(path.startsWith("./assets/") && path.endsWith(".woff2"), `Unexpected font preload: ${path}`);
  await readFile(new URL(path, dist));
}
console.log(`All JavaScript: ${(total / 1024).toFixed(1)} KiB gzip (160 KiB budget); static metadata and font preloads verified.`);
