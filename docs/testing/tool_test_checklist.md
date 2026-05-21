# Hercules MCP Server — Comprehensive Tool Testing Checklist

This checklist verifies functionality, output cleaning, structured responses, concurrency, and token optimization across all **49 MCP tools** and the new `hercules/output/` pipeline.

## Target Environments
1.  **Internet Target**: `scanme.nmap.org` (Authorized by Nmap for light scanning).
2.  **Local Vulnerable Target**: `tleemcjr/metasploitable2`
    - `docker run -it -p 21:21 -p 22:22 -p 80:80 -p 445:445 tleemcjr/metasploitable2:latest sh -c "/bin/services.sh && bash"`
    - Find the container's IP on the Docker bridge network to use as the `<MSF_IP>`.

---

## 1. Output Pipeline (`hercules/output/`)

### Sanitizer (`sanitizer.py`)
- [x] **ANSI stripping**: Feed `\x1b[31mRED\x1b[0m text` → verify output is `RED text`.
- [x] **Broad ANSI coverage**: Feed cursor movement `\x1b[2J`, bold `\x1b[1m`, underline `\x1b[4m` → verify all are stripped.
- [x] **Whitespace compression**: Feed `line1\n\n\n\n\nline2` → verify output is `line1\n\nline2`.
- [x] **Preserves meaningful content**: Feed a real Nmap XML output → verify zero data loss.

### Truncator (`truncator.py`)
- [x] **Under-limit passthrough**: Feed 500-char string with `max_chars=8000` → verify returned unchanged, `was_truncated=False`.
- [x] **Head+tail split**: Feed 20,000-char string → verify first 40% and last 60% are preserved.
- [x] **Truncation notice**: Verify notice contains exact omitted char count and artifact file path.
- [x] **Artifact logging**: Verify full raw output is saved to `/opt/workspace/logs/{tool}_{timestamp}.txt`.
- [x] **Edge case: exactly at limit**: Feed string of exactly `max_chars` length → verify no truncation.

### Banner Blocklist (`banners.py`)
- [x] **SQLMap banner stripped**: Feed real SQLMap output → verify `___` art and `[!] legal disclaimer` are removed.
- [x] **Commix banner stripped**: Feed real Commix output → verify dragon ASCII art is removed.
- [x] **Wafw00f banner stripped**: Feed real Wafw00f output → verify ASCII dog is removed.
- [x] **Hydra banner stripped**: Feed real Hydra output → verify version header is removed.
- [x] **Metasploit banner stripped**: Feed MSF console output → verify `=[  metasploit  ]=` lines removed.
- [x] **False positive safety**: Feed hex dump data (e.g., `xxd` output) → verify it survives banner stripping intact.
- [x] **False positive safety**: Feed base64-encoded certificate block → verify it survives intact.
- [x] **False positive safety**: Feed GPG key block → verify it survives intact.
- [x] **Unknown tool passthrough**: Call `strip_known_banners(text, "unknown_tool")` → verify text is returned unmodified.

### Per-Tool Filters (`filters.py`)
- [x] **Hydra filter**: Feed 10,000-line brute force output → verify only `[port][service] host:... login:... password:...` lines survive.
- [x] **John filter**: Feed full John output → verify only cracked `hash:password` lines and summary survive.
- [x] **Amass filter**: Feed full Amass output → verify only discovered domain lines survive, status messages removed.
- [x] **Empty input**: Verify all filters return empty string on empty input without errors.

### MSF Parser (`msf_parser.py`)
- [x] **Console output**: Feed MSF console session → verify prompt lines (`msf6 >`) and banner metadata stripped.
- [x] **Session output**: Feed Meterpreter command output → verify clean extraction with line count.

### Token Budget Regression
- [x] **All fixtures under budget**: Process every test fixture through the full pipeline → assert all outputs ≤ 8,000 chars.

---

## 2. Response Envelope (`ExecResult`)
- [x] **Standard fields**: Verify all tool responses contain `exit_code`, `stdout`, `stderr`, `duration_seconds`, `command`.
- [x] **Truncated flag**: Verify `truncated: true` appears in response when output exceeds limit.
- [x] **Artifact path**: Verify `artifact` field contains valid path to log file when truncated.
- [x] **Summary field**: Verify `summary` field is populated for structured-output tools (nmap, nuclei, httpx).
- [x] **Backwards compatibility**: Verify `truncated` and `artifact` fields are absent when output is not truncated.

---

## 3. Reconnaissance (`recon_tool.py`)
**Target:** `scanme.nmap.org`

