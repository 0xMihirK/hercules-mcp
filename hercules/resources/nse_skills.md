# Nmap NSE Script Authoring Skill

This resource is an operational guide for AI agents that need to design, write,
validate, debug, and run custom Nmap Scripting Engine scripts through Hercules.
Use it before generating content for `nmap_write_nse_script`, and keep it open
while choosing `nmap_run_nse_script` parameters.

## Hercules Workflow

1. Define the target condition and expected evidence.
2. Choose the NSE rule type and category.
3. Write a complete `.nse` script with metadata, NSEDoc, rule, and `action`.
4. Call `nmap_write_nse_script(name, content)`.
5. Run with `nmap_run_nse_script(target, script_name, extra_args)`.
6. For custom args, pass them in `extra_args`, for example:
   `--script-args my-script.timeout=5000,my-script.path=/admin`.
7. For debugging, add `-d`, `-v`, `--script-trace`, `--packet-trace`, or
   `--reason` in `extra_args`.

Hercules stores custom scripts under Nmap's custom script directory and runs
`nmap --script-updatedb` after writing them. The script name passed to
`nmap_run_nse_script` is sanitized and executed as `custom/<name>.nse`.

## NSE Mental Model

NSE scripts are Lua programs executed by Nmap after scan phases decide that a
script applies. The engine creates many cooperative coroutines, so scripts must
use NSE/Nsock-aware APIs for network operations and avoid blocking standard I/O.

Choose the rule type by the data needed:

| Rule | Use When | Common Inputs |
| --- | --- | --- |
| `prerule` | Work runs once before host scanning, often discovery or global setup. | Interfaces, broadcast ranges, global registry. |
| `hostrule` | Work depends on host-level facts, not one port. | Host address, OS guess, host registry. |
| `portrule` | Work targets a specific service/port. | `host`, `port`, service name, protocol, state. |
| `postrule` | Work aggregates scan-wide output. | `nmap.registry`, collected results. |

Choose categories accurately:

| Category | Meaning |
| --- | --- |
| `default` | Fast and reliable enough for `-sC`. |
| `safe` | Query/enumeration behavior with no service state changes. |
| `discovery` | Finds hosts, names, services, shares, resources, or metadata. |
| `version` | Improves or confirms service fingerprinting. |
| `vuln` | Verifies a vulnerability condition. |
| `auth` | Checks or uses authentication. |
| `brute` | Tries credentials through NSE brute libraries. |
| `intrusive` | Higher-impact probes or state-changing interactions. |
| `exploit` | Attempts exploitation behavior or exploit validation. |
| `malware` | Detects or interacts with malware indicators. |

## Required Script Shape

A production NSE script should include:

- `description`: concise first paragraph plus optional detail.
- `author`, `license`, and `categories`.
- NSEDoc tags: `@usage`, `@args`, `@output`, and `@xmloutput` when relevant.
- `local` module imports with `require`.
- Helper functions before rule/action.
- One or more rule functions.
- `action(host, port)` or `action()` returning `nil`, string, table, or table+string.

Template:

```lua
local nmap = require "nmap"
local shortport = require "shortport"
local stdnse = require "stdnse"

description = [[
One-paragraph summary of what the script detects or extracts.
]]

---
-- @usage
-- nmap -p 8080 --script custom/example --script-args example.path=/health <target>
--
-- @args example.path Path to request. Default: /.
--
-- @output
-- PORT     STATE SERVICE
-- 8080/tcp open  http
-- | example:
-- |   status: 200
--
-- @xmloutput
-- <elem key="status">200</elem>

author = "Hercules Agent"
license = "Same as Nmap--See https://nmap.org/book/man-legal.html"
categories = {"discovery", "safe"}

portrule = shortport.http

action = function(host, port)
  local out = stdnse.output_table()
  out.status = "ok"
  return out
end
```

## Lua and NSE Discipline

Use `local` for every variable and function unless intentionally exporting
metadata globals (`description`, `author`, `license`, `categories`, rules,
`action`). Globals leak between script threads and can corrupt parallel scans.

Prefer tables for structured state:

```lua
local result = {
  evidence = {},
  version = nil,
  vulnerable = false,
}
```

Avoid blocking APIs such as `io.read()` for network input. Use Nmap sockets,
`comm`, `http`, protocol libraries, or NSE helpers that cooperate with Nsock.

Use `nmap.new_try()` to make socket cleanup reliable:

```lua
local nmap = require "nmap"

local function exchange(host, port, payload)
  local socket = nmap.new_socket()
  local catch = function()
    socket:close()
  end
  local try = nmap.new_try(catch)

  socket:set_timeout(5000)
  try(socket:connect(host, port))
  try(socket:send(payload))
  local response = try(socket:receive_lines(1))
  socket:close()
  return response
end
```

