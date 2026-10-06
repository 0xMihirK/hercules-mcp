export type Client = "claude" | "codex" | "opencode" | "hermes";
export type Scenario = "scan" | "ctf" | "web";
export const scenarios: { id: Scenario; name: string }[] = [
  { id: "scan", name: "Scan and report" },
  { id: "ctf", name: "Solve a CTF" },
  { id: "web", name: "Assess a website" },
];
export const profiles = {
  claude: {
    name: "Claude Code",
    version: "2.1.291",
    accent: "#D97757",
    background: "#0a0a0a",
  },
  codex: {
    name: "Codex CLI",
    version: "0.147.0",
    accent: "#E7E7E7",
    background: "#0a0a0a",
  },
  opencode: {
    name: "OpenCode",
    version: "1.18.34",
    accent: "#FAB283",
    background: "#0a0a0a",
  },
  hermes: {
    name: "Hermes Agent",
    version: "3f524a2",
    accent: "#FFBF00",
    background: "#0a0a0a",
  },
} as const;