- [x] **recon_whois**: Run against `scanme.nmap.org`. Verify registrar data returned. Verify ANSI codes stripped.
- [x] **recon_whois (extra_args)**: Run with `extra_args="-H"` → verify the flag is honored.
- [x] **recon_dig**: Run with `record_type="ANY"`. Verify DNS records fetched.
- [x] **recon_dig (extra_args)**: Run with `extra_args="+trace"` → verify trace output returned.
- [x] **recon_dig (zone transfer)**: Run with `axfr=True` against a known AXFR-enabled domain.
- [x] **recon_amass**: Run against `nmap.org`. Verify subdomain list returned. Verify amass status lines filtered out.
- [x] **recon_amass (background)**: Run amass via `shell_exec_background` for long scans. Verify `shell_check_job` returns tail output.
- [x] **recon_dnsx**: Pass `scanme.nmap.org,nmap.org`. Verify both resolve to IPs.

---

## 4. Web Scanning (`web_scanner_tool.py`)
**Target:** `<MSF_IP>` (Metasploitable2 port 80) & `scanme.nmap.org`

- [x] **web_httpx**: Run against `http://scanme.nmap.org`. Verify title and tech detection. Verify structured JSON response.
- [x] **web_httpx (extra_args)**: Run with `extra_args="-follow-redirects"` → verify honored.
- [x] **web_whatweb**: Run against `http://<MSF_IP>`. Verify PHP/Apache detected. Verify `-q` flag produces clean output.
- [x] **web_whatweb (JSON mode)**: Verify `--log-json` returns structured fingerprint data.
- [x] **web_wafw00f**: Run against `http://scanme.nmap.org`. Verify WAF detection. Verify ASCII dog banner is stripped.
- [x] **web_nikto**: Run against `http://<MSF_IP>`. Verify outdated Apache found. Verify output truncated if over 8K chars.
- [x] **web_nikto (extra_args)**: Run with `extra_args="-ssl"` → verify flag honored.
- [x] **web_wpscan**: Test against known WP target or skip. Verify `--no-banner` flag active.
- [x] **web_wpscan (extra_args)**: Run with `extra_args="--stealthy"` → verify flag honored.
- [x] **web_arjun**: Run against Mutillidae page on `<MSF_IP>`. Verify param fuzzing output.
- [x] **web_arjun (extra_args)**: Run with `extra_args="-t 5"` → verify thread count honored.
- [x] **fuzz_dirs (gobuster)**: Fuzz `http://<MSF_IP>/`. Verify `/dvwa`, `/mutillidae` discovered.
- [x] **fuzz_dirs (ffuf)**: Fuzz same target with `tool="ffuf"`. Verify same directories found.
- [x] **web_xss_scan**: Run Dalfox against `http://<MSF_IP>/mutillidae/...?page=...`. Verify XSS findings returned. Verify `--silence` active.
- [x] **web_cmdi_scan**: Run Commix against a vulnerable Mutillidae page. Verify command injection detected. Verify `--quiet` active.

---

## 5. Network & Port Scanning (`nmap_tool.py` & `network_tool.py`)
**Target:** `scanme.nmap.org` & `<MSF_IP>`

- [x] **nmap_quick_scan**: Run against `scanme.nmap.org`. Verify XML parsed to JSON with `parsed` field.
- [x] **nmap_aggressive_scan**: Run against `<MSF_IP>`. Verify OS detection (Linux) and version detection (vsftpd).
- [x] **nmap_aggressive_scan (truncation)**: Verify output is truncated if over 8K chars, with artifact path.
- [x] **nmap_port_scan**: Scan `<MSF_IP>` ports `21,22,80,445`. Verify specific port states in parsed JSON.
- [x] **nmap_script_scan**: Run `scripts="vuln"` against `<MSF_IP>`. Verify NSE output returned.
- [x] **nmap_custom_scan**: Run `raw_args="-sU -p 161 <MSF_IP>"`. Verify UDP scan works.
- [x] **nmap_write_nse_script**: Write dummy NSE script. Verify script DB updates.
- [x] **nmap_run_nse_script**: Run custom script. Verify output appears.
- [x] **network_curl**: Fetch `http://scanme.nmap.org` with `include_headers=True`. Verify HTML and headers.
- [x] **network_curl (extra_args)**: Run with `extra_args="--max-time 5"` → verify timeout honored.
- [x] **network_hping3**: Send 5 SYN packets to `scanme.nmap.org:80`. Verify packet stats.
- [x] **network_ncat**: Start listener `listen=True, listen_port=4444`. Verify connection established.
- [x] **network_ncat (extra_args)**: Run with `extra_args="--ssl"` → verify SSL mode activates.

