import { createCanvas, GlobalFonts, loadImage } from "@napi-rs/canvas";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { createRasterRenderer } from "../renderer.js";
const asset = (name) => new URL(`../assets/${name}`, import.meta.url);
GlobalFonts.registerFromPath(
  fileURLToPath(asset("fonts/archivo-latin-variable.woff2")),
  "Archivo",
);
GlobalFonts.registerFromPath(
  fileURLToPath(asset("fonts/ibm-plex-mono-latin-400.woff2")),
  "Plex Mono",
);
globalThis.document = { createElement: () => createCanvas(1, 1) };
const recipe = JSON.parse(
  await readFile(new URL("../recipe.json", import.meta.url), "utf8"),
);
const emberRecipe = {
  ...recipe,
  tint: "#ff6a2b",
  tintOpacity: 52,
  overlayBlend: "multiply",
};
const raster = createCanvas(1200, 630),
  engine = createRasterRenderer(raster, emberRecipe, {
    width: 1200,
    height: 630,
  });
engine.renderAt(0);
const canvas = createCanvas(1200, 630),
  ctx = canvas.getContext("2d");
ctx.fillStyle = "#07080a";
ctx.fillRect(0, 0, 1200, 630);
ctx.globalAlpha = 0.46;
ctx.drawImage(raster, 0, 0);
ctx.globalAlpha = 1;
const scrim = ctx.createLinearGradient(0, 0, 1200, 0);
scrim.addColorStop(0, "rgba(7,8,10,.88)");
scrim.addColorStop(1, "rgba(7,8,10,.25)");
ctx.fillStyle = scrim;
ctx.fillRect(0, 0, 1200, 630);
ctx.drawImage(
  await loadImage(fileURLToPath(asset("lion.png"))),
  62,
  56,
  44,
  44,
);
ctx.fillStyle = "#F4EFE9";
ctx.font = "600 25px Archivo";
ctx.fillText("hercules / mcp", 124, 88);
ctx.fillStyle = "#F4EFE9";
ctx.font = "600 86px Archivo";
ctx.fillText("A Kali workspace", 59, 286);
ctx.fillText("for your", 59, 382);
const prefixWidth = ctx.measureText("for your ").width;
ctx.fillStyle = "#FF6A2B";
ctx.fillText("AI agent.", Math.round(59 + prefixWidth), 382);
ctx.fillStyle = "#CEC5BC";
ctx.font = "15px Plex Mono";
ctx.fillText("Security tools. Browser automation. Your agent.", 64, 470);
ctx.strokeStyle = "rgba(244,239,233,0.16)";
ctx.beginPath();
ctx.moveTo(64, 550);
ctx.lineTo(1136, 550);
ctx.stroke();
ctx.fillStyle = "#B8AFA6";
ctx.font = "11px Plex Mono";
ctx.fillText("OPEN SOURCE / KALI LINUX / DOCKER", 64, 584);
ctx.fillStyle = "#FF6A2B";
ctx.fillText("0xmihirk.github.io/hercules-mcp", 825, 584);
const jpeg = canvas.toBuffer("image/jpeg", 88);
if (jpeg.length > 250 * 1024) throw Error("Social preview exceeds the 250 KiB budget");
await writeFile(asset("social-preview-v2.jpg"), jpeg);
engine.destroy();
console.log(`Generated 1200×630 social preview (${jpeg.length} bytes); original PNG retained.`);
