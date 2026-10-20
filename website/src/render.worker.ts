/// <reference lib="webworker" />
import { createRasterRenderer } from "../renderer.js";
const scope = self as unknown as DedicatedWorkerGlobalScope;
let renderer: ReturnType<typeof createRasterRenderer> | null = null,
  paused = true,
  reduced = false,
  clock = 0,
  last = performance.now(),
  lastFrame = 0,
  frames = 0,
  pointer: { x: number; y: number } | null = null;
scope.onmessage = ({ data }) => {
  if (data.type === "init") {
    renderer = createRasterRenderer(data.canvas, data.recipe, {
      width: data.width,
      height: data.height,
    });
    renderer.renderAt(0);
  }
  if (data.type === "resize" && renderer) {
    renderer.resize(data.width, data.height);
    renderer.renderAt(reduced ? 0 : clock, pointer);
  }
  if (data.type === "pointer") pointer = data.point;
  if (data.type === "state") {
    paused = data.paused;
    reduced = data.reduced;
    last = performance.now();
    if (reduced) renderer?.renderAt(0);
  }
};
setInterval(() => {
  const now = performance.now();
  if (!renderer || paused || reduced) {
    last = now;
    return;
  }
  const fps = renderer.getStats().averageCost > 40 ? 15 : 24;
  if (now - lastFrame < 1000 / fps) return;
  clock += Math.min(0.15, (now - last) / 1000);
  last = now;
  lastFrame = now;
  renderer.renderAt(clock, pointer);
  frames++;
  if (frames % 5 === 0)
    scope.postMessage({
      type: "stats",
      cost: renderer.getStats().averageCost,
      frames,
      timings: renderer.getStats().timings,
    });
}, 16);