---

## 6. Exploitation (`metasploit_tool.py`, `sqlmap_tool.py`, `searchsploit_tool.py`)
**Target:** `<MSF_IP>`

### Metasploit Framework
- [x] **metasploit_search**: Search `vsftpd_234_backdoor`. Verify module path returned. Verify MSF banner stripped.
- [x] **metasploit_run_module**: Run distcc exploit against `<MSF_IP>:3632`. Verify shell session created. Verify RPC boilerplate stripped.
- [x] **metasploit_list_sessions**: Verify at least one active session.
- [x] **metasploit_interact_session**: Run `whoami` in session. Verify output is `daemon`. Verify clean extraction.
- [x] **metasploit_generate_payload**: Generate `linux/x64/meterpreter_reverse_tcp` ELF (1.1MB). Verify success.
- [x] **metasploit_close_session**: Kill session. Verify session count drops.

### SQLMap
- [x] **sqlmap_run (scan_basic)**: Run against Mutillidae URL. Verify tool executes (exit 0). Banner stripped by pipeline.
- [x] **sqlmap_run (scan_custom)**: Run with `level=3, risk=2`. Verify deeper scan executes.
- [x] **sqlmap_run (scan_custom, forms=True)**: Run with `forms=True`. Verify form scanning activates.
- [x] **sqlmap_run (enumerate, dbs)**: Verify backend databases listed (e.g., `mutillidae`, `dvwa`).
- [x] **sqlmap_run (dump)**: Dump `dvwa.users`. Verify user table data returned.
- [x] **sqlmap_run (os_cmd)**: Run `command="id"`. Verify OS command execution output.
- [x] **sqlmap_run (extra_args)**: Run with `extra_args="--random-agent"` → verify flag honored.

### Searchsploit
- [x] **searchsploit (search)**: Search `UnrealIRCd 3.2.8.1`. Verify backdoor exploit found. Verify structured JSON returned.
- [x] **searchsploit (get)**: Fetch EDB-ID. Verify script content retrieved.

---

## 7. Cracking & Brute Force (`cracking_tool.py`, `wordlist_tool.py`)
**Target:** `<MSF_IP>`

- [x] **bruteforce_hydra**: Run against `ftp://<MSF_IP>` with `usernames="msfadmin"`, `passwords="msfadmin"`. Verify valid login found. Verify only credential lines in output (Hydra filter active).
- [x] **bruteforce_hydra (large wordlist)**: Run with `passwords="file:/usr/share/wordlists/rockyou.txt"`. Verify output is filtered to only credential lines, not every attempt.
- [x] **crack_john**: Pass hash. Verify john loads and processes. Verify only cracked lines in output (John filter active).
- [x] **crack_john (extra_args)**: Run with `extra_args="--rules"` → verify rules-based cracking activates.
- [x] **creds_wordlists_manage (list)**: List `/usr/share/wordlists`. Verify rockyou visible.
- [x] **creds_wordlists_manage (search)**: Search `query="rockyou"`. Verify file path found.
- [x] **creds_wordlists_manage (head)**: Read first 10 lines of rockyou.txt. Verify content returned.
- [x] **creds_wordlists_manage (count)**: Count lines in rockyou.txt. Verify numeric count returned.

---

## 8. Nuclei (`nuclei_tool.py`)
**Target:** `<MSF_IP>`

- [x] **nuclei_run**: Run against `http://<MSF_IP>`. Verify structured JSON findings returned (host, template, severity, matched_at).
- [x] **nuclei_run (severity filter)**: Run with `severity="critical,high"`. Verify only matching severities returned.
- [x] **nuclei_run (tags)**: Run with `tags="cve"`. Verify tag filtering works.
- [x] **nuclei_run (extra_args)**: Run with `extra_args="-rl 50"` → verify rate limiting honored.
- [x] **nuclei_write_template**: Write custom YAML template. Verify file written to `/opt/workspace/nuclei-templates/`.
- [x] **nuclei_write_template (path traversal)**: Pass `path="../../etc/passwd"`. Verify `ValueError` raised.

---

## 9. CTF & Forensics (`ctf_tool.py`)
**Target:** Local Docker Container Workspace

