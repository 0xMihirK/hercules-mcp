# Nuclei Template Authoring Skill

This resource is an operational guide for AI agents that need to design, write,
validate, debug, and run custom Nuclei templates through Hercules. Use it before
generating content for `nuclei_write_template`, and keep it open while choosing
`nuclei_run` parameters.

## Hercules Workflow

1. Define the detection goal and strongest observable evidence.
2. Choose the protocol block: `http`, `dns`, `ssl`, `tcp`, `network`,
   `websocket`, `headless`, `javascript`, `code`, or `file`.
3. Write a complete YAML template with `id`, `info`, protocol requests,
   matchers, and extractors.
4. Call `nuclei_write_template(path, content)`.
5. Validate with `shell_exec("nuclei -validate -t /opt/workspace/nuclei-templates/<path>")`
   or run via `nuclei_run(..., templates="/opt/workspace/nuclei-templates/<path>")`.
6. Run with `nuclei_run(targets, templates, severity, tags, rate_limit, extra_args)`.
7. Debug with `extra_args="-debug -stats -vv"` or narrower flags such as
   `-trace-log`, `-proxy`, `-retries`, `-timeout`, `-headless`, or `-interactions-cache-size`.

Hercules writes custom templates under `/opt/workspace/nuclei-templates/`.
Use absolute template paths when running custom content.

## Template Decision Tree

1. Is one request enough?
   - Use a single `http` request with strong matchers.
2. Does the second request depend on the first?
   - Use multiple requests plus `extractors` and internal matchers, or `flow`.
3. Is the vulnerability blind?
   - Use interactsh variables and match on `interactsh_protocol` or related parts.
4. Is JavaScript/browser behavior required?
   - Use `headless` for DOM/browser state or `javascript`/`code` for local logic.
5. Is protocol normalization a problem?
   - Use raw HTTP and `unsafe: true`.
6. Is the test broad fuzzing?
   - Use `payloads`, `attack`, or `fuzzing` with scoped keys and matchers.
7. Is false-positive resistance weak?
   - Add a second evidence layer: status, content type, product marker,
     version regex, extracted token, timing check, or negative matcher.

## Required Template Shape

Every template should include:

- `id`: unique, lowercase, descriptive, no spaces.
- `info.name`: human-readable title.
- `info.author`: string or list.
- `info.severity`: `info`, `low`, `medium`, `high`, or `critical`.
- `info.description`: short explanation of what is checked.
- `info.tags`: comma-separated taxonomy.
- `classification` when applicable: `cve-id`, `cwe-id`, `cvss-score`,
  `epss-score`, `cpe`.
- Protocol block with requests.
- Matchers scoped to `part`.
- Extractors when values are needed in later steps or output.

Minimal HTTP template:

```yaml
id: example-panel-detect

info:
  name: Example Admin Panel Detection
  author: hercules-agent
  severity: info
  description: Detects an Example admin panel by title and response header.
  tags: tech,panel,example

http:
  - method: GET
    path:
      - "{{BaseURL}}/admin"

    matchers-condition: and
    matchers:
      - type: status
        status:
          - 200
      - type: word
        part: body
        words:
          - "<title>Example Admin</title>"
      - type: word
        part: header
        words:
          - "X-Example-App"
```

## Metadata and Naming

Use `id` values that encode product and issue:

- `product-panel-detect`
- `product-cve-2026-1234-rce`
- `product-default-credentials`
- `product-graphql-introspection`
- `cloud-service-public-bucket`

Use tags that help `nuclei_run(tags=...)` selection:

```yaml
tags: cve,cve2026,rce,kev,product
```

Use classification for known issues:

```yaml
classification:
  cve-id: CVE-2026-1234
  cwe-id: CWE-78
  cvss-score: 9.8
```

Use metadata for search and integration hints:

```yaml
metadata:
  vendor: example
  product: example-server
  shodan-query: 'http.title:"Example Server"'
  verified: true
```

## HTTP Request Patterns

Standard request:

```yaml
http:
  - method: GET
    path:
      - "{{BaseURL}}/api/version"
    redirects: true
    max-redirects: 3
    headers:
      User-Agent: Mozilla/5.0 Hercules-Nuclei
```

POST with JSON:

```yaml
http:
  - method: POST
    path:
      - "{{BaseURL}}/api/login"
    headers:
      Content-Type: application/json
    body: |
      {"username":"{{username}}","password":"{{password}}"}
```

Raw HTTP request:

```yaml
http:
  - raw:
      - |
        GET /admin HTTP/1.1
        Host: {{Hostname}}
        User-Agent: Hercules-Nuclei
        Connection: close
```

Raw unsafe request for non-normalized payloads:

```yaml
http:
  - raw:
      - |
        GET / HTTP/1.1
        Host: {{Hostname}}
        Transfer-Encoding: chunked
        Transfer-Encoding: cow

        0

    unsafe: true
```

## Matchers

Matchers decide whether a response is a finding. Scope every matcher to the
smallest useful `part`.

Common matcher types:

```yaml
matchers-condition: and
matchers:
  - type: status
    status:
      - 200
  - type: word
    part: body
    words:
      - "Welcome to Example"
  - type: regex
    part: body
    regex:
      - 'Example Server v([0-9]+\.[0-9]+\.[0-9]+)'
  - type: dsl
    dsl:
      - "status_code == 200"
      - "contains(tolower(body), 'example')"
```

Use negative matchers for exclusion logic:

```yaml
  - type: word
    part: body
    negative: true
    words:
      - "Access Denied"
      - "Request blocked"
```

Use internal matchers for workflow gates that should not produce their own
result:

```yaml
  - type: word
    part: body
    internal: true
    words:
      - "csrf_token"
```

High-confidence matching usually combines:

- A product marker.
- A version or endpoint marker.
- A vulnerability-specific proof.
- A status/content-type condition.
- A negative matcher for generic block/error pages.

## Extractors

Extractors parse data from responses. Use them for output or later requests.

Regex extractor:

```yaml
extractors:
  - type: regex
    name: version
    part: body
    group: 1
    regex:
      - 'Version: ([0-9.]+)'
```

Internal dynamic extractor:

```yaml
extractors:
  - type: regex
    name: csrf
    part: body
    group: 1
    internal: true
    regex:
      - 'name="csrf" value="([^"]+)"'
```

Header extractor:

```yaml
extractors:
  - type: kval
    kval:
      - server
      - x_powered_by
```

JSON extractor:

```yaml
extractors:
  - type: json
    name: token
    internal: true
    json:
      - ".token"
```

## DSL Notes

Use DSL for conditions that combine response properties:

```yaml
matchers:
  - type: dsl
    dsl:
      - "status_code == 200"
      - "contains(content_type, 'application/json')"
      - "len(body) < 2048"
      - "contains(body, 'admin')"
    condition: and
```

Useful DSL functions/patterns:

- `contains(body, "text")`
- `contains(tolower(body), "text")`
- `regex("pattern", body)`
- `len(body)`
- `md5(body)` or `sha256(body)` for stable fingerprints.
- `duration` for timing checks.
- `status_code`, `content_type`, `header`, `body`, `all_headers`.

Prefer exact checks before broad regex. Use regex when the value is variable.

## Payloads and Attack Modes

Use payloads for parameterized checks:

```yaml
payloads:
  path:
    - "/admin"
    - "/console"
    - "/manager"

http:
  - method: GET
    path:
      - "{{BaseURL}}{{path}}"
    attack: batteringram
```

Attack modes:

| Mode | Use When |
| --- | --- |
| `sniper` | One payload variable at a time. |
| `batteringram` | Same payload injected into multiple positions. |
| `pitchfork` | Multiple lists advance together by index. |
| `clusterbomb` | Cartesian product across payload lists. |

Use `stop-at-first-match: true` when one positive result is enough:

```yaml
stop-at-first-match: true
```

## Fuzzing

Use fuzzing when the exact parameter names are unknown or when testing multiple
parts of a request.

```yaml
http:
  - method: GET
    path:
      - "{{BaseURL}}/search?q=test"

    fuzzing:
      - part: query
        type: replace
        mode: single
        keys:
          - q
        fuzz:
          - "' OR '1'='1"
          - "\" OR \"1\"=\"1"

    matchers-condition: and
    matchers:
      - type: status
        status:
          - 200
      - type: word
        part: body
        words:
          - "SQL syntax"
          - "mysql_fetch"
        condition: or
```

Fuzzing design checklist:

- Scope `part` to query, body, path, header, or cookie.
- Use `keys`, `keys-regex`, or `values` filters.
- Use `mode: single` for isolated parameter attribution.
- Add negative matchers for WAF or generic error pages.
- Use rate limits through `nuclei_run(rate_limit=...)`.

## Flow and Multi-Step Templates

Use `flow` when requests must happen conditionally:

