import test from "node:test";
import assert from "node:assert/strict";
import {
  parseRecording,
  RecordingCursor,
  RecordingWriter,
  chooseScenario,
  ShuffleBag,
  recordingGeometry,
  mapMilestoneTime,
} from "../src/recording.js";
const cast = (...events) =>
  [
    JSON.stringify({ version: 2, width: 120, height: 36, duration: 8 }),
    ...events.map((event) => JSON.stringify(event)),
  ].join("\n");

test("random playback can select every case and never immediately repeats", () => {
  const ids = ["scan", "ctf", "web", "dns", "headers", "browser"];
  const original = [...ids];
  assert.deepEqual(
    ids.map((_, index) =>
      chooseScenario(ids, null, () => (index + 0.5) / ids.length),
    ),
    ids,
  );
  for (const previous of ids) {
    const selected = ids
      .slice(1)
      .map((_, index) =>
        chooseScenario(ids, previous, () => (index + 0.5) / (ids.length - 1)),
      );
    assert.equal(selected.includes(previous), false);
    assert.deepEqual(
      new Set(selected),
      new Set(ids.filter((id) => id !== previous)),
    );
  }
  assert.deepEqual(ids, original);
});
test("raw ANSI and CR/LF survive timed playback without normalization", () => {
  const bytes = "\x1b[2J\x1b[Hlogo\r\n\x1b[31mtool\x1b[0m";
  const recording = parseRecording(cast([0.2, "o", bytes], [3, "o", "done"]));
  const cursor = new RecordingCursor(recording);
  assert.equal(cursor.drain(0.1), "");
  assert.equal(cursor.drain(0.2), bytes);
  assert.equal(cursor.drain(2.9), "");
  assert.equal(cursor.drain(3), "done");
  assert.equal(cursor.finished, false);
  cursor.drain(8);
  assert.equal(cursor.finished, true);
});
test("reset reconstructs terminal bytes without duplicates", () => {
  const cursor = new RecordingCursor(
    parseRecording(cast([1, "o", "A"], [2, "o", "B"], [3, "o", "C"])),
  );
  assert.equal(cursor.drain(3), "ABC");
  assert.equal(cursor.drain(3), "");
  cursor.reset();
  assert.equal(cursor.drain(2), "AB");
  assert.equal(cursor.drain(3), "C");
});
test("malformed geometry and backwards events fail before playback", () => {
  assert.throws(() => parseRecording('{"version":2,"width":0,"height":28}'));
  assert.throws(() => parseRecording(cast([2, "o", "A"], [1, "o", "B"])));
  assert.throws(() => parseRecording(cast([1, "o", {}])));
});

test("slow writes stay serialized and catch up without skipping output", () => {
  const cursor = new RecordingCursor(
    parseRecording(cast([1, "o", "A"], [2, "o", "B"], [3, "o", "C"])),
  );
  const writes = [],
    callbacks = [];
  const writer = new RecordingWriter(cursor, (text, done) => {
    writes.push(text);
    callbacks.push(done);
  });
  writer.writeAt(1);
  writer.writeAt(3);
  assert.deepEqual(writes, ["A"]);
  callbacks.shift()();
  writer.writeAt(3);
  assert.deepEqual(writes, ["A", "BC"]);
  callbacks.shift()();
  writer.writeAt(8);
  assert.equal(cursor.finished, true);
  assert.equal(writer.pending, false);
});

test("discarded-session callbacks cannot restart output after replay", () => {
  const recording = parseRecording(
    cast([1, "o", "old prompt"], [2, "o", " old tail"]),
  );
  const previousOutput = [],
    nextOutput = [],
    callbacks = [];
  const previous = new RecordingWriter(
    new RecordingCursor(recording),
    (text, done) => {
      previousOutput.push(text);
      callbacks.push(done);
    },
  );
  previous.writeAt(1);
  previous.cancel();
  const next = new RecordingWriter(
    new RecordingCursor(recording),
    (text, done) => {
      nextOutput.push(text);
      done();
    },
  );
  next.writeAt(2);
  callbacks.shift()();
  previous.writeAt(2);
  assert.deepEqual(previousOutput, ["old prompt"]);
  assert.deepEqual(nextOutput, ["old prompt old tail"]);
});

test("capture input, markers and terminal responses are never typed into replay", () => {
  const recording = parseRecording(
    cast(
      [0, "i", "/mcp\r"],
      [1, "o", "native menu\r\n"],
      [2, "m", "menu"],
      [3, "i", "\x1b[1;1R"],
    ),
  );
  assert.equal(new RecordingCursor(recording).drain(8), "native menu\r\n");
});

test("shuffle cycles cover each case once and avoid a boundary repeat",()=>{
  const ids=["network","web","ctf","report"];
  const bag=new ShuffleBag(ids,()=>.25);
  let last;
  for(let cycle=0;cycle<6;cycle++){
    const next=ids.map(()=>bag.next());
    assert.deepEqual(new Set(next),new Set(ids));
    assert.notEqual(next[0],last);last=next.at(-1);
  }
  const singleton=new ShuffleBag(["network"]);
  assert.equal(singleton.next(),"network");assert.equal(singleton.next(),"network");
});

test("available player width selects fixed captured geometry",()=>{
  assert.equal(recordingGeometry(279),48);
  assert.equal(recordingGeometry(509),48);
  assert.equal(recordingGeometry(510),80);
  assert.equal(recordingGeometry(759),80);
  assert.equal(recordingGeometry(760),120);
});

test("geometry changes map investigation and completion hold without jumping",()=>{
  const from={mcp:10,query:20,investigation:50,report:100};
  const to={mcp:12,query:24,investigation:60,report:160};
  assert.equal(mapMilestoneTime(75,from,to,166,106),110);
  assert.equal(mapMilestoneTime(103,from,to,166,106),163);
  assert.equal(mapMilestoneTime(106,from,to,166,106),166);
});

test("first frame waits for write completion and cancellation settles loading",async()=>{
  const cursor=new RecordingCursor(parseRecording(cast([1,"o","native logo"])));
  let finish;
  const writer=new RecordingWriter(cursor,(_bytes,done)=>{finish=done;});
  let settled=false;
  const loading=writer.seekTo(1).then(value=>{settled=true;return value;});
  await Promise.resolve();assert.equal(settled,false);
  writer.cancel();assert.equal(await loading,false);
  finish();assert.equal(writer.alive,false);
  const fresh=new RecordingWriter(new RecordingCursor(cursor.recording),(_bytes,done)=>done());
  assert.equal(await fresh.seekTo(1),true);
});
