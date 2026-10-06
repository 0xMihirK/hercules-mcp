import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import xterm from "@xterm/xterm";
import { parseRecording, RecordingCursor } from "../src/recording.js";

const root = new URL("../assets/recordings/", import.meta.url);
const expectedVersions = {
  claude: "2.1.291",
  codex: "0.147.0",
  opencode: "1.18.34",
  hermes: "3f524a2459efe4ab32061c418e309e5da1a931fd",
};
const write = (terminal, bytes) =>
  new Promise((resolve) => terminal.write(bytes, resolve));
function screen(terminal) {
  return {
    x: terminal.buffer.active.cursorX,
    y: terminal.buffer.active.cursorY,
    rows: Array.from({ length: terminal.rows }, (_, y) => {
      const line = terminal.buffer.active.getLine(
        terminal.buffer.active.viewportY + y,
      );
      return Array.from({ length: terminal.cols }, (_, x) => {
        const cell = line.getCell(x);
        return [
          cell.getChars(),
          cell.getWidth(),
          cell.getFgColorMode(),
          cell.getFgColor(),
          cell.getBgColorMode(),
          cell.getBgColor(),
        ];
      });
    }),
  };
}

test("all 24 public sessions have verified native provenance and complete Hercules calls", async () => {
  const manifest = JSON.parse(
    await readFile(new URL("manifest.json", root), "utf8"),
  );
  assert.equal(manifest.nativeUI, true);
  assert.equal(manifest.scriptedModelAndToolResults, true);
  assert.equal(manifest.accountAccess, false);
  assert.equal(manifest.externalNetwork, false);
  assert.equal(manifest.playbackSpeed, 1);
  assert.equal(manifest.recordings.length, 24);
  const names = new Set();
  for (const item of manifest.recordings) {
    const source = await readFile(new URL(item.file, root));
    const recording = parseRecording(source.toString("utf8"));
    assert.equal(
      createHash("sha256").update(source).digest("hex"),
      item.sha256,
    );
    assert.equal(item.version, expectedVersions[item.client]);
    assert.equal(recording.header.clientVersion, item.version);
    assert.deepEqual(
      [recording.header.width, recording.header.height],
      item.columns === 120 ? [120, 36] : [80, 28],
    );
    assert.ok(recording.events.length > 10);
    if (item.client === "codex")
      assert.ok(
        source.includes(Buffer.from("MCP Tools")),
        `${item.file}: native MCP inventory`,
      );
    for (const tool of [
      "system_start_container",
      "workspace_read_file",
      "workspace_write_file",
      { scan: "nmap_scan", ctf: "ctf_binwalk", web: "web_scan" }[item.scenario],
    ])
      assert.ok(item.tools.includes(tool), `${item.file}: ${tool}`);
    assert.ok(
      recording.duration > recording.header.chapters.report + 5,
      "completed report is held",
    );
    names.add(item.file);
  }
  assert.equal(names.size, 24);
});

test("startup, MCP, task and report frames survive catch-up and fresh replay exactly", async () => {
  const manifest = JSON.parse(
    await readFile(new URL("manifest.json", root), "utf8"),
  );
  await Promise.all(
    manifest.recordings.map(async (item) => {
      const recording = parseRecording(
        await readFile(new URL(item.file, root), "utf8"),
      );
      const options = {
        cols: item.columns,
        rows: item.rows,
        convertEol: false,
        scrollback: 0,
      };
      const sequential = new xterm.Terminal(options);
      const cursor = new RecordingCursor(recording);
      const checkpoints = [
        recording.header.chapters.mcp + 4,
        recording.header.chapters.query + 6,
        recording.header.chapters.report + 6,
        recording.duration,
      ];
      try {
        for (const time of checkpoints) {
          // Deliver original chunks individually, then compare with a single catch-up write.
          let output;
          while (
            cursor.index < recording.events.length &&
            recording.events[cursor.index][0] <= time
          ) {
            output = cursor.drain(recording.events[cursor.index][0]);
            await write(sequential, output);
          }
          const fresh = new xterm.Terminal(options);
          try {
            await write(fresh, new RecordingCursor(recording).drain(time));
            assert.deepEqual(
              screen(sequential),
              screen(fresh),
              `${item.file} at ${time}s`,
            );
          } finally {
            fresh.dispose();
          }
        }
      } finally {
        sequential.dispose();
      }
    }),
  );
});