```yaml
id: example-flow-auth-check

info:
  name: Example Authenticated Flow Check
  author: hercules-agent
  severity: medium
  tags: auth,flow,example

flow: http(1) && http(2)

http:
  - method: GET
    path:
      - "{{BaseURL}}/login"
    extractors:
      - type: regex
        name: csrf
        part: body
        group: 1
        internal: true
        regex:
          - 'name="csrf" value="([^"]+)"'
    matchers:
      - type: word
        internal: true
        part: body
        words:
          - "csrf"

  - method: POST
    path:
      - "{{BaseURL}}/login"
    headers:
      Content-Type: application/x-www-form-urlencoded
    body: "username={{username}}&password={{password}}&csrf={{csrf}}"
    cookie-reuse: true
    matchers:
      - type: word
        part: body
        words:
          - "Dashboard"
```

Use `cookie-reuse: true` when a response sets cookies required by the next
request.

## OOB and Interactsh

Use OOB checks for blind SSRF, blind command injection, XXE, deserialization, or
callbacks that only prove execution through an external interaction.

```yaml
id: example-blind-ssrf

info:
  name: Example Blind SSRF via Callback
  author: hercules-agent
  severity: high
  tags: ssrf,oob,interactsh

http:
  - method: POST
    path:
      - "{{BaseURL}}/fetch"
    headers:
      Content-Type: application/json
    body: |
      {"url":"http://{{interactsh-url}}/ssrf"}

    matchers-condition: and
    matchers:
      - type: word
        part: interactsh_protocol
        words:
          - "http"
      - type: word
        part: interactsh_request
        words:
          - "ssrf"
```

Run with interactsh enabled by default Nuclei behavior, or set custom interactsh
options in `extra_args` when needed.

## Headless Browser Pattern

Use `headless` for DOM XSS, client-side routing, browser-only redirects, or
JavaScript-rendered evidence.

```yaml
id: example-headless-dom-xss

info:
  name: Example DOM XSS Headless Check
  author: hercules-agent
  severity: medium
  tags: xss,headless,dom

headless:
  - steps:
      - action: navigate
        args:
          url: "{{BaseURL}}/search?q=%3Cimg%20src=x%20onerror=alert(document.domain)%3E"
      - action: waitload
      - action: script
        name: page_check
        args:
          code: |
            () => document.body.innerText

    matchers:
      - type: word
        part: page_check
        words:
          - "Search"
```

Run with `extra_args="-headless -debug"` when debugging browser execution.

## Network, DNS, SSL, and WebSocket Patterns

DNS:

```yaml
dns:
  - name: "{{FQDN}}"
    type: TXT
    matchers:
      - type: word
        part: answer
        words:
          - "v=spf1"
```

SSL:

```yaml
ssl:
  - address: "{{Host}}:{{Port}}"
    matchers:
      - type: dsl
        dsl:
          - "contains(subject_cn, 'example')"
```

TCP/network:

```yaml
tcp:
  - inputs:
      - data: "00000000"
        type: hex
    host:
      - "{{Hostname}}"
    read-size: 64
    matchers:
      - type: word
        part: data
        words:
          - "Example"
```

WebSocket:

```yaml
websocket:
  - address: "{{BaseURL}}/ws"
    inputs:
      - data: '{"type":"ping"}'
    matchers:
      - type: word
        part: body
        words:
          - "pong"
```

## JavaScript and Code Protocol Patterns

Use JavaScript when Nuclei's JS runtime is the best fit for protocol logic,
token construction, or multi-step parsing. Use code protocol when local command
execution is part of the template design and the template can be signed or run
with the required Nuclei options.

JavaScript sketch:

```yaml
javascript:
  - code: |
      const result = "computed-" + template["BaseURL"];
      Export(result);
    matchers:
      - type: word
        words:
          - "computed-"
```

Code protocol sketch:

```yaml
code:
  - engine:
      - python3
    source: |
      print("probe-ok")
    matchers:
      - type: word
        words:
          - "probe-ok"
```

Code templates require Nuclei signing or execution options compatible with the
installed Nuclei version. Validate them before using `nuclei_run`.

## Race and Timing Patterns

Race checks:

```yaml
http:
  - method: POST
    path:
      - "{{BaseURL}}/transfer"
    body: "amount=10&to=test"
    race: true
    threads: 20
    matchers:
      - type: dsl
        dsl:
          - "status_code == 200"
          - "contains(body, 'success')"
        condition: and
```

Timing check:

```yaml
matchers:
  - type: dsl
    dsl:
      - "duration >= 5"
      - "status_code == 200"
    condition: and
```

Use timing matchers with a control request when possible so network latency does
not become the only signal.

