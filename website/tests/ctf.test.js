import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
test("forensic captures follow packet and manifest clues before checking the flag",async()=>{
  const root=new URL("../assets/recordings/",import.meta.url),m=JSON.parse(await readFile(new URL("manifest.json",root),"utf8"));
  for(const r of m.recordings.filter(r=>r.scenario==="forensics")){
    const report=await readFile(new URL(r.report,root),"utf8");assert.match(report,/route_fragment/);assert.match(report,/PBKDF2/);assert.match(report,/reject/);assert.match(report,/checksum|Checksum/);assert.ok(r.tools.includes("ctf_binwalk"));
    const pcap=r.artifacts.find(a=>a.path==="challenge/route.pcap"),bytes=await readFile(new URL(pcap.file,root));assert.equal(bytes.readUInt32LE(0),0xa1b2c3d4);
    let offset=24;const fragments=[];while(offset<bytes.length){const length=bytes.readUInt32LE(offset+8);offset+=16;const packet=bytes.subarray(offset,offset+length);offset+=length;fragments.push(JSON.parse(packet.subarray(42).toString()).route_fragment);}
    assert.deepEqual(fragments,["north","gate","17"]);assert.ok(!r.artifacts.some(a=>a.path.endsWith("ctf_lab.py")),"no prewritten challenge solver");
  }
});
