import test from "node:test";
import assert from "node:assert/strict";
import { frameAt,PlaybackClock,sessionEnd } from "../src/pixel-timeline.js";

test("pixel playback uses original presentation timestamps without capped frame steps",()=>{
  const frames=[{at:0},{at:.0167},{at:.123},{at:2.019}];
  assert.equal(frameAt(frames,.01669),0);assert.equal(frameAt(frames,.0167),1);
  assert.equal(frameAt(frames,.1229),1);assert.equal(frameAt(frames,.123),2);
  assert.equal(frameAt(frames,10),3);
  const clock=new PlaybackClock(2);clock.tick(100,false,60);
  assert.equal(clock.tick(1800,false,60),3.7,"slow rendering preserves elapsed 1× time");
  clock.tick(1900,true,60);clock.tick(9000,true,60);clock.tick(9500,false,60);
  assert.equal(clock.tick(9800,false,60),4,"explicit pauses do not accrue time");
  clock.suspend();assert.equal(clock.tick(20000,false,60),4,"hidden intervals do not become resume jumps");
});

test("cycling retains the completed native report instead of showing process teardown",()=>{
  const frames=[{at:0,kind:"startup"},{at:100,kind:"report"},{at:106.03,kind:"exit-clear"}];
  const end=sessionEnd(106.5,100),clock=new PlaybackClock(105.9);
  clock.tick(0,false,end);clock.tick(300,false,end);
  assert.equal(clock.time,106);assert.equal(frames[frameAt(frames,clock.time)].kind,"report");
  assert.equal(frames.at(-1).kind,"exit-clear","untouched source still contains teardown");
  assert.equal(sessionEnd(80,undefined),80);assert.equal(sessionEnd(105,100),105);
});

test("2.5× playback scales source time, preserves pauses and loops before teardown",()=>{
  const end=sessionEnd(106.5,100),clock=new PlaybackClock(2,2.5);
  clock.tick(100,false,end);assert.equal(clock.tick(2100,false,end),7);
  clock.tick(2200,true,end);clock.tick(20000,true,end);clock.tick(21000,false,end);
  assert.equal(clock.tick(21400,false,end),8,"pause intervals stay excluded at accelerated speed");
  clock.suspend();assert.equal(clock.tick(40000,false,end),8);
  assert.equal(clock.tick(100000,false,end),106,"loop ends on the native report, before exit clear");
  assert.throws(()=>new PlaybackClock(0,0),RangeError);assert.throws(()=>new PlaybackClock(0,Infinity),RangeError);
});

test("duplicate capture timestamps present the last native frame at that timestamp",()=>{
  const frames=[{at:0,id:"opening"},{at:.117,id:"partial"},{at:.117,id:"complete"},{at:.134,id:"next"}];
  assert.equal(frames[frameAt(frames,.116999)].id,"opening");
  assert.equal(frames[frameAt(frames,.117)].id,"complete");
  assert.equal(frames[frameAt(frames,.133999)].id,"complete");
  assert.equal(frames[frameAt(frames,.134)].id,"next");
});
