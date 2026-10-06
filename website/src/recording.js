/** Raw asciicast v2 parsing and playback position, independent of the renderer. */
export function parseRecording(source) {
  const lines = source
    .trim()
    .split(/\r?\n/)
    .map((line) => JSON.parse(line));
  const header = lines.shift();
  if (
    header?.version !== 2 ||
    !Number.isInteger(header.width) ||
    !Number.isInteger(header.height) ||
    header.width < 1 ||
    header.height < 1
  )
    throw new Error("Unsupported terminal recording");
  if (
    header.duration !== undefined &&
    (!Number.isFinite(header.duration) || header.duration < 0)
  )
    throw new Error("Invalid recording duration");
  let previous = 0;
  const events = lines.filter((event) => {
    if (
      !Array.isArray(event) ||
      event.length !== 3 ||
      !Number.isFinite(event[0]) ||
      event[0] < previous ||
      !["o", "i", "r", "m"].includes(event[1]) ||
      typeof event[2] !== "string"
    )
      throw new Error("Invalid recording event");
    previous = event[0];
    return event[1] === "o";
  });
  return { header, events, duration: Math.max(header.duration || 0, previous) };
}
export class RecordingCursor {
  constructor(recording) {
    this.recording = recording;
    this.index = 0;
    this.time = 0;
  }
  drain(time) {
    this.time = Math.min(this.recording.duration, Math.max(this.time, time));
    const chunks = [];
    while (
      this.index < this.recording.events.length &&
      this.recording.events[this.index][0] <= this.time
    )
      chunks.push(this.recording.events[this.index++][2]);
    return chunks.join("");
  }
  reset() {
    this.index = 0;
    this.time = 0;
  }
  get finished() {
    return this.time >= this.recording.duration;
  }
}

/** One xterm write at a time; cancelled sessions cannot enqueue more output. */
export class RecordingWriter {
  constructor(cursor, write) {
    this.cursor = cursor;
    this.write = write;
    this.pending = false;
    this.alive = true;
  }
  writeAt(time) {
    if (!this.alive || this.pending) return;
    const output = this.cursor.drain(time);
    if (!output) return;
    this.pending = true;
    this.write(output, () => {
      if (this.alive) this.pending = false;
    });
  }
  cancel() {
    this.alive = false;
  }
}