Use `stdnse.get_script_args()` for parameters. Namespace args by script name:

```lua
local stdnse = require "stdnse"

local SCRIPT_NAME = "custom-http-check"
local path = stdnse.get_script_args(SCRIPT_NAME .. ".path") or "/"
local timeout = tonumber(stdnse.get_script_args(SCRIPT_NAME .. ".timeout")) or 5000
```

Use `stdnse.debug1()`, `stdnse.debug2()`, and `stdnse.verbose1()` for diagnostic
messages. They appear only when the operator enables the corresponding Nmap
debug or verbosity levels.

## Rule Selection Patterns

Use `shortport` helpers when possible:

```lua
local shortport = require "shortport"

portrule = shortport.port_or_service({80, 8080, 8443}, {"http", "https"}, {"tcp"})
```

Use `nmap.get_port_state()` for multi-port dependency checks:

```lua
local nmap = require "nmap"
local shortport = require "shortport"

portrule = function(host, port)
  if not shortport.port_or_service(8080, "http")(host, port) then
    return false
  end
  local ident = nmap.get_port_state(host, {number = 113, protocol = "tcp"})
  return ident and ident.state == "open"
end
```

Use a `hostrule` for host-wide checks:

```lua
hostrule = function(host)
  return host.ip ~= nil
end
```

Use `prerule` or `postrule` only when a port context is not appropriate.
Store scan-wide aggregate data in `nmap.registry`; store host-specific data in
`host.registry` so memory can be released after the host finishes.

## Output Strategy

Return `nil` when there is nothing meaningful to report. This keeps Nmap output
clean.

Return `stdnse.output_table()` for machine-readable XML:

```lua
local out = stdnse.output_table()
out.product = "Example Server"
out.version = "1.2.3"
out.evidence = "Server: Example/1.2.3"
return out
```

Return a table and a human string when text formatting matters:

```lua
return out, ("Detected %s %s"):format(out.product, out.version)
```

Use arrays for repeated values:

```lua
out.findings = {}
table.insert(out.findings, {path = "/admin", status = 200})
```

## Library Selection Guide

Choose the highest-level NSE library that matches the protocol:

| Need | Preferred Libraries |
| --- | --- |
| HTTP/HTTPS | `http`, `url`, `json`, `base64`, `shortport.http` |
| Raw TCP/UDP exchange | `comm`, `nmap.new_socket`, `match` |
| DNS | `dns`, `target`, `ipOps` |
| SMB/Windows | `smb`, `smb2`, `msrpc`, `unicode`, `creds` |
| FTP/SMTP/Telnet | `ftp`, `smtp`, `telnet` |
| TLS/SSH metadata | `ssl`, `ssh`, `nmap.get_ssl_certificate` |
| Databases | `mysql`, `postgres`, `redis`, `mongodb` |
| Vulnerability reporting | `vulns` |
| Credential testing | `brute`, `creds`, `unpwdb` |
| Binary parsing | `bin`, `string.unpack`, `packet`, `match` |

Use `stdnse.silent_require()` when optional libraries may be unavailable:

```lua
local have_json, json = pcall(require, "json")
if not have_json then
  return nil
end
```

## Vulnerability Reporting With `vulns`

Use `vulns` when the script verifies a known weakness or CVE. This produces
consistent output and supports `vulns.showall`.

```lua
local shortport = require "shortport"
local stdnse = require "stdnse"
local http = require "http"
local vulns = require "vulns"

description = [[Checks whether an example endpoint exposes a diagnostic token.]]
author = "Hercules Agent"
license = "Same as Nmap--See https://nmap.org/book/man-legal.html"
categories = {"vuln", "safe"}

portrule = shortport.http

action = function(host, port)
  local vuln = {
    title = "Example Diagnostic Token Exposure",
    IDS = {CVE = "CVE-2099-0001"},
    risk_factor = "Medium",
    description = "The application exposes a diagnostic token at /debug.",
    references = {"https://example.invalid/advisory"},
    dates = {disclosure = {year = 2099, month = 1, day = 1}},
  }

  local report = vulns.Report:new(SCRIPT_NAME, host, port)
  local response = http.get(host, port, "/debug")

  if response and response.status == 200 and response.body and response.body:match("diagnostic_token=") then
    vuln.state = vulns.STATE.VULNERABLE
    vuln.check_results = {"Found diagnostic_token marker in /debug response."}
  else
    vuln.state = vulns.STATE.NOT_VULN
  end

  return report:make_output(vuln)
end
```

