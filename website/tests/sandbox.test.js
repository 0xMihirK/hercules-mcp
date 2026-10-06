import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";
const source = (
  await readFile(new URL("../src/client-sandbox.ts", import.meta.url), "utf8")
).replace(
  /import art from ["']\.\/native-art\.json["'];/,
  `const art=${await readFile(new URL("../src/native-art.json", import.meta.url), "utf8")};`,
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.ES2022,
  },
}).outputText;
const {
  initialSession,
  execute,
  handleInput,
  renderScreen,
  settingOptions,
  profiles,
} = await import(
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
);
const send = (session, client, text) =>
  execute({ ...session, input: text }, client, 5);
test("each client uses its native MCP command and rejects unimplemented commands", () => {
  for (const client of Object.keys(profiles)) {
    assert.equal(
      send(initialSession(client), client, profiles[client].statusCommand)
        .screen,
      "mcp",
    );
    assert.equal(
      send(initialSession(client), client, "/invented").screen,
      "home",
    );
  }
  assert.match(
    send(initialSession("codex"), "codex", "/help").transcript,
    /Unknown/,
  );
  assert.equal(
    handleInput(initialSession("codex"), "codex", "?", 0).screen,
    "help",
  );
});
test("Claude MCP details, tool inventory and disable/reconnect work", () => {
  let s = send(initialSession("claude"), "claude", "/mcp");
  s = handleInput(s, "claude", "\r", 0);
  assert.equal(s.screen, "mcp-detail");
  s = handleInput(s, "claude", "\r", 0);
  assert.equal(s.screen, "tools");
  s = handleInput(s, "claude", "\x1b", 0);
  s = handleInput(s, "claude", "\x1b[A", 0);
  s = handleInput(s, "claude", "\r", 0);
  assert.equal(s.connected, false);
  assert.match(send(s, "claude", "Inspect the lab").transcript, /disabled/);
  s = { ...s, selected: 1 };
  s = handleInput(s, "claude", "\r", 0);
  assert.equal(s.connected, true);
});
test("OpenCode Ctrl+P opens commands; MCP toggles stay in the dialog", () => {
  assert.equal(
    handleInput(initialSession("opencode"), "opencode", "\x10", 0).screen,
    "commands",
  );
  let s = send(initialSession("opencode"), "opencode", "/mcps");
  s = handleInput(s, "opencode", " ", 0);
  assert.equal(s.connected, false);
  assert.equal(s.screen, "mcp");
  s = handleInput(s, "opencode", "\r", 0);
  assert.equal(s.connected, true);
  assert.equal(s.screen, "mcp");
});
test("client settings have distinct choices and persist; history restores tasks", () => {
  for (const client of Object.keys(profiles)) {
    let s = send(
      initialSession(client),
      client,
      client === "opencode" ? "/models" : "/model",
    );
    const choices = settingOptions(s, client);
    s = handleInput({ ...s, selected: 1 }, client, "\r", 0);
    assert.equal(s.model, choices[1]);
    s = send(s, client, "/clear");
    assert.equal(s.model, choices[1]);
    s = send(s, client, "Inspect my lab");
    s = send(
      s,
      client,
      client === "opencode" || client === "hermes" ? "/sessions" : "/resume",
    );
    s = handleInput(s, client, "\r", 0);
    assert.equal(s.input, "Inspect my lab");
  }
  let config = send(initialSession("claude"), "claude", "/config");
  config = handleInput(config, "claude", " ", 0);
  assert.equal(config.config["Auto-compact"], false);
  assert.equal(config.screen, "settings");
});
test("input editing, cancellation and staged task rendering are deterministic", () => {
  let s = handleInput(initialSession("codex"), "codex", "abc", 0);
  s = handleInput(s, "codex", "\x1b[D", 0);
  s = handleInput(s, "codex", "X", 0);
  assert.equal(s.input, "abXc");
  s = send(s, "codex", "Inspect the lab");
  assert.doesNotMatch(renderScreen(s, "codex", 80, 30, 5), /web_scan/);
  assert.match(renderScreen(s, "codex", 80, 30, 15), /HTTP 200/);
  assert.equal(
    renderScreen(s, "codex", 80, 30, 15),
    renderScreen(s, "codex", 80, 30, 15),
  );
  s = handleInput(s, "codex", "\x03", 16);
  assert.equal(s.screen, "home");
});
