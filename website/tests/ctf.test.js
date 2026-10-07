import test from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

test("local CTF fixture recovers the layered payload and rejects a decoy", async () => {
  const { stdout } = await promisify(execFile)(
    "python",
    [
      "-c",
      `
import base64, hashlib, json, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path('capture').resolve()))
from ctf_lab import create_challenge
with tempfile.TemporaryDirectory() as directory:
    home = Path(directory)
    create_challenge(home)
    command = [sys.executable, str(home / 'ctf_lab.py')]
    image, out = home / 'challenge.png', home / 'evidence'
    subprocess.run(command + ['extract', str(image), str(out)], check=True, capture_output=True)
    subprocess.run(command + ['solve', str(image), str(out)], check=True, capture_output=True)
    result = json.loads((out / 'solution.json').read_text())
    assert result['flag'] == 'HERCULES{evidence_before_answers}'
    assert result['checksum_match'] and not result['decoy_sha256_match']
    assert result['sha256'] == hashlib.sha256(result['flag'].encode()).hexdigest()
    assert image.read_bytes()[result['archive_offset']:][:4] == b'PK\\x03\\x04'
    key = result['key'].encode()
    decoy = base64.b64encode((out / 'decoy.txt').read_bytes().strip())
    (out / 'payload.bin').write_bytes(bytes(value ^ key[i % len(key)] for i, value in enumerate(decoy)))
    (out / 'solution.json').unlink()
    rejected = subprocess.run(command + ['solve', str(image), str(out)], capture_output=True, text=True)
    assert rejected.returncode != 0 and 'failed SHA-256 verification' in rejected.stderr
    assert not (out / 'solution.json').exists()
    print(json.dumps(result))
`,
    ],
    { cwd: new URL("../", import.meta.url), timeout: 30000 },
  );
  assert.equal(JSON.parse(stdout).key, "NORTH");
});
