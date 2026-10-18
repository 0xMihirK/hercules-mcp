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
  tintOpacity: 72,
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
ctx.globalAlpha = 0.72;
ctx.drawImage(raster, 0, 0);
ctx.globalAlpha = 1;
const scrim = ctx.createLinearGradient(0, 0, 1200, 0);
scrim.addColorStop(0, "rgba(7,8,10,.78)");
scrim.addColorStop(1, "rgba(7,8,10,.18)");
ctx.fillStyle = scrim;
ctx.fillRect(0, 0, 1200, 630);
ctx.drawImage(
  await loadImage(fileURLToPath(asset("lion.png"))),
  62,
  48,
  36,
  36,
);
ctx.fillStyle = "#F4EFE9";
ctx.font = "600 25px Archivo";
ctx.fillText("hercules / mcp", 112, 76);
ctx.fillStyle = "#FFB48A";
ctx.font = "12px Plex Mono";
ctx.fillText("OPEN SOURCE / MODEL CONTEXT PROTOCOL", 64, 180);
ctx.fillStyle = "#F4EFE9";
ctx.font = "600 86px Archivo";
ctx.fillText("A Kali workspace", 59, 286);
ctx.fillText("for your", 59, 382);
const prefixWidth = ctx.measureText("for your ").width;
ctx.fillStyle = "#FF6A2B";
ctx.fillText("AI agent.", Math.round(59 + prefixWidth), 382);
ctx.fillStyle = "#CEC5BC";
ctx.font = "15px Plex Mono";
ctx.fillText("47 tools     22 capability bundles     7 resources", 64, 504);
ctx.strokeStyle = "rgba(244,239,233,0.16)";
ctx.beginPath();
ctx.moveTo(64, 550);
ctx.lineTo(1136, 550);
ctx.stroke();
ctx.fillStyle = "#B8AFA6";
ctx.font = "11px Plex Mono";
ctx.fillText("PYTHON / DOCKER / KALI LINUX", 64, 584);
ctx.fillStyle = "#FF6A2B";
ctx.fillText("github.com/0xMihirK/hercules-mcp", 821, 584);
await writeFile(asset("social-preview.png"), canvas.toBuffer("image/png"));
engine.destroy();
console.log("Generated the social preview from the procedural background.");