When writing `vulns` scripts, include at least one strong condition beyond a
single generic word. Good evidence combines status, header, body marker,
version range, timing, or protocol-specific behavior.

## Credentials and Brute-Force Patterns

Use the `brute` framework for login guessing rather than hand-rolled loops. It
coordinates thread counts, credentials, account lockout controls, and output.
Store discovered credentials with `creds.Credentials:add()` so later scripts can
reuse them through Nmap registry.

Agent checklist for brute scripts:

- Define a driver with `connect`, `login`, and `disconnect` behavior.
- Use `unpwdb` for usernames/passwords.
- Respect args such as `userdb`, `passdb`, `unpwdb.timelimit`,
  `brute.threads`, and `brute.firstonly`.
- Return credential tables, not raw noisy logs.
- Add `brute` and `auth` categories.

## Performance and Concurrency

NSE scales through coroutines. Write scripts so blocked network waits yield to
the engine:

- Use `socket:set_timeout()` before connecting or reading.
- Use `match.numbytes(n)` or `match.pattern_limit(pattern, limit)` for streams.
- Cap payload loops and expose limits through `--script-args`.
- Store host data in `host.registry`; use `nmap.registry` only for scan-wide
  data.
- Use `nmap.condvar()` if multiple worker coroutines update shared state.
- Return early when service fingerprint, status code, or protocol magic fails.

## Skeleton: Basic Banner or Protocol Probe

```lua
local nmap = require "nmap"
local shortport = require "shortport"
local stdnse = require "stdnse"

description = [[Reads a single banner line from a custom TCP service.]]
author = "Hercules Agent"
license = "Same as Nmap--See https://nmap.org/book/man-legal.html"
categories = {"discovery", "safe"}

portrule = shortport.port_or_service(12345, "example", "tcp")

action = function(host, port)
  local socket = nmap.new_socket()
  local catch = function() socket:close() end
  local try = nmap.new_try(catch)
  socket:set_timeout(4000)

  try(socket:connect(host, port))
  local banner = try(socket:receive_lines(1))
  socket:close()

  if not banner or banner == "" then
    return nil
  end

  local out = stdnse.output_table()
  out.banner = banner
  return out
end
```

## Skeleton: Authenticated HTTP Workflow

```lua
local http = require "http"
local shortport = require "shortport"
local stdnse = require "stdnse"

local SCRIPT_NAME = "custom-auth-http"

description = [[Logs in to an HTTP app and checks an authenticated endpoint.]]
author = "Hercules Agent"
license = "Same as Nmap--See https://nmap.org/book/man-legal.html"
categories = {"auth", "discovery"}

portrule = shortport.http

local function arg(name, default)
  return stdnse.get_script_args(SCRIPT_NAME .. "." .. name) or default
end

action = function(host, port)
  local user = arg("user", "admin")
  local pass = arg("pass", "admin")
  local login_path = arg("login_path", "/login")
  local check_path = arg("check_path", "/admin")

  local login = http.post(host, port, login_path, nil, nil, {
    username = user,
    password = pass,
  })
  if not login or login.status ~= 200 then
    return nil
  end

  local cookies = login.cookies
  local response = http.get(host, port, check_path, {cookies = cookies})
  if not response or response.status ~= 200 then
    return nil
  end

  local out = stdnse.output_table()
  out.authenticated = true
  out.path = check_path
  out.status = response.status
  return out
end
```

## Skeleton: Multi-Port Dependency

```lua
local nmap = require "nmap"
local shortport = require "shortport"
local stdnse = require "stdnse"

description = [[Runs only when a service and its helper port are open.]]
author = "Hercules Agent"
license = "Same as Nmap--See https://nmap.org/book/man-legal.html"
categories = {"discovery", "safe"}

portrule = function(host, port)
  if not shortport.port_or_service(8080, "http", "tcp")(host, port) then
    return false
  end
  local helper = nmap.get_port_state(host, {number = 113, protocol = "tcp"})
  return helper and helper.state == "open"
end

action = function(host, port)
  local out = stdnse.output_table()
  out.main_port = port.number
  out.helper_port = 113
  out.dependency = "present"
  return out
end
```

## Skeleton: Custom Binary Protocol

