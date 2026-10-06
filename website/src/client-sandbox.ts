import art from "./native-art.json";
export type Client = "claude" | "codex" | "opencode" | "hermes";
export type Screen =
  | "home"
  | "mcp"
  | "mcp-detail"
  | "tools"
  | "commands"
  | "help"
  | "settings"
  | "history"
  | "task"
  | "exit";
export type Session = {
  screen: Screen;
  input: string;
  cursor: number;
  selected: number;
  history: string[];
  historyIndex: number;
  connected: boolean;
  taskStart: number;
  model: string;
  theme: string;
  transcript: string;
  setting: string;
  config: Record<string, boolean>;
  permission: string;
};
export const profiles = {
  claude: {
    name: "Claude Code",
    version: "2.1.291",
    accent: "#D97757",
    background: "#141414",
    prompt: ">",
    commands: ["help", "mcp", "config", "model", "resume", "clear", "exit"],
    statusCommand: "/mcp",
    model: "Opus 5.5",
    footer: "? for shortcuts · shift+tab to cycle modes",
  },
  codex: {
    name: "Codex CLI",
    version: "0.147.0",
    accent: "#E7E7E7",
    background: "#111315",
    prompt: "›",
    commands: [
      "mcp",
      "model",
      "permissions",
      "keymap",
      "theme",
      "status",
      "resume",
      "clear",
      "quit",
    ],
    statusCommand: "/mcp",
    model: "gpt-5.4",
    footer: "? for shortcuts · 100% context left",
  },
  opencode: {
    name: "OpenCode",
    version: "1.18.34",
    accent: "#FAB283",
    background: "#0A0A0A",
    prompt: "",
    commands: ["help", "mcps", "models", "themes", "sessions", "clear", "exit"],
    statusCommand: "/mcps",
    model: "Claude Sonnet",
    footer: "ctrl+x leader · tab switch agent · ctrl+p commands",
  },
  hermes: {
    name: "Hermes Agent",
    version: "3f524a2",
    accent: "#FFBF00",
    background: "#151310",
    prompt: "❯",
    commands: [
      "help",
      "reload-mcp",
      "model",
      "verbose",
      "sessions",
      "status",
      "clear",
      "exit",
    ],
    statusCommand: "/reload-mcp",
    model: "claude-sonnet-4",
    footer: "Enter send · Alt+Enter newline · /help commands",
  },
} as const;
export const DEMO_PROMPT = "Inspect the local lab with Hercules.";
export const initialSession = (client: Client): Session => ({
  screen: "home",
  input: "",
  cursor: 0,
  selected: 0,
  history: [],
  historyIndex: -1,
  connected: true,
  taskStart: 0,
  model: profiles[client].model,
  theme: "opencode",
  transcript: "",
  setting: "",
  config: {
    "Auto-compact": true,
    "Show tips": true,
    "Reduce motion": false,
    "Thinking mode": true,
    "Prompt suggestions": true,
    "Session recap": true,
  },
  permission: "Default",
});
export function settingOptions(session: Session, client: Client): string[] {
  if (session.setting === "/config") return Object.keys(session.config);
  if (session.setting === "/permissions")
    return ["Read Only", "Default", "Full Access"];
  if (session.setting === "/keymap") return ["Default", "Emacs"];
  if (session.setting === "/verbose") return ["off", "on"];
  if (session.setting === "/theme")
    return ["Default", "GitHub Dark", "Catppuccin Mocha"];
  if (session.setting === "/themes")
    return ["opencode", "catppuccin", "tokyonight"];
  if (client === "claude") return ["Opus 5.5", "Sonnet 5.5", "Haiku 4.5"];
  if (client === "codex") return ["gpt-5.4", "gpt-5.3-codex"];
  if (client === "opencode")
    return ["Claude Sonnet", "GPT-5.4", "Gemini 2.5 Pro"];
  return ["claude-sonnet-4", "gpt-5.4"];
}
const historyItems = (session: Session) =>
  session.history.filter((h) => !h.startsWith("/"));
