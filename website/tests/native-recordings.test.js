import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import xterm from "@xterm/xterm";
import { parseRecording, RecordingCursor } from "../src/recording.js";

const root = new URL("../assets/recordings/", import.meta.url);
const cases = JSON.parse(
  await readFile(new URL("../capture/cases.json", import.meta.url), "utf8"),
);
const sessionCount = Object.keys(cases).length * 4 * 2;
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

test("every case has native recordings for all clients and both grids", async () => {
  const manifest = JSON.parse(
    await readFile(new URL("manifest.json", root), "utf8"),
  );
  assert.equal(manifest.nativeUI, true);
  assert.equal(manifest.scriptedModelAndToolResults, true);
  assert.equal(manifest.accountAccess, false);
  assert.equal(manifest.externalNetwork, false);
  assert.equal(manifest.playbackSpeed, 1);
  assert.equal(
    manifest.caseCatalogSha256,
    createHash("sha256")
      .update(await readFile(new URL("../capture/cases.json", import.meta.url)))
      .digest("hex"),
  );
  assert.equal(manifest.recordings.length, sessionCount);
  const names = new Set();
  for (const item of manifest.recordings) {
    const source = await readFile(new URL(item.file, root));
    const recording = parseRecording(source.toString("utf8"));
    assert.ok(cases[item.scenario], `Unknown case: ${item.scenario}`);
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
    if (item.client === "claude") {
      assert.ok(
        recording.events.some(([, , output]) =>
          output.includes("\x1b[38;2;215;119;87m"),
        ),
        `${item.file}: Claude's native orange theme is recorded`,
      );
    }
    assert.ok(
      item.displayStart >= 0 &&
        item.displayStart < recording.header.chapters.query,
      `${item.file}: startup skip stops before the example prompt`,
    );
    assert.ok(recording.events.some(([time]) => time === item.displayStart));
    if (item.client === "codex")
      assert.ok(
        source.includes(Buffer.from("MCP Tools")),
        `${item.file}: native MCP inventory`,
      );
    for (const tool of [
      "system_start_container",
      "workspace_read_file",
      "workspace_write_file",
      ...cases[item.scenario].operations.map((operation) => operation.tool),
    ])
      assert.ok(item.tools.includes(tool), `${item.file}: ${tool}`);
    if (item.scenario === "ctf")
      assert.equal(
        item.tools.filter((tool) => tool === "shell_exec").length,
        3,
      );
    assert.ok(
      recording.duration > recording.header.chapters.report + 5,
      "completed report is held",
    );
    names.add(item.file);
  }
  assert.equal(names.size, sessionCount);
  for (const client of Object.keys(expectedVersions))
    for (const scenario of Object.keys(cases))
      for (const columns of [80, 120])
        assert.ok(names.has(`${client}-${scenario}-${columns}.cast`));
});

test("Claude's native mascot animation retains colored, distinct startup frames", async () => {
  const manifest = JSON.parse(await readFile(new URL("manifest.json", root), "utf8"));
  for (const item of manifest.recordings.filter((item) => item.client === "claude")) {
    const recording = parseRecording(await readFile(new URL(item.file, root), "utf8"));
    const terminal = new xterm.Terminal({cols: item.columns, rows: item.rows, scrollback: 0});
    const frames = new Set();
    try {
      for (const [time, , output] of recording.events) {
        if (time >= recording.header.chapters.mcp + 4) break;
        await write(terminal, output);
        if (terminal.buffer.active.type !== "alternate") continue;
        const cells = screen(terminal).rows.slice(0, 4).map((row) => row.slice(0, 10));
        if (cells.some((row) => row.some(([text, , , color]) => text.trim() && color === 0xd77757)))
          frames.add(JSON.stringify(cells));
      }
      assert.ok(frames.size >= 2, `${item.file}: animated mascot frames`);
    } finally {
      terminal.dispose();
    }
  }
});

test("startup, MCP, task and report frames survive catch-up and fresh replay exactly", async () => {
  const manifest = JSON.parse(
    await readFile(new URL("manifest.json", root), "utf8"),
  );
  const results = await Promise.allSettled(
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
        item.displayStart,
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
            if (time === recording.header.chapters.mcp + 4) {
              const buffer = fresh.buffer.active;
              const text = Array.from({ length: fresh.rows }, (_, y) =>
                buffer.getLine(buffer.viewportY + y).translateToString(true),
              ).join("\n");
              assert.ok(text.toLowerCase().includes("hercules"), `${item.file}: native MCP inspection`);
            }
            if (time === item.displayStart)
              assert.ok(
                screen(fresh).rows.some((row) =>
                  row.some(([text]) => text.trim()),
                ),
                `${item.file}: playback opens on visible native output`,
              );
            if (time === recording.duration && item.scenario === "ctf") {
              const buffer = fresh.buffer.active;
              const text = Array.from({ length: fresh.rows }, (_, y) =>
                buffer.getLine(buffer.viewportY + y).translateToString(true),
              ).join("\n");
              assert.ok(
                text.includes("HERCULES{evidence_before_answers}"),
                item.file,
              );
              assert.ok(text.includes("Checksum match: true"), item.file);
              assert.ok(text.includes("Decoy match: false"), item.file);
            }
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
  for (const result of results)
    if (result.status === "rejected") throw result.reason;
});