```lua
local nmap = require "nmap"
local shortport = require "shortport"
local stdnse = require "stdnse"
local match = require "match"

description = [[Sends a binary probe and parses a fixed-size response.]]
author = "Hercules Agent"
license = "Same as Nmap--See https://nmap.org/book/man-legal.html"
categories = {"version", "discovery"}

portrule = shortport.port_or_service(9999, "custom-binary", "tcp")

action = function(host, port)
  local socket = nmap.new_socket()
  local catch = function() socket:close() end
  local try = nmap.new_try(catch)
  socket:set_timeout(3000)

  try(socket:connect(host, port))
  try(socket:send(string.char(0x01, 0x00, 0x00, 0x00)))
  local data = try(socket:receive_buf(match.numbytes(16), true))
  socket:close()

  if not data or #data < 8 then
    return nil
  end

  local major, minor = data:byte(5), data:byte(6)
  local out = stdnse.output_table()
  out.protocol = "custom-binary"
  out.version = ("%d.%d"):format(major, minor)
  out.raw_length = #data
  return out
end
```

## Skeleton: Intrusive or Exploit Category Pattern

Use explicit categories and operator-controlled args when a script sends a
payload intended to trigger a vulnerability path or state transition.

```lua
local http = require "http"
local shortport = require "shortport"
local stdnse = require "stdnse"

local SCRIPT_NAME = "custom-exploit-check"

description = [[Sends an operator-supplied verification payload to an endpoint.]]
author = "Hercules Agent"
license = "Same as Nmap--See https://nmap.org/book/man-legal.html"
categories = {"intrusive", "exploit"}

portrule = shortport.http

action = function(host, port)
  local path = stdnse.get_script_args(SCRIPT_NAME .. ".path") or "/api/run"
  local marker = stdnse.get_script_args(SCRIPT_NAME .. ".marker") or "hercules-marker"
  local payload = stdnse.get_script_args(SCRIPT_NAME .. ".payload") or ("echo " .. marker)

  local response = http.post(host, port, path, nil, nil, {cmd = payload})
  if not response or not response.body then
    return nil
  end

  local out = stdnse.output_table()
  out.path = path
  out.marker_reflected = response.body:find(marker, 1, true) ~= nil
  out.status = response.status
  return out
end
```

Run with:

```text
extra_args="--script-args custom-exploit-check.path=/api/run,custom-exploit-check.marker=abc123 -d --script-trace"
```

## Agent Decision Tree

1. Is the target a known port/service?
   - Yes: use `portrule` and `shortport`.
   - No: use `hostrule` or `prerule`.
2. Is the protocol supported by nselib?
   - Yes: use the protocol library.
   - No: use `nmap.new_socket`, `comm`, and `match` limits.
3. Is the result a vulnerability?
   - Yes: use `vulns.Report`.
   - No: return a structured `stdnse.output_table`.
4. Does the script need user input?
   - Use namespaced `stdnse.get_script_args`.
5. Does the script keep state?
   - Per host: `host.registry`.
   - Across scan: `nmap.registry` with bounded data.
6. Does the script require debugging?
   - Add `stdnse.debug*`, run with `-d`, `-v`, `--script-trace`.

## Validation Loop

Before calling `nmap_write_nse_script`:

- Confirm all imports are `local`.
- Confirm metadata globals exist.
- Confirm category labels match behavior.
- Confirm rule function returns boolean.
- Confirm `action` closes sockets on all paths.
- Confirm args are namespaced.
- Confirm output is structured and returns `nil` on no finding.

After writing:

1. Run a narrow target/port first:
   `nmap_run_nse_script(target, script_name, extra_args="-p 8080 -d")`.
2. If there is no output, add `--script-trace` and check rule targeting.
3. If the script is not found, write it again and confirm the returned
   `script_db_updated` field from `nmap_write_nse_script`.
4. If XML parsing fails in Hercules output, inspect raw stdout via tool output
   and simplify returned table keys.
5. If sockets hang, add or lower `socket:set_timeout`.

## Common Failure Fixes

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| Script never runs | Rule does not match service or port. | Use `-p`, `-sV`, or broader `shortport` logic. |
| `attempt to index nil` | Missing response field. | Check response/table exists before indexing. |
| No output on vulnerable target | Returning `nil` or matcher too strict. | Add `stdnse.debug1` and run with `-d`. |
| Scan stalls | Blocking read or no timeout. | Use NSE sockets, `match` limits, and `set_timeout`. |
| XML output poor | Returned raw string only. | Return `stdnse.output_table`. |
| Args ignored | Wrong namespace. | Match `SCRIPT_NAME .. ".arg"` with `--script-args`. |

## Hercules Examples

Write:

```json
{
  "name": "custom-http-check",
  "content": "<complete Lua NSE script>"
}
```

Run:

```json
{
  "target": "https://target.example",
  "script_name": "custom-http-check",
  "extra_args": "-p 443 -sV --script-args custom-http-check.path=/health -d"
}
```

For complex NSE development, iterate in small steps: first prove the rule runs,
then prove one request works, then add parsing, then add structured output, then
add optional args and richer detection.