- [x] **ctf_binwalk**: Run against a known firmware image or ZIP file. Verify extraction output.
- [x] **ctf_binwalk (extra_args)**: Run with `extra_args="--signature"` → verify signature scan mode.
- [x] **ctf_strings**: Run against `/usr/bin/nmap`. Verify printable strings extracted.
- [x] **ctf_strings (grep_pattern)**: Run with `grep_pattern="nmap"`. Verify only matching lines returned.
- [x] **ctf_strings (min_length)**: Run with `min_length=10`. Verify short strings excluded.
- [x] **ctf_steghide (info)**: Run `action="info"` against a JPEG file. Verify metadata returned.
- [x] **ctf_steghide (extract)**: Run `action="extract"` with known passphrase. Verify hidden data extracted.
- [x] **ctf_base64 (encode)**: Encode `"Hello Hercules"` with `decode=False`. Verify base64 output.
- [x] **ctf_base64 (decode)**: Decode `"SGVsbG8gSGVyY3VsZXM="`. Verify `Hello Hercules` returned.
- [x] **ctf_xxd**: Hex dump a small file. Verify hex output with addresses.
- [x] **ctf_xxd (reverse)**: Reverse a hex dump back to binary with `reverse=True`. Verify reconstruction.

---

## 10. System & Workspace (`shell_tool.py`, `scripts_tool.py`, `file_tool.py`, `system_tool.py`)
**Target:** Local Docker Container Workspace

### Shell Execution
- [x] **shell_exec**: Run `cat /etc/os-release`. Verify Kali Linux rolling reported. Verify ANSI stripped by default.
- [x] **shell_exec (raw mode)**: Run `ls -la --color=always /` with `raw=True`. Verify ANSI codes preserved in output.
- [x] **shell_exec (truncation)**: Run `find / -name "*.conf" 2>/dev/null`. Verify output truncated with artifact path if over 8K.
- [x] **shell_exec_background**: Run `sleep 5 && echo DONE`. Verify job_id returned immediately.
- [x] **shell_check_job**: Poll the background job. Verify `is_running`, `total_lines`, `showing_last` fields present.
- [x] **shell_check_job (tail_lines)**: Poll with `tail_lines=10`. Verify only last 10 lines returned.
- [x] **shell_kill_job**: Kill a running background job. Verify `killed=True` returned.

### Scripts
- [x] **workspace_scripts (write python)**: Write `test.py` with `print("Hercules Working")`. Verify file created.
- [x] **workspace_scripts (run python)**: Run `test.py`. Verify output is `Hercules Working`.
- [x] **workspace_scripts (syntax error)**: Write a Python script with a syntax error. Verify `py_compile` catches it before execution.
- [x] **workspace_scripts (write shell)**: Write `test.sh` with `echo $USER`. Verify file created.
- [x] **workspace_scripts (run shell)**: Run `test.sh`. Verify output is `root`.

### File Management
- [x] **workspace_read_file**: Read `/etc/hostname`. Verify content returned raw (no cleaning).
- [x] **workspace_write_file**: Write `hello.txt` with content `Hercules`. Verify file persists.
- [x] **workspace_edit_file**: Edit `hello.txt` replacing `Hercules` with `Hercules MCP`. Verify edit applied.

### System
- [x] **system_stop_container**: Verify container stops cleanly. *(Run last — destructive test)*.

---

## 11. Concurrency & Resources
- [x] **Parallel light tasks**: Fire 5 simultaneous `recon_whois` calls. Verify all complete without deadlock.
- [x] **Heavy task blocking**: Fire 2 simultaneous `nmap_aggressive_scan` calls. Verify second waits for semaphore.
- [x] **Background job accumulation**: Start 3 background jobs. Verify all tracked independently. Kill all cleanly.
- [x] **Host network**: Verify container can reach host-only interfaces (e.g., `ifconfig` shows host's tun0/eth0).
- [x] **VPN passthrough**: Connect host to OpenVPN. Verify container can ping VPN target IPs.

---

## 13. Resources (In-Memory Context)
- [x] **Post-Exploitation GTFOBins**: Read `resource://post_exploitation/gtfobins`. Verify JSON data loads.
- [x] **LinPEAS script**: Read `resource://post_exploitation/linpeas`. Verify script content loads.
- [x] **WinPEAS script**: Read `resource://post_exploitation/winpeas`. Verify script content loads.
- [x] **PowerUp script**: Read `resource://post_exploitation/powerup`. Verify script content loads.

---

## 13. End-to-End Pipeline Validation
- [x] Verify `/opt/workspace/logs/` directory is created and populated with artifact logs from truncated outputs.
- [x] Verify heavy tasks respect `concurrency_lifespan` semaphore and don't timeout prematurely.
- [x] Verify all tool responses conform to the standardized envelope schema.
- [x] Run `pytest tests/test_sanitizer.py tests/test_filters.py -v` → all pass.
- [x] Token budget regression: all fixture outputs ≤ 8,000 chars after full pipeline.
