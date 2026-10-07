// Locate the first visible native frame, including ANSI split across PTY chunks.
import { readFile } from "node:fs/promises";
import xterm from "@xterm/xterm";
import { parseRecording } from "../src/recording.js";

const frames = await Promise.all(
  process.argv.slice(2).map(async (file) => {
    const recording = parseRecording(await readFile(file, "utf8"));
    const terminal = new xterm.Terminal({
      cols: recording.header.width,
      rows: recording.header.height,
      scrollback: 0,
      convertEol: false,
    });
    try {
      for (const [time, , output] of recording.events) {
        await new Promise((resolve) => terminal.write(output, resolve));
        const buffer = terminal.buffer.active;
        // Claude's first-run theme/trust wizard is configuration, not the
        // demonstration. Begin at the native app so its mascot entrance plays.
        if (recording.header.title.startsWith("claude /") && buffer.type !== "alternate")
          continue;
        if (
          Array.from({ length: terminal.rows }, (_, y) =>
            buffer
              .getLine(buffer.viewportY + y)
              ?.translateToString(true)
              .trim(),
          ).some(Boolean)
        )
          return [file, time];
      }
      throw new Error(`${file}: no visible terminal frame`);
    } finally {
      terminal.dispose();
    }
  }),
);
process.stdout.write(JSON.stringify(Object.fromEntries(frames)));
