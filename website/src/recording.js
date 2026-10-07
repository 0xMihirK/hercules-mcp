/** Raw asciicast v2 parsing and playback position, independent of the renderer. */
/**
 * @template {string} T
 * @param {T[]} ids
 * @param {T | null} [previous]
 * @param {() => number} [random]
 * @returns {T}
 */
export function chooseScenario(ids, previous = null, random = Math.random) {
  const available = ids.filter((id) => id !== previous);
  return available[Math.floor(random() * available.length)];
}

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
    this.settle = null;
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
    this.settle?.(false);
    this.settle = null;
  }
  /** Reconstruct a fresh renderer, resolving only after its write completes. */
  seekTo(time) {
    if (!this.alive || this.pending) return Promise.resolve(false);
    const output = this.cursor.drain(time);
    if (!output) return Promise.resolve(true);
    this.pending = true;
    return new Promise((resolve) => {
      this.settle = resolve;
      this.write(output, () => {
        if (!this.alive) return;
        this.pending = false;
        this.settle = null;
        resolve(true);
      });
    });
  }
}

/** @template {string} T */
export class ShuffleBag {
  /** @param {T[]} ids @param {() => number} [random] */
  constructor(ids, random = Math.random) {
    if (!ids.length) throw new Error("A case bag needs at least one recording");
    this.ids = [...new Set(ids)]; this.random = random; this.bag = []; this.last = null;
  }
  /** @returns {T} */
  next() {
    if (!this.bag.length) {
      this.bag = [...this.ids];
      for (let i = this.bag.length - 1; i > 0; i--) {
        const j = Math.floor(this.random() * (i + 1));
        [this.bag[i], this.bag[j]] = [this.bag[j], this.bag[i]];
      }
      if (this.bag.length > 1 && this.bag[this.bag.length - 1] === this.last)
        [this.bag[0], this.bag[this.bag.length - 1]] = [this.bag[this.bag.length - 1], this.bag[0]];
    }
    this.last = this.bag.pop(); return this.last;
  }
}

/** Fixed recording geometry, based on the actual presentation width. */
export function recordingGeometry(width) { return width >= 760 ? 120 : width >= 510 ? 80 : 48; }

/** Preserve the relative position within corresponding native milestones. */
export function mapMilestoneTime(time, from, to, duration, fromDuration = duration) {
  const names = Object.keys(from).filter(key => Number.isFinite(to[key])).sort((a,b) => from[a]-from[b]);
  const current = names.filter(key => from[key] <= time).pop();
  if (!current) return Math.min(duration, to[names[0]] || 0);
  const next = names[names.indexOf(current)+1];
  const span = next ? from[next]-from[current] : fromDuration-from[current];
  const nextTime = next ? to[next] : duration;
  const progress = span > 0 ? Math.max(0,Math.min(1,(time-from[current])/span)) : 0;
  return Math.min(duration,to[current]+progress*(nextTime-to[current]));
}