export function execute(
  session: Session,
  client: Client,
  clock: number,
): Session {
  const input = session.input.trim(),
    command = input.split(/\s+/)[0].toLowerCase(),
    next = {
      ...session,
      input: "",
      cursor: 0,
      selected: 0,
      history: input ? [...session.history, input] : session.history,
      historyIndex: -1,
    };
  if (!input) return next;
  if (
    input.startsWith("/") &&
    !profiles[client].commands.includes(command.slice(1) as never)
  )
    return { ...next, screen: "home", transcript: `Unknown command: ${input}` };
  if (
    command === profiles[client].statusCommand ||
    (command === "/mcp" && client === "codex")
  )
    return { ...next, screen: "mcp" };
  if (command === "/help" || (input === "?" && client === "codex"))
    return { ...next, screen: "help" };
  if (
    [
      "/model",
      "/models",
      "/config",
      "/permissions",
      "/keymap",
      "/theme",
      "/themes",
      "/verbose",
    ].includes(command)
  )
    return { ...next, screen: "settings", setting: command };
  if (["/resume", "/sessions", "/history"].includes(command))
    return { ...next, screen: "history" };
  if (command === "/status") return { ...next, screen: "mcp" };
  if (command === "/clear")
    return {
      ...session,
      screen: "home",
      input: "",
      cursor: 0,
      transcript: "",
      history: next.history,
    };
  if (command === "/exit" || command === "/quit")
    return { ...next, screen: "exit" };
  if (input.startsWith("/"))
    return { ...next, screen: "home", transcript: `Unknown command: ${input}` };
  return session.connected
    ? { ...next, screen: "task", taskStart: clock, transcript: input }
    : {
        ...next,
        screen: "home",
        transcript: "Hercules MCP is disabled. Re-enable it to use its tools.",
      };
}
export function handleInput(
  session: Session,
  client: Client,
  data: string,
  clock: number,
): Session {
  let next = { ...session };
  if (data === "\x1b" || data === "\x03") {
    return {
      ...next,
      screen:
        next.screen === "tools"
          ? "mcp-detail"
          : next.screen === "mcp-detail"
            ? "mcp"
            : "home",
      input: "",
      cursor: 0,
      selected: 0,
    };
  }
  if (data === "\x0c") return { ...next, screen: "home", transcript: "" };
  if (data === "\x15")
    return {
      ...next,
      input: next.input.slice(next.cursor),
      cursor: 0,
      screen: "home",
    };
  if (data === "\x0b")
    return { ...next, input: next.input.slice(0, next.cursor) };
  if (next.screen === "exit")
    return data === "\r" ? initialSession(client) : next;
  const modal = [
    "mcp",
    "mcp-detail",
    "tools",
    "commands",
    "help",
    "settings",
    "history",
  ].includes(next.screen);
  const count =
    next.screen === "settings"
      ? settingOptions(next, client).length
      : next.screen === "history"
        ? Math.max(1, historyItems(next).length)
        : next.screen === "mcp-detail"
          ? 3
          : next.screen === "tools"
            ? 46
            : next.screen === "commands"
              ? Math.max(
                  1,
                  profiles[client].commands.filter((c) =>
                    ("/" + c).startsWith(next.input),
                  ).length,
                )
              : 1;
  if (data === "\x10" && client === "opencode" && !modal)
    return { ...next, screen: "commands", input: "", selected: 0 };
  if (data === "\x1b[A" || data === "\x10") {
    if (modal) next.selected = (next.selected + count - 1) % count;
    else {
      const index =
        next.historyIndex < 0
          ? next.history.length - 1
          : Math.max(0, next.historyIndex - 1);
      next.historyIndex = index;
      next.input = next.history[index] || "";
      next.cursor = next.input.length;
    }
    return next;
  }
  if (data === "\x1b[B" || data === "\x0e") {
    if (modal) next.selected = (next.selected + 1) % count;
    else {
      const index = next.historyIndex + 1;
      next.historyIndex = index < next.history.length ? index : -1;
      next.input = index < next.history.length ? next.history[index] : "";
      next.cursor = next.input.length;
    }
    return next;
  }
  if (data === "\x1b[D") {
    next.cursor = Math.max(0, next.cursor - 1);
    return next;
  }
  if (data === "\x1b[C") {
    next.cursor = Math.min(next.input.length, next.cursor + 1);
    return next;
  }
  if (data === "\x01") {
    next.cursor = 0;
    return next;
  }
  if (data === "\x05") {
    next.cursor = next.input.length;
    return next;
  }
  if (data === " " && next.screen === "mcp" && client === "opencode") {
    next.connected = !next.connected;
    return next;
  }
  if (
    data === "\r" ||
    (data === " " && next.screen === "settings" && next.setting === "/config")
  ) {
    if (next.screen === "mcp" && client === "claude")
      return { ...next, screen: "mcp-detail" };
    if (next.screen === "mcp" && client === "opencode")
      return { ...next, connected: !next.connected };
    if (next.screen === "mcp-detail") {
      if (next.selected === 0) return { ...next, screen: "tools" };
      return {
        ...next,
        connected: next.selected === 1,
        transcript:
          next.selected === 1 ? "Reconnected to hercules" : "Disabled hercules",
      };
    }
    if (next.screen === "commands") {
      const list = profiles[client].commands.filter((c) =>
        ("/" + c).startsWith(next.input),
      );
      if (list.length) next.input = "/" + list[next.selected % list.length];
      return execute(next, client, clock);
    }
    if (next.screen === "settings") {
      const choice = settingOptions(next, client)[next.selected];
      if (next.setting === "/config")
        return {
          ...next,
          config: { ...next.config, [choice]: !next.config[choice] },
        };
      if (next.setting === "/model" || next.setting === "/models")
        next.model = choice;
      if (next.setting === "/theme" || next.setting === "/themes")
        next.theme = choice;
      if (next.setting === "/permissions") next.permission = choice;
      return {
        ...next,
        screen: "home",
        transcript: `${next.setting}: ${choice}`,
      };
    }
    if (next.screen === "history") {
      next.input = historyItems(next)[next.selected] || DEMO_PROMPT;
      next.cursor = next.input.length;
      next.screen = "home";
      return next;
    }
    if (modal) return { ...next, screen: "home" };
    return execute(next, client, clock);
  }
  if (data === "\t") {
    const match = profiles[client].commands.filter((c) =>
      ("/" + c).startsWith(next.input),
    );
    if (match.length) {
      next.input = "/" + match[next.selected % match.length];
      next.cursor = next.input.length;
      next.screen = "commands";
    }
    return next;
  }
  if (data === "\x7f" || data === "\b") {
    if (next.cursor > 0) {
      next.input =
        next.input.slice(0, next.cursor - 1) + next.input.slice(next.cursor);
      next.cursor--;
    }
    if (!next.input.startsWith("/")) next.screen = "home";
    return next;
  }
  if (data === "?" && !next.input && client === "codex")
    return { ...next, screen: "help" };
  if (data === "\n") {
    next.input += "\n";
    next.cursor = next.input.length;
    return next;
  }
  const clean = data.replace(/[\x00-\x08\x0b-\x1f\x7f]/g, "");
  if (clean) {
    next.input =
      next.input.slice(0, next.cursor) + clean + next.input.slice(next.cursor);
    next.cursor += clean.length;
    next.selected = 0;
    next.screen = next.input.startsWith("/") ? "commands" : "home";
  }
  return next;
}
const esc = "\x1b[";
const color = (hex: string, text: string) => {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  return `${esc}38;2;${c.join(";")}m${text}${esc}0m`;
};
const dim = (text: string) => `${esc}2m${text}${esc}0m`;
const rich = (text: string) =>
  text
    .replace(/\[(?:bold )?(#[0-9A-Fa-f]{6})\]/g, (_, hex) => {
      const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
      return `${esc}38;2;${c.join(";")}m`;
    })
    .replace(/\[\/\]/g, `${esc}0m`);
function box(title: string, lines: string[], width: number, accent: string) {
  const w = Math.max(20, Math.min(width - 4, 66));
  return [
    color(
      accent,
      `╭─ ${title} ${"─".repeat(Math.max(0, w - title.length - 4))}╮`,
    ),
    ...lines.map(
      (l) =>
        `│ ${l}${" ".repeat(Math.max(0, w - l.replace(/\x1b\[[0-9;]*m/g, "").length - 2))}│`,
    ),
    color(accent, `╰${"─".repeat(w)}╯`),
  ];
}
const openLeft = [
  "                   ",
  "█▀▀█ █▀▀█ █▀▀█ █▀▀▄",
  "█__█ █__█ █^^^ █__█",
  "▀▀▀▀ █▀▀▀ ▀▀▀▀ ▀~~▀",
];
const openRight = [
  "             ▄     ",
  "█▀▀▀ █▀▀█ █▀▀█ █▀▀█",
  "█___ █__█ █__█ █^^^",
  "▀▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀",
];
const openLogo = (accent: string) =>
  openLeft.map((line, i) =>
    [...(line + "  " + openRight[i])]
      .map((char) =>
        char === "_"
          ? `${esc}48;2;44;44;44m ${esc}0m`
          : char === "^"
            ? color(accent, "▀")
            : char === "~"
              ? color("#555555", "▀")
              : color(i < 2 ? "#aaaaaa" : accent, char),
      )
      .join(""),
  );
export function renderScreen(
  session: Session,
  client: Client,
  cols: number,
  rows: number,
  time: number,
  boot = false,
  tools: string[] = [],
): string {
  const p = profiles[client],
    accent = p.accent,
    w = Math.max(20, cols - 2),
    spinner = ["·", "✢", "✳", "✶", "✻", "✽"][Math.floor(time * 8) % 6];
  const lines: string[] = [];
  if (client === "claude")
    lines.push(
      "",
      color(accent, " ▐▛███▛█") + "   Claude Code v" + p.version,
      color(accent, "▝▜██████▀") +
        "  " +
        session.model +
        " with high effort · Claude Max",
      color(accent, " ▝▝   ▝▝") + "   ~/hercules-lab",
      "",
    );
  if (client === "codex")
    lines.push(
      ...box(
        ">_ OpenAI Codex (v" + p.version + ")",
        [
          "",
          "model:     " + session.model + "   /model to change",
          "directory: ~/hercules-lab",
          "",
        ],
        cols,
        "#747b84",
      ),
      "",
    );
  if (client === "opencode") {
    lines.push("");
    const pad = " ".repeat(Math.max(0, Math.floor((w - 40) / 2))),
      themeAccent =
        session.theme === "catppuccin"
          ? "#cba6f7"
          : session.theme === "tokyonight"
            ? "#7aa2f7"
            : accent;
    openLogo(themeAccent).forEach((l) => lines.push(pad + l));
    lines.push("", "");
  }
  if (client === "hermes") {
    if (cols >= 95) lines.push(...rich(art.HERMES_AGENT_LOGO).split("\n"));
    else
      lines.push(
        color("#FFD700", " ☤  HERMES AGENT"),
        dim(" Nous Research · " + p.version),
      );
    lines.push("");
    const artLines = rich(art.HERMES_CADUCEUS).split("\n");
    if (cols >= 68 && session.screen === "home" && !session.input) {
      const info = [
        "╭─ Session ──────────────────────────╮",
        "│ Model: " + session.model,
        "│ Backend: anthropic",
        "│ Directory: ~/hercules-lab",
        "╰────────────────────────────────────╯",
        "",
        "╭─ MCP Servers ──────────────────────╮",
        "│ hercules (stdio) — 46 tool(s)",
        "╰────────────────────────────────────╯",
      ];
      artLines.forEach((l, i) => lines.push(l + "  " + (info[i] || "")));
    } else
      lines.push(
        color("#CD7F32", " ╭─ MCP Servers ────────────────────────╮"),
        " │ hercules (stdio) — 46 tool(s)         │",
        color("#CD7F32", " ╰──────────────────────────────────────╯"),
      );
    lines.push("");
  }
  if (boot) {
    lines.push(
      color(
        accent,
        client === "codex"
          ? `• Booting MCP server: hercules (${Math.floor(time)}s • esc to interrupt)`
          : `${spinner} Connecting to hercules…`,
      ),
    );
  } else if (session.screen === "mcp") {
    if (client === "codex")
      lines.push(
        "› /mcp",
        "",
        "🔌 MCP Tools",
        "",
        "  • hercules",
        "    • Status: enabled",
        "    • Auth: Unsupported",
        "    • Tools: system_start_container, web_scan,",
        "      workspace_read_file, shell_exec, nmap_scan, …",
        "    • Resources: 7",
      );
    else if (client === "hermes")
      lines.push(
        "❯ /reload-mcp",
        color("#FFBF00", " Reloading MCP servers…"),
        color("#7fd88f", " hercules (stdio) — 46 tool(s)"),
        dim(" MCP servers reloaded."),
      );
    else if (client === "claude")
      lines.push(
        "▔".repeat(w),
        "   Manage MCP servers",
        "   1 server",
        "",
        "   Built-in MCPs (always available)",
        color(
          accent,
          `   > ${session.connected ? "√" : "○"}   hercules   46 tools`,
        ),
        "",
        "   https://code.claude.com/docs/en/mcp for help",
        "",
        "   ↑/↓ to navigate · Enter to confirm · Esc to cancel",
      );
    else
      lines.push(
        ...box(
          "MCPs",
          [
            color(accent, "❯ hercules"),
            color(
              session.connected ? "#7fd88f" : "#8c8c8c",
              session.connected ? "  ● Connected" : "  ○ Disabled",
            ),
            "",
            "  Space toggle · ↑↓ select · Esc close",
          ],
          cols,
          accent,
        ),
      );
  } else if (session.screen === "mcp-detail") {
    lines.push(
      "▔".repeat(w),
      "   Hercules MCP Server",
      "",
      "   Status:           " +
        (session.connected ? "√ connected" : "○ disabled"),
      "   Config location:  Dynamically configured",
      "",
      "   Capabilities: tools · resources",
      "   Tools: 46 tools",
      "",
      ...["View tools", "Reconnect", "Disable"].map((name, i) =>
        color(
          i === session.selected ? accent : "#eeeeee",
          `   ${i === session.selected ? ">" : " "} ${i + 1}. ${name}`,
        ),
      ),
      "",
      "   ↑/↓ to navigate · Enter to select · Esc to back",
    );
  } else if (session.screen === "tools") {
    const names = tools.length
      ? tools
      : ["system_start_container", "workspace_read_file", "web_scan"];
    lines.push(
      "▔".repeat(w),
      `   Hercules tools (${tools.length || 46})`,
      "",
      ...names
        .slice(session.selected, session.selected + Math.max(4, rows - 12))
        .map((name, i) =>
          color(
            i === 0 ? accent : "#eeeeee",
            `   ${i === 0 ? ">" : " "} ${name}`,
          ),
        ),
      "",
      "   ↑/↓ to navigate · Esc to back",
    );
  } else if (session.screen === "commands") {
    const list = p.commands.filter((c) => ("/" + c).startsWith(session.input));
    lines.push(
      ...list
        .slice(0, 8)
        .map((c, i) =>
          color(
            i === session.selected % Math.max(1, list.length)
              ? accent
              : "#969da6",
            `${i === session.selected % Math.max(1, list.length) ? "❯" : " "} /${c}`,
          ),
        ),
      dim("  ↑↓ navigate · Tab complete · Enter select"),
    );
  } else if (session.screen === "help") {
    if (client === "codex")
      lines.push(
        "  Keyboard shortcuts",
        "",
        "  /          commands",
        "  ↑ / ↓      input history",
        "  Ctrl+C     interrupt",
        "  Ctrl+L     clear screen",
        "  Enter      submit message",
        "  ?          toggle shortcuts",
        "",
        "  Esc to close",
      );
    else
      lines.push(
        ...box(
          "Help",
          p.commands
            .map((c) => "/" + c)
            .concat([
              "",
              "↑↓ history · Enter send",
              "Esc close · Ctrl+C interrupt",
            ]),
          cols,
          accent,
        ),
      );
  } else if (session.screen === "settings") {
    const options = settingOptions(session, client),
      items = options.map((name, i) =>
        color(
          session.selected === i ? accent : "#a1a1a1",
          `${session.selected === i ? ">" : " "} ${name}${session.setting === "/config" ? " ".repeat(Math.max(1, 30 - name.length)) + session.config[name] : ""}`,
        ),
      );
    if (client === "claude" && session.setting === "/config")
      lines.push(
        "▔".repeat(w),
        "  Settings  Status  " + `${esc}7m Config ${esc}27m` + " Usage  Stats",
        "",
        "  ⌕ Search settings…",
        "",
        ...items,
        "",
        "  Enter/Space to change · Esc to close",
      );
    else
      lines.push(
        ...box(
          session.setting.includes("model")
            ? "Select model"
            : session.setting.includes("theme")
              ? "Select theme"
              : session.setting === "/permissions"
                ? "Select approval mode"
                : session.setting.slice(1),
          items.concat(["", "Enter select · Esc cancel"]),
          cols,
          accent,
        ),
      );
  } else if (session.screen === "history") {
    const history = historyItems(session);
    lines.push(
      ...box(
        client === "opencode"
          ? "Sessions"
          : client === "hermes"
            ? "Recent sessions"
            : "Resume a session",
        (history.length ? history : [DEMO_PROMPT])
          .slice(-6)
          .map(
            (h, i) =>
              `${i === session.selected % Math.max(1, history.length) ? "❯" : " "} ${h.slice(0, 48)}`,
          )
          .concat(["", "Enter resume · Esc cancel"]),
        cols,
        accent,
      ),
    );
  } else if (session.screen === "task") {
    const t = Math.max(0, time - session.taskStart),
      prefix =
        client === "codex"
          ? "• Called"
          : client === "hermes"
            ? "┊"
            : client === "claude"
              ? "●"
              : "⚙";
    lines.push(`${p.prompt || "❯"} ${session.transcript || DEMO_PROMPT}`, "");
    if (t < 2)
      lines.push(
        color(
          accent,
          `${spinner} ${client === "hermes" ? "(｡•́︿•̀｡) pondering..." : "Working…"} (${t.toFixed(1)}s)`,
        ),
      );
    if (t >= 2)
      lines.push(
        color(accent, `${prefix} hercules.system_start_container({})`),
        dim("  └ status: success · start_mode: created"),
      );
    if (t >= 4.1)
      lines.push(
        "",
        color(accent, `${prefix} hercules.web_scan({`),
        '    tool: "httpx", urls: "http://lab.local:8080"',
        "  })",
      );
    if (t >= 6.4) lines.push(dim("  └ 200 · Local lab · nginx"));
    if (t >= 8.3) lines.push("", "The local service responds with HTTP 200.");
    else if (t >= 2)
      lines.push(
        "",
        color(accent, `${spinner} Running tool… (${t.toFixed(1)}s)`),
      );
  } else if (session.screen === "exit")
    lines.push(
      dim("Session ended."),
      dim("Press Enter to start a new session."),
    );
  else if (session.transcript) lines.push(session.transcript);
  if (
    !boot &&
    session.screen === "home" &&
    !session.transcript &&
    !session.input &&
    client !== "hermes"
  )
    lines.push(dim("  Hercules MCP connected · 46 tools available"), "");
  const available = Math.max(4, rows - 5),
    body = lines.length > available ? lines.slice(-available) : lines;
  let output = "\x1b[?25l\x1b[H\x1b[2J" + body.join("\r\n");
  const footerRow = Math.max(body.length + 2, rows - 3),
    promptRow = Math.min(rows - 1, footerRow + 1);
  if (client === "claude" || client === "opencode")
    output += `${esc}${footerRow};1H` + dim("─".repeat(w));
  if (client === "hermes")
    output +=
      `${esc}${footerRow};1H` +
      color("#B8860B", `☤ ${session.model} │ 0/200K │ 0% │ n/a`);
  const typed = session.input.replace(/\n/g, " ↵ ");
  output +=
    `${esc}${promptRow};1H` +
    color(accent, (p.prompt || "❯") + " ") +
    (typed || dim(client === "opencode" ? "Ask anything…" : " "));
  output += `${esc}${rows};1H` + dim(p.footer.slice(0, w));
  output += `${esc}${promptRow};${Math.min(cols, (p.prompt || "❯").length + 2 + session.cursor)}H\x1b[?25h`;
  return output;
}