## Skeleton: LFI Verification

```yaml
id: example-lfi-passwd

info:
  name: Example LFI /etc/passwd Verification
  author: hercules-agent
  severity: high
  tags: lfi,path-traversal,example

http:
  - method: GET
    path:
      - "{{BaseURL}}/download?file=../../../../etc/passwd"

    matchers-condition: and
    matchers:
      - type: status
        status:
          - 200
      - type: regex
        part: body
        regex:
          - "root:.*:0:0:"
      - type: word
        part: header
        words:
          - "text/html"
          - "text/plain"
        condition: or
```

## Skeleton: API/JWT None Algorithm Pattern

```yaml
id: example-jwt-none-accepted

info:
  name: Example JWT None Algorithm Acceptance
  author: hercules-agent
  severity: high
  tags: jwt,auth-bypass,api

variables:
  none_jwt: "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VyIjoiYWRtaW4ifQ."

http:
  - method: GET
    path:
      - "{{BaseURL}}/api/me"
    headers:
      Authorization: "Bearer {{none_jwt}}"

    matchers-condition: and
    matchers:
      - type: status
        status:
          - 200
      - type: word
        part: body
        words:
          - "admin"
      - type: word
        part: header
        negative: true
        words:
          - "WWW-Authenticate"
```

## Skeleton: Raw Unsafe HTTP Request

```yaml
id: example-raw-unsafe-smuggling-probe

info:
  name: Example Raw Unsafe HTTP Differential Probe
  author: hercules-agent
  severity: medium
  tags: raw,unsafe,http

http:
  - raw:
      - |
        POST / HTTP/1.1
        Host: {{Hostname}}
        Content-Length: 4
        Transfer-Encoding: chunked

        0

        X
    unsafe: true

    matchers:
      - type: dsl
        dsl:
          - "status_code >= 400 && status_code < 500"
```

## Validation Loop

Before `nuclei_write_template`:

- Confirm YAML indentation uses spaces.
- Confirm `id`, `info.name`, `info.author`, `info.severity`, and `info.tags`.
- Confirm protocol block syntax matches Nuclei schema.
- Confirm matcher parts are scoped.
- Confirm extractors use `internal: true` when only needed for later requests.
- Confirm flow references valid request indexes.
- Confirm payload variables are defined before use.

After writing:

1. Validate:
   `shell_exec("nuclei -validate -t /opt/workspace/nuclei-templates/<path>")`.
2. Run one target:
   `nuclei_run(targets="https://target", templates="/opt/workspace/nuclei-templates/<path>", rate_limit=25)`.
3. If validation fails, fix YAML shape first.
4. If no finding appears, run with `extra_args="-debug -vv"`.
5. If requests are wrong, use `-proxy` or `-debug-req -debug-resp` depending
   on the installed Nuclei version.
6. If a finding is noisy, add product/version/status/content-type/negative
   matchers.

## Common Failure Fixes

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| `yaml: did not find expected key` | Indentation or quoting error. | Normalize spaces and quote `:` in strings. |
| Template validates but never matches | Matchers too strict or wrong `part`. | Add `-debug`, inspect body/header, adjust part. |
| Too many findings | Single weak matcher. | Add `matchers-condition: and` and another evidence layer. |
| Extracted variable empty | Regex group or internal extractor issue. | Add a temporary non-internal extractor and debug response. |
| Flow skips later request | Earlier internal matcher failed. | Debug request 1 and loosen the gate. |
| OOB not firing | Payload not reaching sink or interactsh blocked. | Check raw request and interactsh matcher part. |
| Headless no result | Browser flag or selector mismatch. | Run with `-headless -debug`, simplify actions. |

## Hercules Examples

Write:

```json
{
  "path": "custom/example-lfi.yaml",
  "content": "<complete YAML template>"
}
```

Validate:

```json
{
  "command": "nuclei -validate -t /opt/workspace/nuclei-templates/custom/example-lfi.yaml",
  "timeout": 60
}
```

Run:

```json
{
  "targets": "https://target.example",
  "templates": "/opt/workspace/nuclei-templates/custom/example-lfi.yaml",
  "severity": "medium,high,critical",
  "tags": "lfi,example",
  "rate_limit": 25,
  "extra_args": "-debug -stats"
}
```

For complex Nuclei development, iterate in layers: first make a syntactically
valid template, then prove the request reaches the target, then add one matcher,
then add extractors/flow, then add false-positive controls, then tune execution
with `rate_limit`, `tags`, and `extra_args`.
