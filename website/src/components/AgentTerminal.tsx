import { useEffect, useRef, useState } from "react";
import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { useInView } from "motion/react";
import { Terminal } from "./ui/terminal";
import {
  DEMO_PROMPT,
  profiles,
  initialSession,
  handleInput,
  renderScreen,
  execute,
  type Client,
} from "../client-sandbox";
export default function AgentTerminal({
  client,
  offset,
  paused,
  reduced,
  tools = [],
}: {
  client: Client;
  offset: number;
  paused: boolean;
  reduced: boolean;
  tools?: string[];
}) {
  const card = useRef<HTMLDivElement>(null),
    host = useRef<HTMLDivElement>(null),
    terminal = useRef<XTerm | null>(null);
  const session = useRef(initialSession(client)),
    clock = useRef(0),
    last = useRef<number | null>(null),
    playing = useRef(true),
    takingOver = useRef(false);
  const [localPaused, setLocalPaused] = useState(false),
    [expanded, setExpanded] = useState(false),
    [replay, setReplay] = useState(0),
    [interactive, setInteractive] = useState(false),
    [status, setStatus] = useState(
      "Hercules MCP connected. 46 tools available.",
    );
  const paintKey = useRef(""),
    openButton = useRef<HTMLButtonElement>(null),
    toolNames = useRef(tools);
  toolNames.current = tools;
  const visible = useInView(card, { amount: 0.08 }),
    flags = useRef({ paused, reduced, visible, localPaused });
  flags.current = { paused, reduced, visible, localPaused };
  const p = profiles[client];
  useEffect(() => {
    if (!host.current) return;
    const term = new XTerm({
      fontFamily: '"IBM Plex Mono", "Cascadia Mono", Consolas, monospace',
      fontSize: innerWidth < 800 ? 11 : 12,
      lineHeight: 1.35,
      letterSpacing: 0,
      cursorBlink: !reduced,
      scrollback: 100,
      convertEol: true,
      theme: {
        background: p.background,
        foreground: client === "hermes" ? "#FFF8DC" : "#eeeeee",
        cursor: p.accent,
        selectionBackground: "#636b7655",
      },
      allowProposedApi: false,
      screenReaderMode: false,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(host.current);
    terminal.current = term;
    const paint = () => {
      const output = renderScreen(
        session.current,
        client,
        term.cols,
        term.rows,
        clock.current,
        false,
        toolNames.current,
      );
      if (output !== paintKey.current) {
        term.write(output);
        paintKey.current = output;
      }
    };
    const resize = () => {
      try {
        fit.fit();
        paintKey.current = "";
        paint();
      } catch {}
    };
    const observer = new ResizeObserver(resize);
    observer.observe(host.current);
    document.fonts.ready.then(resize);
    resize();
    const input = term.onData((data) => {
      if (playing.current && !takingOver.current)
        session.current = { ...session.current, input: "", cursor: 0 };
      takingOver.current = true;
      playing.current = false;
      setInteractive(true);
      session.current = handleInput(
        session.current,
        client,
        data,
        clock.current,
      );
      if (flags.current.reduced && session.current.screen === "task")
        session.current.taskStart = clock.current - 9;
      setStatus(
        `${p.name}: ${session.current.screen}. ${session.current.transcript}`,
      );
      term.options.screenReaderMode = session.current.screen !== "task";
      paint();
    });
    let frame = 0,
      lastPaint = -Infinity;
    function tick(timestamp: number) {
      const f = flags.current,
        active = f.visible && !f.paused && !f.localPaused && !document.hidden;
      if (active && !f.reduced) {
        if (last.current !== null)
          clock.current += Math.min(0.1, (timestamp - last.current) / 1000);
        last.current = timestamp;
      } else last.current = null;
      if (active && timestamp - lastPaint > 100) {
        lastPaint = timestamp;
        const t = Math.max(0, clock.current - offset);
        if (playing.current && !takingOver.current && !f.reduced) {
          if (t < 2.4)
            session.current = { ...session.current, screen: "home", input: "" };
          else if (t < 4.5)
            session.current = { ...session.current, screen: "mcp", input: "" };
          else if (t < 7.7) {
            const len = Math.min(
              DEMO_PROMPT.length,
              Math.floor((t - 5.2) * 18),
            );
            session.current = {
              ...session.current,
              screen: "home",
              input: DEMO_PROMPT.slice(0, Math.max(0, len)),
              cursor: Math.max(0, len),
            };
          } else if (session.current.screen !== "task")
            session.current = execute(
              { ...session.current, input: DEMO_PROMPT },
              client,
              clock.current,
            );
          if (t > 19) playing.current = false;
        }
        if (
          f.reduced &&
          session.current.screen === "home" &&
          !takingOver.current
        )
          session.current = { ...session.current, transcript: "" };
        const output = renderScreen(
          session.current,
          client,
          term.cols,
          term.rows,
          clock.current,
          playing.current && !f.reduced && t < 2.4,
          toolNames.current,
        );
        if (output !== paintKey.current) {
          term.write(output);
          paintKey.current = output;
        }
      }
      frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      input.dispose();
      term.dispose();
      terminal.current = null;
      last.current = null;
    };
  }, [client, replay, reduced]);
  useEffect(() => {
    if (!expanded) return;
    terminal.current?.focus();
    const key = (event: KeyboardEvent) => {
      if (
        event.key === "Escape" &&
        session.current.screen === "home" &&
        !session.current.input
      ) {
        setExpanded(false);
        event.stopPropagation();
      }
      if (event.key === "Tab" && session.current.screen !== "commands") {
        const controls =
          card.current?.querySelectorAll<HTMLElement>("button,textarea");
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
    document.addEventListener("keydown", key, true);
    const prior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", key, true);
      document.body.style.overflow = prior;
      openButton.current?.focus();
    };
  }, [expanded]);
  function restart() {
    session.current = initialSession(client);
    clock.current = 0;
    last.current = null;
    paintKey.current = "";
    playing.current = true;
    takingOver.current = false;
    setInteractive(false);
    setLocalPaused(false);
    setReplay((n) => n + 1);
  }
  function example() {
    takingOver.current = true;
    playing.current = false;
    setInteractive(true);
    session.current = execute(
      { ...session.current, input: DEMO_PROMPT },
      client,
      clock.current,
    );
    if (reduced) session.current.taskStart = clock.current - 9;
    terminal.current?.focus();
  }
  return (
    <div
      ref={card}
      className={`agent-card ${expanded ? "agent-expanded" : ""}`}
      role={expanded ? "dialog" : undefined}
      aria-modal={expanded || undefined}
      aria-label={`${p.name} interactive demo`}
    >
      <Terminal
        sequence={false}
        header={
          <div className="agent-toolbar">
            <div className="agent-name">
              <span style={{ color: p.accent }}>
                {client === "hermes"
                  ? "☤"
                  : client === "codex"
                    ? ">_"
                    : client === "claude"
                      ? "✳"
                      : "◧"}
              </span>
              {p.name}
              <small>{p.version}</small>
            </div>
            <div className="agent-actions">
              <button
                title={localPaused ? "Resume" : "Pause"}
                aria-label={`${localPaused ? "Resume" : "Pause"} ${p.name}`}
                onClick={() => setLocalPaused(!localPaused)}
              >
                {localPaused ? "▷" : "Ⅱ"}
              </button>
              <button
                title="Replay"
                aria-label={`Replay ${p.name}`}
                onClick={restart}
              >
                ↺
              </button>
              <button
                ref={openButton}
                title={expanded ? "Close" : "Enlarge"}
                aria-label={`${expanded ? "Close" : "Enlarge"} ${p.name}`}
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? "×" : "⛶"}
              </button>
            </div>
          </div>
        }
        body={
          <div
            className="terminal-screen"
            ref={host}
            onClick={() => {
              if (playing.current && !takingOver.current)
                session.current = { ...session.current, input: "", cursor: 0 };
              playing.current = false;
              takingOver.current = true;
              setInteractive(true);
              terminal.current?.focus();
            }}
          />
        }
      />
      <p className="sr-only" aria-live="polite">
        {status}
      </p>
      <div className="agent-hint">
        <span>
          {interactive
            ? "Keyboard active · Esc returns to prompt"
            : `Try ${p.statusCommand} · / for commands`}
        </span>
        <button onClick={example}>Try a Hercules task ↗</button>
      </div>
    </div>
  );
}
