import { useEffect, useRef, useState } from "react";
import { Terminal as XTerm } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import { useInView } from "motion/react";
import { Terminal } from "./ui/terminal";
import {
  parseRecording,
  RecordingCursor,
  RecordingWriter,
} from "../recording.js";
import {
  profiles,
  scenarios,
  type Client,
  type Scenario,
} from "../recording-profiles";

const cache = new Map<string, ReturnType<typeof parseRecording>>();
export default function AgentTerminal({
  client,
  paused,
  reduced,
}: {
  client: Client;
  paused: boolean;
  reduced: boolean;
}) {
  const card = useRef<HTMLDivElement>(null),
    host = useRef<HTMLDivElement>(null),
    viewport = useRef<HTMLDivElement>(null),
    openButton = useRef<HTMLButtonElement>(null);
  const [scenario, setScenario] = useState<Scenario>("scan"),
    [localPaused, setLocalPaused] = useState(false),
    [expanded, setExpanded] = useState(false),
    [replay, setReplay] = useState(0);
  const [motionOverride, setMotionOverride] = useState(false);
  const [mobile, setMobile] = useState(() => innerWidth < 800),
    [error, setError] = useState(""),
    [ready, setReady] = useState(false),
    [progress, setProgress] = useState(0);
  const elapsed = useRef(0),
    generationRef = useRef(0),
    visible = useInView(card, { amount: 0.08 });
  const flags = useRef({
    paused,
    reduced,
    motionOverride,
    localPaused,
    visible,
    expanded,
  });
  flags.current = {
    paused,
    reduced,
    motionOverride,
    localPaused,
    visible,
    expanded,
  };
  const still = reduced && !motionOverride;
  const stopped = localPaused || still;
  const profile = profiles[client];
  useEffect(() => {
    const query = matchMedia("(max-width: 799px)");
    const update = () => setMobile(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    const generation = ++generationRef.current,
      abort = new AbortController();
    let terminal: XTerm | undefined,
      observer: ResizeObserver | undefined,
      frame = 0,
      cursor: RecordingCursor | undefined,
      writer: RecordingWriter | undefined,
      last: number | null = null,
      updateAt = 0;
    const visibilityChanged = () => {
      last = null;
    };
    document.addEventListener("visibilitychange", visibilityChanged);
    const valid = () =>
      generation === generationRef.current && !abort.signal.aborted;
    setReady(false);
    setError("");
    async function initialize() {
      try {
        const url = `${import.meta.env.BASE_URL}assets/recordings/${client}-${scenario}-${mobile ? 80 : 120}.cast`;
        const fontReady = document.fonts.load('12px "IBM Plex Mono"');
        let recording = cache.get(url);
        if (!recording) {
          const response = await fetch(url, { signal: abort.signal });
          if (!response.ok) throw new Error("Recording unavailable");
          recording = parseRecording(await response.text());
          cache.set(url, recording);
        }
        await fontReady;
        const duration = recording.duration;
        if (!valid() || !host.current || !viewport.current) return;
        cursor = new RecordingCursor(recording);
        terminal = new XTerm({
          cols: recording.header.width,
          rows: recording.header.height,
          fontFamily: '"IBM Plex Mono", monospace',
          fontSize: 12,
          lineHeight: 1,
          letterSpacing: 0,
          convertEol: false,
          disableStdin: true,
          cursorBlink: false,
          scrollback: 0,
          minimumContrastRatio: 1,
          theme: {
            background: profile.background,
            foreground: "#eeeeee",
            cursor: "#eeeeee",
          },
        });
        terminal.open(host.current);
        terminal.textarea?.setAttribute("tabindex", "-1");
        const size = () => {
          if (
            !host.current ||
            !viewport.current ||
            !terminal?.element ||
            !valid()
          )
            return;
          const screen =
            host.current.querySelector<HTMLElement>(".xterm-screen");
          if (!screen) return;
          const width = screen.offsetWidth,
            height = screen.offsetHeight;
          if (!width || !height) return;
          const scale = Math.min(
            viewport.current.clientWidth / width,
            viewport.current.clientHeight / height,
            flags.current.expanded ? 1.6 : 1.15,
          );
          host.current.style.width = `${width}px`;
          host.current.style.height = `${height}px`;
          host.current.style.transform = `translate(-50%, -50%) scale(${scale})`;
        };
        observer = new ResizeObserver(size);
        observer.observe(viewport.current);
        size();
        elapsed.current = Math.min(
          flags.current.reduced && !flags.current.motionOverride
            ? recording.duration
            : elapsed.current,
          recording.duration,
        );
        await new Promise<void>((resolve) =>
          terminal!.write(cursor!.drain(elapsed.current), resolve),
        );
        if (!valid()) return;
        writer = new RecordingWriter(
          cursor,
          (output: string, done: () => void) => terminal!.write(output, done),
        );
        size();
        setReady(true);
        function tick(timestamp: number) {
          if (!valid() || !cursor || !terminal) return;
          const f = flags.current,
            active =
              !f.paused &&
              !f.localPaused &&
              (!f.reduced || f.motionOverride) &&
              (f.visible || f.expanded) &&
              !document.hidden;
          if (active) {
            if (last !== null) elapsed.current += (timestamp - last) / 1000;
            if (writer) {
              writer.writeAt(elapsed.current);
              if (cursor.finished && !writer.pending) {
                elapsed.current = 0;
                setScenario(
                  (current) =>
                    scenarios[
                      (scenarios.findIndex((item) => item.id === current) + 1) %
                        scenarios.length
                    ].id,
                );
                return;
              }
            }
          }
          last = active ? timestamp : null;
          if (timestamp - updateAt > 500) {
            updateAt = timestamp;
            setProgress(Math.min(100, (elapsed.current / duration) * 100));
          }
          frame = requestAnimationFrame(tick);
        }
        frame = requestAnimationFrame(tick);
      } catch {
        if (valid()) setError("Could not load this recording.");
      }
    }
    initialize();
    return () => {
      document.removeEventListener("visibilitychange", visibilityChanged);
      abort.abort();
      generationRef.current++;
      writer?.cancel();
      cancelAnimationFrame(frame);
      observer?.disconnect();
      terminal?.dispose();
      host.current?.replaceChildren();
    };
  }, [client, scenario, mobile, replay, reduced, profile.background]);
  useEffect(() => {
    if (!expanded) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setExpanded(false);
      }
      if (event.key === "Tab") {
        const controls = card.current?.querySelectorAll<HTMLElement>(
          "button:not(:disabled),select:not(:disabled)",
        );
        if (!controls?.length) return;
        const first = controls[0],
          last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    openButton.current?.focus();
    document.addEventListener("keydown", key);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener("keydown", key);
      openButton.current?.focus();
    };
  }, [expanded]);
  function restart() {
    elapsed.current = 0;
    setProgress(0);
    setReplay((n) => n + 1);
  }
  return (
    <div
      ref={card}
      className={`agent-card ${expanded ? "agent-expanded" : ""}`}
      role={expanded ? "dialog" : "group"}
      aria-modal={expanded || undefined}
      aria-label={`${profile.name} recorded demonstration`}
    >
      <Terminal
        sequence={false}
        header={
          <div className="agent-toolbar">
            <div className="agent-name">
              <span style={{ color: profile.accent }}>
                {client === "hermes"
                  ? "☤"
                  : client === "codex"
                    ? ">_"
                    : client === "opencode"
                      ? "◧"
                      : "✳"}
              </span>
              {profile.name}
              <small>{profile.version}</small>
            </div>
            <div className="agent-actions">
              <button
                disabled={paused || !ready}
                title={
                  paused
                    ? "Resume animations using the page control"
                    : stopped
                      ? "Play"
                      : "Pause"
                }
                aria-label={`${stopped ? "Play" : "Pause"} ${profile.name}`}
                onClick={() => {
                  if (still) {
                    setMotionOverride(true);
                    setLocalPaused(false);
                    restart();
                  } else setLocalPaused(!localPaused);
                }}
              >
                {stopped ? "▷" : "Ⅱ"}
              </button>
              <button
                title="Replay"
                aria-label={`Replay ${profile.name}`}
                onClick={restart}
              >
                ↺
              </button>
              <button
                ref={openButton}
                title={expanded ? "Close" : "Enlarge"}
                aria-label={`${expanded ? "Close" : "Enlarge"} ${profile.name}`}
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? "×" : "⛶"}
              </button>
            </div>
          </div>
        }
        body={
          <div
            className="terminal-viewport"
            ref={viewport}
            style={{ background: profile.background }}
          >
            <div className="terminal-recording" ref={host} aria-hidden="true" />
            {!ready && (
              <div className="recording-state mono" role="status">
                {error || "Loading native recording…"}
                {error && <button onClick={restart}>Try again</button>}
              </div>
            )}
          </div>
        }
      />
      <div className="recording-controls">
        <label className="sr-only" htmlFor={`example-${client}`}>
          {profile.name} example
        </label>
        <select
          id={`example-${client}`}
          value={scenario}
          onChange={(event) => {
            elapsed.current = 0;
            setProgress(0);
            setScenario(event.target.value as Scenario);
          }}
        >
          {scenarios.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <span className="mono">
          {still
            ? "Still frame"
            : paused || localPaused
              ? "Paused"
              : "Recorded · 1×"}
        </span>
      </div>
      <div className="recording-progress" aria-hidden="true">
        <div style={{ width: `${progress}%`, background: profile.accent }} />
      </div>
      <p className="sr-only">
        Native terminal interface with scripted example results. Use the example
        selector and playback controls.
      </p>
    </div>
  );
}
