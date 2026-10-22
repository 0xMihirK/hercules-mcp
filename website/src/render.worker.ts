/// <reference lib="webworker" />
import { createRasterRenderer } from "../renderer.js";
const scope = self as unknown as DedicatedWorkerGlobalScope;
let renderer: ReturnType<typeof createRasterRenderer> | null = null,
  paused = true,
  reduced = false,
  clock = 0,
  last = performance.now(),
  timer: ReturnType<typeof setTimeout> | undefined,
  frames = 0,
  pointer: { x: number; y: number } | null = null;
function tick() {
  timer = undefined;
  if (!renderer || paused || reduced) return;
  const now = performance.now();
  clock += Math.min(0.15, (now - last) / 1000);
  last = now;
  renderer.renderAt(clock, pointer);
  frames++;
  if (frames % 5 === 0) scope.postMessage({
    type: "stats", cost: renderer.getStats().averageCost,
    frames, timings: renderer.getStats().timings,
  });
  const cost = performance.now() - now;
  // Leave CPU headroom for native playback even when one decorative frame is expensive.
  timer = setTimeout(tick, Math.max(1000 / 24 - cost, cost * 2));
}
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
    clearTimeout(timer);
    timer = undefined;
    paused = data.paused;
    reduced = data.reduced;
    last = performance.now();
    if (reduced) renderer?.renderAt(0);
    if (!paused && !reduced) timer = setTimeout(tick, 0);
  }
};
