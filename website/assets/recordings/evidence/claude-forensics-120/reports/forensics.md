# Binary and layered forensics

Hercules tool results from a disposable local lab.

## Verified observations

### 3. shell_exec
I will identify the supplied binary and inspect its header and strings before inferring what it does. It has no executable program to decompile.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: ELF Header:
  Magic:   7f 45 4c 46 02 01 01 00 00 00 00 00 00 00 00 00 
  Class:                             ELF64
  Data:                              2's complement, little endian
  Version:                           1 (current)
  OS/ABI:                            UNIX - System V
  ABI Version:                       0
  Type:                              REL (Relocatable file)
  Machine:                           Advanced Micro Devices X86-64
  Version:                           0x1
  Entry point address:               0x0
  Start of program headers:          0 (bytes into file)
  Start of section headers:          0 (bytes into file)
  Flags:                             0x0
  Size of this header:               64 (bytes)
  Size of program headers:           56 (bytes)
  Number of program headers:         0
  Size of section headers:           64 (bytes)
  Number of section headers:         0
  Section header string table index: 0
ATLAS-LAB-MODULE-1.0

stderr: /opt/workspace/tmp/shell_8eb6d9bd03b2407993d845b3994ec3a6.sh: line 1: file: command 
```

### 4. shell_exec
I will establish file types and hashes before modifying or extracting any challenge input.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: 594deb6fd0ef2a3091a754e44747a2bebdd91e0bb47266b3b114614ac7677110  /opt/workspace/challenge/advisory.json
4576b5ace22e907ef160986dcf4169f6668254bd066581f01fc568826dc1f620  /opt/workspace/challenge/carrier.png
ac73762deb7cf852fa8492d5e4d31a574569c591cca430435cee984d50b83e7c  /opt/workspace/challenge/module.o
f75d3f5a470d08914e988d5d204eb9888570fc5027336c6c2965bbd60fd68fd7  /opt/workspace/challenge/route.pcap

stderr: /opt/workspace/tmp/shell_c867f6a540314863b50a9dd438fcdd9b.sh: line 1: file: command not found

duration_seconds: 0.29
command: bash /opt/workspace/tmp/shell_c867f6a540314863b50a9dd438fcdd9b.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 410
stderr_chars: 94
stdout_bytes: 410
stderr_bytes: 94
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 410
inline_stderr_chars: 94
estimated_inline_tokens: 126
requested_timeout_seconds: 45
effective_timeout_seconds: 45
```

### 5. shell_exec
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
duration_seconds: 0.5
command: bash /opt/workspace/tmp/shell_783d31d2c04745b9af58a1389d55f95f.sh
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
requested_timeout_seconds: 45
effective_timeout_seconds: 45
```

### 6. ctf_binwalk
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
duration_seconds: 2.95
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

### 7. shell_exec
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
Z]mk
manifest.json%
NB-Y
\H!u
F!F);
Apk"
payload.enc
Salted__
8\'FA
?DoPK
decoy.txt
Z]mk
manifest.jsonPK
payload.encPK
decoy.txtPK

stderr: 
duration_seconds: 0.22
command: bash /opt/workspace/tmp/shell_22de0af23e1641379088766bdbeb527f.sh
output_filtered: False
output_complete: True
evidence_complete: True
stdout_truncated: False
stderr_truncated: False
stdout_chars: 240
stderr_chars: 0
stdout_bytes: 240
stderr_bytes: 0
stdout_chars_exact: True
stderr_chars_exact: True
inline_stdout_chars: 240
inline_stderr_chars: 0
estimated_inline_tokens: 60
requested_timeout_seconds: 45
effective_timeout_seconds: 45
```

### 8. shell_exec
The appended ZIP is confirmed. I will extract the locally authored entries into a separate evidence directory and inspect the manifest.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: ['manifest.json', 'payload.enc', 'decoy.txt']

stderr: 
duration_seconds: 2.58
command: bash /opt/workspace/tmp/shell_05aab82cac9b44d59d86edcc48db8b9b.sh
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
requested_timeout_seconds: 45
effective_timeout_seconds: 45
```

### 9. workspace_read_file
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

### 10. shell_exec
I will reject the tempting unseparated-route hypothesis. A failed decryption is evidence to revise the key construction.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 1
stdout: 
stderr: bad decrypt
40C7047B66730000:error:1C800064:Provider routines:ossl_cipher_unpadblock:bad decrypt:../providers/implementations/ciphers/ciphercommon_block.c:107:

duration_seconds: 0.23
command: bash /opt/workspace/tmp/shell_f79033ec7ddf4608b23c1ebaf736660f.sh
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
requested_timeout_seconds: 45
effective_timeout_seconds: 45
```

### 11. shell_exec
The manifest's separators matter. I will derive the key from the observed packet sequence and decrypt the actual payload.

Actual response excerpt:
```text
tool: shell_exec
exit_code: 0
stdout: 
stderr: 
duration_seconds: 0.26
command: bash /opt/workspace/tmp/shell_1cbfc6e3c83048fe92b12be4fea5f3ea.sh
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
requested_timeout_seconds: 45
effective_timeout_seconds: 45
```

### 12. shell_exec
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
duration_seconds: 0.36
command: bash /opt/workspace/tmp/shell_50a22e10f5994e0baeec0307ebe83a88.sh
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
requested_timeout_seconds: 45
effective_timeout_seconds: 45
```

### 13. workspace_read_file
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
