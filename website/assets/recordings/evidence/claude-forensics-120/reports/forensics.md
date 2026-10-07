# Layered forensic CTF

Real Hercules tools in a disposable local lab. Model decisions and this report are scripted.

## Verified observations

### 3. shell_exec
I will establish file types and hashes before modifying or extracting any challenge input.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: cd6a0877ed35ad1333291d93ff887b96287c4d07b1498638e01995ff1761dfb2  /opt/workspace/challenge/carrier.png
f75d3f5a470d08914e988d5d204eb9888570fc5027336c6c2965bbd60fd68fd7  /opt/workspace/challenge/route.pcap

stderr: /opt/workspace/tmp/shell_b99919fcc9804eb587be70de53cabf8a.sh: line 1: file: command not found

duration_seconds: 0.19
command: bash /opt/workspace/tmp/shell_b99919fcc9804eb587be70de53cabf8a.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 205
stderr_chars: 94
stdout_bytes: 205
stderr_bytes: 94
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 205
inline_stderr_chars: 94
estimated_inline_tokens: 75
```

### 4. shell_exec
I will inspect the real packet payloads in sequence and retain their route fragments as clues, without assuming they are the final answer.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: {
  "packets": [
    {
      "sequence": 1,
      "route_fragment": "north",
      "carrier": "carrier.png"
    },
    {
      "sequence": 2,
      "route_fragment": "gate",
      "carrier": "carrier.png"
    },
    {
      "sequence": 3,
      "route_fragment": "17",
      "carrier": "carrier.png"
    }
  ],
  "next": "Inspect the carrier, then apply the route rule from its archive manifest."
}

stderr: 
duration_seconds: 0.17
command: bash /opt/workspace/tmp/shell_ec78875a82a040a4a6a8ced0fe2ae3f4.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 399
stderr_chars: 0
stdout_bytes: 399
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 399
inline_stderr_chars: 0
estimated_inline_tokens: 100
```

### 5. ctf_binwalk
The packets name the carrier. I will check its embedded signatures before choosing an extraction method.

Actual response excerpt:
```text
tool: ctf_binwalk
filepath: /opt/workspace/challenge/carrier.png
exit_code: 0
stdout: 
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
0             0x0             PNG image, 32 x 32, 8-bit/color RGB, non-interlaced
137           0x89            Zlib compressed data, default compression
195           0xC3            Zip archive data, at least v2.0 to extract, compressed size: 216, uncompressed size: 282, name: manifest.json
454           0x1C6           Zip archive data, at least v2.0 to extract, compressed size: 85, uncompressed size: 80, name: payload.enc
580           0x244           Zip archive data, at least v2.0 to extract, compressed size: 43, uncompressed size: 43, name: decoy.txt
833           0x341           End of Zip archive, footer length: 22


stderr: 
duration_seconds: 0.66
command: binwalk /opt/workspace/challenge/carrier.png
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 757
stderr_chars: 0
stdout_bytes: 757
s
```

### 6. shell_exec
The carrier contains a clue about multiple endings. I will inspect the archive as a separate layer, rather than treat the image's first signature as complete.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: IHDR
TtEXtComment
A valid image can have more than one ending. The route lives in the packets.zP
*IDATx
IEND
IG]mk
manifest.json%
NB-Y
\H!u
F!F);
Apk"
payload.enc
Salted__
V/p#
7(	iA
decoy.txt
IG]mk
manifest.jsonPK
payload.encPK
decoy.txtPK

stderr: 
duration_seconds: 0.16
command: bash /opt/workspace/tmp/shell_35b61c1383a844f995152e9361a0b605.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 241
stderr_chars: 0
stdout_bytes: 241
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 241
inline_stderr_chars: 0
estimated_inline_tokens: 61
```

### 7. shell_exec
The appended ZIP is confirmed. I will extract the locally authored entries into a separate evidence directory and inspect the manifest.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: ['manifest.json', 'payload.enc', 'decoy.txt']

stderr: 
duration_seconds: 0.17
command: bash /opt/workspace/tmp/shell_cc7910cc211e4f378b1b4021814a71f0.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 46
stderr_chars: 0
stdout_bytes: 46
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 46
inline_stderr_chars: 0
estimated_inline_tokens: 12
```

### 8. workspace_read_file
The manifest specifies AES-256-CBC, PBKDF2 and zlib, and says to join packet fragments with hyphens. I will test the key construction against those clues.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/forensics/manifest.json
encoding: text
bytes: 282
total_bytes: 282
offset: 0
truncated: False
next_offset: None
content: {
  "flag_sha256": "857ac4783c125b64d0201818c5b1709812c211f8892343241222e8cbeae0a909",
  "cipher": "AES-256-CBC",
  "kdf": "PBKDF2",
  "iterations": 10000,
  "compression": "zlib",
  "password_rule": "Join the three route fragments from the capture with hyphens, in packet order."
}
```

### 9. shell_exec
I will reject the tempting unseparated-route hypothesis. A failed decryption is evidence to revise the key construction.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 1
stdout: 
stderr: bad decrypt
40A7926EC1770000:error:1C800064:Provider routines:ossl_cipher_unpadblock:bad decrypt:../providers/implementations/ciphers/ciphercommon_block.c:107:

duration_seconds: 0.16
command: bash /opt/workspace/tmp/shell_89755ddb138b47698d8a6d8d692042dd.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 0
stderr_chars: 160
stdout_bytes: 0
stderr_bytes: 160
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 160
estimated_inline_tokens: 40
```

### 10. shell_exec
The manifest's separators matter. I will derive the key from the observed packet sequence and decrypt the actual payload.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.14
command: bash /opt/workspace/tmp/shell_9c68914080a84bf19de68b2c517e3ad1.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 0
stderr_chars: 0
stdout_bytes: 0
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 0
inline_stderr_chars: 0
estimated_inline_tokens: 0
```

### 11. shell_exec
I will apply the discovered compression layer, compare the recovered flag's SHA-256 with the manifest, and reject the decoy by its mismatching digest.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: {
  "flag": "HERCULES{packet_to_carrier_to_verified_evidence}",
  "sha256": "857ac4783c125b64d0201818c5b1709812c211f8892343241222e8cbeae0a909",
  "checksum_match": true,
  "decoy_match": false
}

stderr: 
duration_seconds: 0.17
command: bash /opt/workspace/tmp/shell_2a4776738cd2412986c0a41b3d133fb1.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 195
stderr_chars: 0
stdout_bytes: 195
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 195
inline_stderr_chars: 0
estimated_inline_tokens: 49
```

### 12. workspace_read_file
The checksum and decoy checks passed. I will reread the verification artifact before publishing the reproducible write-up.

Actual response excerpt:
```text
tool: workspace_read_file
path: /opt/workspace/artifacts/forensics/verification.json
encoding: text
bytes: 194
total_bytes: 194
offset: 0
truncated: False
next_offset: None
content: {
  "flag": "HERCULES{packet_to_carrier_to_verified_evidence}",
  "sha256": "857ac4783c125b64d0201818c5b1709812c211f8892343241222e8cbeae0a909",
  "checksum_match": true,
  "decoy_match": false
}
```

## Scope and limitations

Only the internal fixture was assessed. No public target was contacted. Inputs are authored lab fixtures; tool results are real.
This is an evidence-linked demonstration, not a complete security assessment. A reference match, open port or missing header alone does not establish exploitability.
Raw diagnostics and workspace artifacts are retained. Inline output completeness does not prove investigation completeness.

## Evidence
See evidence-index.json for artifact paths, byte counts and SHA-256 hashes.
