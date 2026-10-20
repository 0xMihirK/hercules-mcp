import test from "node:test";
import assert from "node:assert/strict";
import { createCanvas, Image } from "@napi-rs/canvas";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import {
  createRasterRenderer,
  RENDER_MODES,
  averageRect,
} from "../renderer.js";
import { createThreadLight } from "../thread-light.js";
globalThis.document = { createElement: () => createCanvas(1, 1) };
globalThis.Image = class extends Image {
  set src(value) {
    super.src = value.startsWith("data:")
      ? Buffer.from(value.split(",")[1], "base64")
      : value;
  }
};
globalThis.ResizeObserver = class {
  observe() {}
  disconnect() {}
};
const recipe = JSON.parse(
  await readFile(new URL("../recipe.json", import.meta.url), "utf8"),
);
const hash = (canvas) =>
  createHash("sha256").update(canvas.toBuffer("image/png")).digest("hex");
function render(changes = {}, time = 0) {
  const settings = structuredClone(recipe);
  Object.assign(settings, changes);
  const canvas = createCanvas(64, 48),
    engine = createRasterRenderer(canvas, settings, { width: 64, height: 48 });
  engine.renderAt(time);
  return { canvas, engine, digest: hash(canvas) };
}
test("all 25 primitives render distinct, nonempty rasters", () => {
  const rasters = new Set();
  for (const renderMode of RENDER_MODES) {
    const r = render({ renderMode });
    assert.ok(
      r.canvas
        .getContext("2d")
        .getImageData(0, 0, 64, 48)
        .data.some((v, i) => i % 4 === 3 && v > 0),
      renderMode,
    );
    rasters.add(r.digest);
    r.engine.destroy();
  }
  assert.ok(rasters.size >= 23, `${rasters.size} distinct primitive rasters`);
});
test("fixed frames are deterministic; animation, pointer, coverage and color controls affect pixels", () => {
  const initial = render(),
    second = render(),
    animated = render({}, 4);
  assert.equal(initial.digest, second.digest);
  assert.notEqual(initial.digest, animated.digest);
  initial.engine.renderAt(0, { x: 0.5, y: 0.5 });
  assert.notEqual(hash(initial.canvas), second.digest);
  for (const changes of [
    { coverage: 0 },
    { density: 70 },
    { invert: true },
    { edgeEmphasis: 100 },
    { brightness: 35 },
    { contrast: 50 },
    { grayscale: 0, saturation: 100 },
    { tintOpacity: 65, tint: "#3ca6ff", overlayBlend: "multiply" },
  ]) {
    const r = render(changes);
    assert.notEqual(r.digest, second.digest, JSON.stringify(changes));
    r.engine.destroy();
  }
  const empty = render({ coverage: 0, pfx: {} });
  assert.ok(
    empty.canvas
      .getContext("2d")
      .getImageData(0, 0, 64, 48)
      .data.every((v) => v === 0),
  );
  for (const r of [initial, second, animated, empty]) r.engine.destroy();
});
test("every enabled post effect and blur changes the raster", () => {
  const plainPfx = Object.fromEntries(
      Object.keys(recipe.pfx).map((key) => [
        key,
        { enabled: false, intensity: 70 },
      ]),
    ),
    baseline = render({ pfx: plainPfx });
  for (const key of Object.keys(plainPfx)) {
    const r = render(
      { pfx: { ...plainPfx, [key]: { enabled: true, intensity: 70 } } },
      1.7,
    );
    const sameTime = render({ pfx: plainPfx }, 1.7);
    assert.notEqual(r.digest, sameTime.digest, key);
    r.engine.destroy();
    sameTime.engine.destroy();
  }
  for (const blurType of [
    "gaussian",
    "lens",
    "tilt-shift",
    "directional",
    "zoom",
    "spin",
    "progressive",
  ]) {
    const r = render({ blurType, blurAmount: 70, pfx: plainPfx });
    assert.notEqual(r.digest, baseline.digest, blurType);
    r.engine.destroy();
  }
  const light = render({
    lights: {
      enabled: true,
      points: [{ x: 0.5, y: 0.5, radius: 0.4, intensity: 0.8 }],
    },
    pfx: plainPfx,
  });
  assert.notEqual(light.digest, baseline.digest);
  light.engine.destroy();
  baseline.engine.destroy();
});
test("mask reveals the procedural source, and inverting it changes the revealed region", async () => {
  const mask = createCanvas(64, 48),
    ctx = mask.getContext("2d");
  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, 32, 48);
  const masked = render({
      mask: {
        ...recipe.mask,
        enabled: true,
        dataUrl: mask.toDataURL("image/png"),
      },
    }),
    inverted = render({
      mask: {
        ...recipe.mask,
        enabled: true,
        invert: true,
        dataUrl: mask.toDataURL("image/png"),
      },
    });
  await Promise.all([masked.engine.ready, inverted.engine.ready]);
  masked.engine.renderAt(0);
  inverted.engine.renderAt(0);
  assert.notEqual(hash(masked.canvas), hash(inverted.canvas));
  masked.engine.destroy();
  inverted.engine.destroy();
});
test("rectangular samples include the entire halfblock; lifecycle stops drawing and resizes", () => {
  const pixels = new Uint8ClampedArray([255, 0, 0, 255, 0, 0, 255, 255]);
  assert.deepEqual(averageRect(pixels, 2, 1, 0, 0, 2, 1), [127.5, 0, 127.5]);
  const canvas = createCanvas(64, 48);
  let width = 64;
  canvas.getBoundingClientRect = () => ({ width, height: 48 });
  const engine = createThreadLight(canvas, recipe);
  engine.renderAt(0);
  engine.pause();
  const count = engine.getStats().renderedFrames;
  engine.update(1000);
  assert.equal(engine.getStats().renderedFrames, count);
  engine.resume();
  engine.update(1100);
  assert.ok(engine.getStats().renderedFrames > count);
  width = 80;
  engine.resize();
  assert.equal(canvas.width, 80);
  engine.destroy();
  const stopped = engine.getStats().renderedFrames;
  engine.renderAt(2);
  engine.update(3000);
  assert.equal(engine.getStats().renderedFrames, stopped);
});
