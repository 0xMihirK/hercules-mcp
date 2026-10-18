import { useEffect, useRef } from "react";
import recipe from "../../recipe.json";
import { createThreadLight } from "../../thread-light.js";
import { createEmberField, type EmberFieldController } from "../ember-field";

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
      fallbackRenderer: ReturnType<typeof createThreadLight> | null = null,
      ember: EmberFieldController | null = null,
      frame = 0,
      stopped = false,
      lastTick = 0,
      sampleCount = 0,
      sampleCost = 0;

    const startFallback = (targetCanvas: HTMLCanvasElement) => {
      parent.dataset.renderer = "canvas-fallback";
      targetCanvas.style.cssText =
        "width:100%;height:100%;display:block;filter:sepia(1) saturate(3.4) hue-rotate(-24deg) brightness(0.95) contrast(1.25)";
      const rect = parent.getBoundingClientRect();
      if ("transferControlToOffscreen" in targetCanvas && typeof Worker === "function") {
        const surface = targetCanvas.transferControlToOffscreen();
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
        control.current = (isPaused, isReduced) =>
          worker?.postMessage({
            type: "state",
            paused: isPaused || document.hidden,
            reduced: isReduced,
          });
      } else {
        fallbackRenderer = createThreadLight(targetCanvas, recipe);
        const tick = (time: number) => {
          if (stopped) {
            frame = 0;
            return;
          }
          fallbackRenderer?.update(time);
          frame = requestAnimationFrame(tick);
        };
        frame = requestAnimationFrame(tick);
        control.current = (isPaused, isReduced) => {
          stopped = isPaused || isReduced || document.hidden;
          if (isReduced) fallbackRenderer?.renderAt(0);
          if (!stopped && !frame) frame = requestAnimationFrame(tick);
        };
      }
    };

    ember = createEmberField(canvas);
    if (ember) {
      parent.dataset.renderer = "webgl-ember";
      ember.frame(4200);
      const tick = (time: number) => {
        if (stopped || !ember) {
          frame = 0;
          return;
        }
        if (time - lastTick >= 28) {
          lastTick = time;
          const cost = ember.frame(time + 4200);
          parent.dataset.renderMs = cost.toFixed(2);
          if (sampleCount < 30) {
            sampleCount++;
            sampleCost += cost;
            if (sampleCount === 30 && sampleCost / 30 > 22) {
              ember.destroy();
              ember = null;
              const replacement = document.createElement("canvas");
              canvas.replaceWith(replacement);
              startFallback(replacement);
              control.current(paused, reduced);
              return;
            }
          }
        }
        frame = requestAnimationFrame(tick);
      };
      control.current = (isPaused, isReduced) => {
        stopped = isPaused || isReduced || document.hidden;
        if (stopped) {
          if (frame) {
            cancelAnimationFrame(frame);
            frame = 0;
          }
          ember?.frame(4200);
        } else if (!frame) {
          frame = requestAnimationFrame(tick);
        }
      };
    } else {
      startFallback(canvas);
    }

    const resize = () => {
      const rect = parent.getBoundingClientRect();
      ember?.resize(rect.width, rect.height);
      if (stopped) ember?.frame(4200);
      worker?.postMessage({
        type: "resize",
        width: rect.width,
        height: rect.height,
      });
      fallbackRenderer?.resize();
    };

    const pointer = (event: PointerEvent) => {
      if (event.pointerType === "touch") return;
      const point = {
        x: event.clientX / Math.max(1, innerWidth),
        y: event.clientY / Math.max(1, innerHeight),
      };
      ember?.setPointer(point);
      worker?.postMessage({ type: "pointer", point });
      fallbackRenderer?.setPointer(point);
    };

    const onScroll = () => {
      if (!ember) return;
      const maxScroll = Math.max(1, document.documentElement.scrollHeight - innerHeight);
      const progress = Math.max(0, Math.min(1, scrollY / maxScroll));
      ember.setScroll(progress);
      // Bright in the hero (0..0.18) and footer (0.85..1.0), calmer behind dense mid-page reading
      const heroBoost = Math.max(0, 1 - progress / 0.22) * 0.36;
      const footerBoost = Math.max(0, (progress - 0.8) / 0.2) * 0.38;
      ember.setIntensity(0.74 + heroBoost + footerBoost);
    };

    const observer = new ResizeObserver(resize);
    observer.observe(parent);
    window.addEventListener("pointermove", pointer, { passive: true });
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    control.current(paused, reduced);

    return () => {
      ember?.destroy();
      worker?.terminate();
      fallbackRenderer?.destroy();
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener("pointermove", pointer);
      window.removeEventListener("scroll", onScroll);
      parent.replaceChildren();
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
