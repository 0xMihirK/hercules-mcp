import { useEffect, useRef } from "react";
import recipe from "../../recipe.json";
import { createThreadLight } from "../../thread-light.js";
export default function Background({
  paused,
  reduced,
}: {
  paused: boolean;
  reduced: boolean;
}) {
  const host = useRef<HTMLDivElement>(null),
    control = useRef<(paused: boolean, reduced: boolean) => void>(() => {});
  useEffect(() => {
    if (!host.current) return;
    const parent = host.current,
      canvas = document.createElement("canvas");
    canvas.style.cssText = "width:100%;height:100%;display:block";
    parent.append(canvas);
    let worker: Worker | null = null,
      renderer: ReturnType<typeof createThreadLight> | null = null,
      frame = 0;
    const resize = () => {
      const rect = parent.getBoundingClientRect();
      worker?.postMessage({
        type: "resize",
        width: rect.width,
        height: rect.height,
      });
      renderer?.resize();
    };
    if ("transferControlToOffscreen" in canvas) {
      const surface = canvas.transferControlToOffscreen(),
        rect = parent.getBoundingClientRect();
      worker = new Worker(new URL("../render.worker.ts", import.meta.url), {
        type: "module",
      });
      worker.postMessage(
        {
          type: "init",
          canvas: surface,
          recipe,
          width: rect.width,
          height: rect.height,
        },
        [surface],
      );
      worker.onmessage = ({ data }) => {
        if (data.type === "stats") {
          parent.dataset.renderMs = data.cost.toFixed(2);
          parent.dataset.frame = String(data.frames);
          parent.dataset.timings = JSON.stringify(data.timings);
        }
      };
      control.current = (paused, reduced) =>
        worker?.postMessage({
          type: "state",
          paused: paused || document.hidden,
          reduced,
        });
    } else {
      renderer = createThreadLight(canvas, recipe);
      let stopped = false;
      const tick = (time: number) => {
        if (!stopped) renderer?.update(time);
        frame = requestAnimationFrame(tick);
      };
      frame = requestAnimationFrame(tick);
      control.current = (paused, reduced) => {
        stopped = paused || reduced || document.hidden;
        if (reduced) renderer?.renderAt(0);
      };
    }
    const pointer = (event: PointerEvent) => {
      if (event.pointerType === "touch") return;
      const point = {
        x: event.clientX / innerWidth,
        y: event.clientY / innerHeight,
      };
      worker?.postMessage({ type: "pointer", point });
      renderer?.setPointer(point);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(parent);
    window.addEventListener("pointermove", pointer, { passive: true });
    control.current(paused, reduced);
    return () => {
      worker?.terminate();
      renderer?.destroy();
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("pointermove", pointer);
      canvas.remove();
    };
  }, []);
  useEffect(() => {
    control.current(paused, reduced);
    const visibility = () => control.current(paused, reduced);
    document.addEventListener("visibilitychange", visibility);
    return () => document.removeEventListener("visibilitychange", visibility);
  }, [paused, reduced]);
  return <div ref={host} className="thread-background" aria-hidden="true" />;
}
