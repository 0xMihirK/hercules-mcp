"""Authored investigation programs, gated by real MCP results.

These are scripted model decisions. No step supplies a scanner/tool result and
no challenge solver is placed in the workspace. Dynamic arguments are derived
from the preceding evidence (job IDs, reference IDs and recovered clues).
"""
import json

HOST = "172.30.42.10"
URL = "http://" + HOST + ":8000"


def step(tool, arguments, expect, observation, **options):
    return {"tool": tool, "arguments": arguments, "expect": expect, "observation": observation, **options}


def shell(command, expect, observation, **options):
    return step("shell_exec", {"command": command, "timeout": 45}, expect, observation, **options)


SCOPE = step("workspace_read_file", {"path": "scope.md"}, "Only the lab fixture", "My owned runtime is ready. I will verify the supplied scope, investigate the internal lab and stop the runtime after reporting.")
START = step("system_start_container", {}, "session_id", "Connecting MCP has not started Kali. I will explicitly start the runtime before executing tools.")
DNS = step("recon_dns", {"tool": "dig", "target": HOST, "server": HOST, "record_type": "A"}, HOST, "I will query the lab DNS server directly. The result will establish the local address before service discovery.")
NMAP = step("nmap_scan", {"mode": "port", "target": HOST, "ports": "8000,8080,8443", "extra_args": "-Pn -sT"}, "8000", "DNS is confirmed. I will map only the three scoped service ports; an open port alone will not establish a vulnerability.")
HTTP = step("network_curl", {"url": URL + "/health", "extra_args": "--max-time 5 -o /opt/workspace/artifacts/health.txt"}, "exit_code", "I will confirm that the discovered HTTP service responds, retaining the response as a file.")
SKILL = step("browser_skill", {}, "browser", "Before browser operations, I will read Hercules's actual browser guidance and use fresh snapshots for targeting.")
OPEN = step("browser_open", {"url": URL + "/login", "session": "review"}, "Atlas", "I will check the live local page in the native browser backend rather than infer behavior from headers.")
SNAPSHOT = step("browser_snapshot", {"session": "review", "interactive": True}, "Sign in", "The page has loaded. I will inspect the current accessibility tree before choosing form controls.")
DEBUG_TEMPLATE = """id: hercules-lab-debug
info:
  name: Disposable Atlas debug endpoint
  author: hercules-showcase
  severity: info
http:
  - method: GET
    path:
      - '{{BaseURL}}/debug'
    matchers-condition: and
    matchers:
      - type: status
        status: [200]
      - type: word
        words: ['\"debug\": true', 'disposable']
        condition: and
"""

PCAP_INSPECT = """python3 - <<'PY'
import json,struct
from pathlib import Path
p=Path('/opt/workspace/challenge/route.pcap').read_bytes(); cursor=24; clues=[]
while cursor<len(p):
    ts,us,size,orig=struct.unpack_from('<IIII',p,cursor); cursor+=16
    packet=p[cursor:cursor+size]; cursor+=size
    clue=json.loads(packet[42:]); clues.append(clue)
assert [c['sequence'] for c in clues]==[1,2,3]
print(json.dumps({'packets':clues,'next':'Inspect the carrier, then apply the route rule from its archive manifest.'},indent=2))
PY"""
VERIFY_FLAG = """python3 - <<'PY'
import hashlib,json,zlib
from pathlib import Path
p=Path('/opt/workspace/artifacts/forensics'); m=json.loads((p/'manifest.json').read_text())
flag=zlib.decompress((p/'decrypted.bin').read_bytes()); digest=hashlib.sha256(flag).hexdigest()
decoy=(p/'decoy.txt').read_bytes().strip(); decoy_digest=hashlib.sha256(decoy).hexdigest()
assert digest==m['flag_sha256'] and decoy_digest!=digest
result={'flag':flag.decode(),'sha256':digest,'checksum_match':True,'decoy_match':False}
(p/'verification.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
PY"""


CASES = {
 "network": {
  "title": "Service boundary map", "objective": "Map the scoped services and compare a closed-port control.", "prompt": "Map the scoped fixture, compare open and closed ports, verify HTTP and TLS, and report only observed service behavior.",
  "summary": "The investigation checks a negative port control before correlating DNS, services, HTTP, and certificate evidence.",
  "steps": [DNS,NMAP,
   shell("nmap -Pn -sT -sV --version-light -p 8000,8080,8443 " + HOST + " -oA /opt/workspace/artifacts/services", "8000", "The ports are reachable. I will verify service behavior with version detection and retain both text and XML output."),
   HTTP,
   step("network_curl", {"url":URL + "/robots.txt","extra_args":"--max-time 5 -o /opt/workspace/artifacts/robots.txt"}, "exit_code", "The HTTP service is healthy. I will inspect its declared routes before interpreting what the application exposes."),
   shell("openssl s_client -connect " + HOST + ":8443 -CAfile /opt/workspace/lab-cert.pem -verify_return_error </dev/null > /opt/workspace/artifacts/tls.txt 2>&1; cat /opt/workspace/artifacts/tls.txt", "Verification: OK|Verify return code: 0", "I will verify the lab certificate with its supplied CA; I will not disable certificate validation."),
   step("workspace_read_file",{"path":"artifacts/services.xml","max_bytes":4096}, "nmaprun", "I will inspect the structured scan artifact before writing the inventory. The report should distinguish discovery from verified application behavior."),
   shell("nmap -Pn -sT -p 9999 " + HOST + " -oN /opt/workspace/artifacts/closed-port.txt; cat /opt/workspace/artifacts/closed-port.txt", "closed|filtered", "The negative-control port should not look like an exposed service. I will save its actual result before drawing a network boundary."),
   step("workspace_read_file",{"path":"artifacts/closed-port.txt"}, "9999", "I will include the negative control in the report so coverage is explicit.")]
 },
 "services": {
  "title":"Version and exploit triage", "objective": "Check whether a version and exploit lead matches the observed product.", "prompt":"Compare the local service identity and build with a supplied synthetic advisory and SearchSploit leads. Reject a product mismatch and report remaining uncertainty.",
  "summary":"A broad exploit hit is read, then rejected against the fixture's observed product and local advisory. No CVE is invented for the synthetic app.",
  "steps":[NMAP,
   shell("nmap -Pn -sT -sV --version-light -p 8000 " + HOST + " -oA /opt/workspace/artifacts/assessment", "8000", "I will obtain service-detection evidence before consulting vulnerability references."),
   step("network_curl",{"url":URL,"extra_args":"--max-time 5 -D /opt/workspace/artifacts/headers.txt -o /opt/workspace/artifacts/home.html"}, "exit_code", "I will retain the actual headers and page, then compare them with the scanner's service classification."),
   step("searchsploit",{"action":"search","query_or_id":"http server"}, "RESULTS|results|total", "I will search the local Exploit-DB catalog for HTTP-server leads. This is reference gathering, not exploitation."),
   step("searchsploit",{"action":"get","query_or_id":"$reference_id"}, "stdout|content|path", "A reference exists. I will read it and compare its product and prerequisites with the Atlas lab evidence.", dynamic="reference"),
   step("workspace_read_file",{"path":"artifacts/headers.txt"}, "AtlasLab", "The lab identifies itself as AtlasLab. I will reject a generic catalog hit whose affected product or deployment prerequisites are not established."),
   step("network_curl",{"url":URL + "/admin","extra_args":"--max-time 5 -o /opt/workspace/artifacts/admin-denied.html"}, "exit_code", "I will verify the administrative route's actual response. A 403 is an access-control observation, not evidence of compromise."),
   step("workspace_read_file",{"path":"challenge/advisory.json"}, "product mismatch", "The supplied advisory concerns another product. Version-like text alone cannot establish applicability, so I will reject this lead."),
   step("workspace_read_file",{"path":"artifacts/admin-denied.html"}, "Access denied", "The route still denies access. I will report exposure and uncertainty separately from exploitability.")]
 },
 "website": {
  "title":"Web and API exposure", "objective": "Verify a web exposure and reject unauthenticated API guesses.", "prompt":"Discover the local application's routes, compare unauthenticated API and debug behavior, reject a missing backup route, and verify one exposure independently.",
  "summary":"A bounded fuzz, a local Nuclei matcher, HTTP controls, and browser confirmation establish the debug exposure while the profile API and backup guesses are rejected.",
  "steps":[step("fuzz_dirs",{"tool":"ffuf","target_url":URL,"wordlist":"/opt/workspace/paths.txt","threads":2,"extra_args":"-mc all -fc 404 -rate 15"}, "debug", "I will discover only the fixture's small route list, with bounded concurrency and a retained tool result."),
   step("web_scan",{"tool":"whatweb","target":URL}, "Atlas", "Directory discovery found a lead. I will fingerprint the actual application before selecting a verification check."),
   step("nuclei_write_template",{"path":"lab-debug.yaml","content":DEBUG_TEMPLATE}, "path|success", "I will author a local Nuclei check requiring both HTTP 200 and the explicit disposable debug marker."),
   step("nuclei_run",{"targets":URL,"templates":"/opt/workspace/nuclei-templates/lab-debug.yaml","rate_limit":10,"extra_args":"-duc -ni"}, "hercules-lab-debug", "I will run only this local template. Built-in online template updates and interactsh are disabled."),
   step("network_curl",{"url":URL + "/backup","extra_args":"--max-time 5 -o /opt/workspace/artifacts/backup-404.html"}, "exit_code", "I will test the suspected backup route independently. Its normal 404 must be rejected rather than counted as an exposure."),SKILL,
   step("browser_open",{"url":URL + "/debug","session":"review"}, "url|success", "I will confirm the debug response in the browser before accepting the scanner lead."),
   step("browser_read",{"what":"text","target":"body","target_type":"css","session":"review"}, "disposable", "The browser confirms the disposable debug data. I will document this limited exposure without inventing credentials or exploitability."),
   step("browser_screenshot",{"path":"artifacts/debug.png","session":"review"}, "image|screenshot|path", "I will save visual evidence alongside the raw HTTP and scanner artifacts."),
   step("network_curl",{"url":URL + "/api/profile","extra_args":"--max-time 5 -o /opt/workspace/artifacts/profile-denied.json"}, "exit_code", "The profile endpoint is a separate hypothesis. I will test it without a session rather than assume the debug exposure grants account access."),
   step("workspace_read_file",{"path":"artifacts/profile-denied.json"}, "login required", "The API rejects unauthenticated access. I will keep this negative control out of the findings list.")]
 },
 "tls": {
  "title":"TLS and protocol review", "objective": "Trace the redirect, verify TLS, and test the protocol directly.", "prompt":"Trace the scoped redirect, verify the certificate with the supplied CA, send a manual HTTP request through Ncat, and compare browser behavior with transport evidence.",
  "summary":"Independent TLS and Ncat checks separate protocol reachability from browser trust; a missing route supplies a negative control.",
  "steps":[DNS,
   step("network_curl",{"url":"http://"+HOST+":8080","follow_redirects":False,"extra_args":"--max-time 5 -o /opt/workspace/artifacts/redirect.txt"}, "exit_code", "I will inspect the first redirect without following it, so each hop remains explicit."),
   step("workspace_read_file",{"path":"artifacts/redirect.txt"}, "302|Redirect", "The first hop redirects to the local TLS endpoint. I will verify the certificate before requesting that destination."),
   shell("openssl s_client -connect " + HOST + ":8443 -CAfile /opt/workspace/lab-cert.pem -verify_return_error </dev/null > /opt/workspace/artifacts/tls.txt 2>&1; cat /opt/workspace/artifacts/tls.txt", "Verification: OK|Verify return code: 0", "I will validate the actual chain with the supplied lab CA, preserving OpenSSL diagnostics."),
   step("network_curl",{"url":"https://"+HOST+":8443/login","extra_args":"--cacert /opt/workspace/lab-cert.pem --max-time 5 -o /opt/workspace/artifacts/tls-login.html"}, "exit_code", "The lab chain verifies. I will request the TLS page with certificate validation enabled and retain the response."),SKILL,
   step("browser_open",{"url":"http://"+HOST+":8080","session":"review"}, "certificate|CERT|url|error", "I will observe how the browser handles the redirect. A supplied curl CA does not automatically establish browser trust.", allow_error=True),
   OPEN,
   step("browser_screenshot",{"path":"artifacts/http-login.png","session":"review"}, "image|path|screenshot", "I will retain the reachable HTTP page for comparison and report any browser trust limitation separately from TLS chain validation."),
   shell("printf 'GET /health HTTP/1.0\\r\\nHost: lab\\r\\n\\r\\n' | ncat -w 3 " + HOST + " 8000 > /opt/workspace/artifacts/ncat-health.txt; cat /opt/workspace/artifacts/ncat-health.txt", "status.*ok", "I will send a minimal raw request with Ncat and compare its response with the structured HTTP checks."),
   shell("printf 'GET /missing HTTP/1.0\\r\\nHost: lab\\r\\n\\r\\n' | ncat -w 3 " + HOST + " 8000 > /opt/workspace/artifacts/ncat-missing.txt; cat /opt/workspace/artifacts/ncat-missing.txt", "404", "The same protocol path should reject an absent route; this checks that the manual request did not merely hit a catch-all page.")]
 },
 "browser": {
  "title":"Authentication workflow", "objective": "Exercise login and verify its negative and session controls.", "prompt":"Exercise the local login with a disposable account, then verify a rejected password, session-cookie attributes, and the protected API using independent HTTP requests.",
  "summary":"Browser success is cross-checked against a rejected password, an unauthenticated profile request, and the actual Set-Cookie attributes.",
  "steps":[SKILL,OPEN,SNAPSHOT,
   step("browser_act",{"action":"fill","target":"Email","target_type":"label","value":"reviewer@lab.test","session":"review"}, "exit_code|success", "The email control has a label in the fresh snapshot. I will fill the disposable account address."),
   step("browser_act",{"action":"fill","target":"Password","target_type":"label","value":"lab-only-password","session":"review"}, "exit_code|success", "I will fill the fixture-only password; no personal credentials are used."),
   step("browser_act",{"action":"click","target":"button","target_type":"role","name":"Sign in","session":"review"}, "exit_code|success", "Both controls are filled. I will submit the actual local form and inspect the resulting page."),
   step("browser_snapshot",{"session":"review"}, "Dashboard", "The dashboard confirms successful authentication. I will retain evidence rather than infer success from the click."),
   step("network_curl",{"url":URL+"/login","method":"POST","data":"email=reviewer%40lab.test&password=wrong","extra_args":"--max-time 5 -o /opt/workspace/artifacts/login-rejected.txt"}, "exit_code", "I will independently confirm that an incorrect fixture password is rejected; the successful browser flow alone does not test this branch."),
   step("browser_screenshot",{"path":"artifacts/dashboard.png","session":"review"}, "image|path|screenshot", "I will save the verified final page. The report will distinguish tested authentication behavior from untested security properties."),
   step("network_curl",{"url":URL+"/login","method":"POST","data":"email=reviewer%40lab.test&password=lab-only-password","extra_args":"--max-time 5 -D /opt/workspace/artifacts/login-headers.txt -o /opt/workspace/artifacts/login-ok.txt"}, "exit_code", "I will verify the server's session response independently of the browser UI."),
   step("workspace_read_file",{"path":"artifacts/login-headers.txt"}, "HttpOnly.*SameSite=Lax", "I will cite the observed cookie attributes, not assume them from a successful sign-in."),
   step("network_curl",{"url":URL+"/api/profile","cookie":"atlas-session=lab-reviewer","extra_args":"--max-time 5 -o /opt/workspace/artifacts/profile-authorized.json"}, "exit_code", "The fixture session can now request the protected profile. I will save the response without extending the claim to untested accounts."),
   step("workspace_read_file",{"path":"artifacts/profile-authorized.json"}, "reviewer", "The protected response matches the scoped account. The wrong-password control remains rejected.")]
 },
 "forensics": {
  "title":"Binary and layered forensics", "objective": "Triage a binary, follow file clues, and reject a decoy.", "prompt":"Triage a supplied ELF header, then follow PCAP, image, archive and encryption clues. Reject the wrong key and decoy before accepting a checksum-verified result.",
  "summary":"Binutils establish the binary's limits; packet fragments lead to an appended archive, a failed decryption hypothesis, and a digest-checked result.",
  "steps":[shell("file /opt/workspace/challenge/module.o; readelf -h /opt/workspace/challenge/module.o; strings -a /opt/workspace/challenge/module.o", "ELF.*x86-64|ATLAS-LAB-MODULE", "I will identify the supplied binary and inspect its header and strings before inferring what it does. It has no executable program to decompile."),
   shell("file /opt/workspace/challenge/route.pcap /opt/workspace/challenge/carrier.png; sha256sum /opt/workspace/challenge/*", "pcap|PCAP|capture", "I will establish file types and hashes before modifying or extracting any challenge input."),
   shell(PCAP_INSPECT, "route_fragment", "I will inspect the real packet payloads in sequence and retain their route fragments as clues, without assuming they are the final answer."),
   step("ctf_binwalk",{"filepath":"challenge/carrier.png","extract":False}, "[Zz][Ii][Pp]", "The packets name the carrier. I will check its embedded signatures before choosing an extraction method."),
   shell("strings -a /opt/workspace/challenge/carrier.png | head -n 20", "valid image", "The carrier contains a clue about multiple endings. I will inspect the archive as a separate layer, rather than treat the image's first signature as complete."),
   shell("mkdir -p /opt/workspace/artifacts/forensics; python3 - <<'PY'\nfrom pathlib import Path\nfrom zipfile import ZipFile\np=Path('/opt/workspace/artifacts/forensics')\nwith ZipFile('/opt/workspace/challenge/carrier.png') as z:\n print(z.namelist()); z.extractall(p)\nPY", "manifest.json", "The appended ZIP is confirmed. I will extract the locally authored entries into a separate evidence directory and inspect the manifest."),
   step("workspace_read_file",{"path":"artifacts/forensics/manifest.json"}, "PBKDF2", "The manifest specifies AES-256-CBC, PBKDF2 and zlib, and says to join packet fragments with hyphens. I will test the key construction against those clues."),
   shell("openssl enc -d -aes-256-cbc -pbkdf2 -iter 10000 -in /opt/workspace/artifacts/forensics/payload.enc -out /opt/workspace/artifacts/forensics/rejected.bin -pass pass:route-without-separators", "bad decrypt|decrypt", "I will reject the tempting unseparated-route hypothesis. A failed decryption is evidence to revise the key construction.", allow_error=True, exit_code=1),
   shell("$decrypt", "exit_code", "The manifest's separators matter. I will derive the key from the observed packet sequence and decrypt the actual payload.", dynamic="decrypt"),
   shell(VERIFY_FLAG, "checksum_match.*true", "I will apply the discovered compression layer, compare the recovered flag's SHA-256 with the manifest, and reject the decoy by its mismatching digest."),
   step("workspace_read_file",{"path":"artifacts/forensics/verification.json"}, "decoy_match.*false", "The checksum and decoy checks passed. I will reread the verification artifact before publishing the reproducible write-up.")]
 },
 "web-ctf": {
  "title":"Chained web CTF", "objective": "Combine browser state and an API header, then verify the result.", "prompt":"Follow local route clues through browser state and an API header. Reject a plausible decoy and a request missing one prerequisite, then verify the actual result by digest.",
  "summary":"A route needs both session state and a header. A cookie-only request and an inconsistent decoy are rejected before the final digest passes.",
  "steps":[step("network_curl",{"url":URL+"/robots.txt","extra_args":"--max-time 5 -o /opt/workspace/artifacts/robots.txt"}, "exit_code", "I will inspect declared routes before guessing endpoints."),
   step("workspace_read_file",{"path":"artifacts/robots.txt"}, "api/draft", "The draft API is listed. I will test its unauthenticated behavior before exploring browser state."),
   step("network_curl",{"url":URL+"/api/draft","extra_args":"--max-time 5 -o /opt/workspace/artifacts/draft-denied.txt"}, "exit_code", "I will preserve the rejected request. It should tell us which prerequisite is missing."),SKILL,
   step("browser_open",{"url":URL+"/ctf/bootstrap","session":"review"}, "url|success", "The challenge offers a draft-session bootstrap. I will follow that local clue in the actual browser."),
   step("browser_snapshot",{"session":"review"}, "X-Draft-Route|atlas-7", "The page reveals a route-header requirement. I will combine it with the disposable session cookie instead of putting the value in the URL."),
   step("network_curl",{"url":URL+"/api/draft","cookie":"ctf-session=atlas-reader","extra_args":"--max-time 5 -o /opt/workspace/artifacts/draft-no-header.json"}, "exit_code", "The cookie alone may be insufficient. I will retain that negative control before sending the discovered header."),
   step("workspace_read_file",{"path":"artifacts/draft-no-header.json"}, "route header missing", "The rejection names the missing prerequisite; I will not count this branch as a solved challenge."),
   step("network_curl",{"url":URL+"/ctf/decoy","extra_args":"--max-time 5 -o /opt/workspace/artifacts/decoy.json"}, "exit_code", "A separate candidate is available. I will check its digest before accepting the first flag-like string."),
   shell("python3 - <<'PY'\nimport hashlib,json\nfrom pathlib import Path\np=Path('/opt/workspace/artifacts/decoy.json'); d=json.loads(p.read_text()[p.read_text().index('{'):]); assert hashlib.sha256(d['flag'].encode()).hexdigest()!=d['sha256']; print('decoy checksum mismatch; rejected')\nPY", "decoy checksum mismatch", "The decoy's digest does not match. I will keep it as a rejected candidate."),
   step("network_curl",{"url":URL+"/api/draft","headers":"X-Draft-Route: atlas-7","cookie":"ctf-session=atlas-reader","extra_args":"--max-time 5 -o /opt/workspace/artifacts/draft-flag.txt"}, "exit_code", "Both prerequisites are now observed. I will send the scoped request and save the actual response."),
   shell("python3 - <<'PY'\nimport hashlib,json\nfrom pathlib import Path\np=Path('/opt/workspace/artifacts/draft-flag.txt'); raw=p.read_text(); data=json.loads(raw[raw.index('{'):]); digest=hashlib.sha256(data['flag'].encode()).hexdigest(); assert digest==data['sha256']; print(json.dumps({'flag':data['flag'],'checksum_match':True,'sha256':digest})); Path('/opt/workspace/artifacts/web-ctf-verification.json').write_text(json.dumps(data,indent=2))\nPY", "checksum_match.*true", "I will verify the returned flag against its digest. The report will document the rejected request and the two required state elements.")]
 },
 "reporting": {
  "title":"Credential controls and evidence", "objective": "Validate one disposable credential and reconcile evidence.", "prompt":"Check one authorized fixture account with positive and negative controls, then reconcile the result with paged historical input and fresh service evidence.",
  "summary":"A wrong password fails and a known disposable account succeeds. The report separates those live checks from a supplied log and notes untested identities.",
  "steps":[NMAP,HTTP,
   step("workspace_read_file",{"path":"review-log.ndjson","max_bytes":2048}, "sequence", "The review log is larger than a concise inline answer. I will read its first bounded page and note that these are supplied inputs, not current scanner results."),
   step("workspace_read_file",{"path":"review-log.ndjson","offset":2048,"max_bytes":2048}, "sequence", "I will page the next bytes without silently assuming that the first chunk was the whole artifact."),
   shell("python3 - <<'PY'\nimport json\nfrom pathlib import Path\np=Path('/opt/workspace/review-log.ndjson'); records=[json.loads(s) for s in p.read_text().splitlines()]; summary={'records':len(records),'debug_records':sum(r['path']=='/debug' for r in records),'source':'authored lab input','fresh_evidence':'artifacts/health.txt'}; Path('/opt/workspace/artifacts/reconciled.json').write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2))\nPY", "records.*160", "I will reconcile every log record with a full-file computation, not extrapolate from the two inline pages."),
   step("network_curl",{"url":URL+"/debug","extra_args":"--max-time 5 -o /opt/workspace/artifacts/current-debug.txt"}, "exit_code", "I will check the debug route now. The report must distinguish current evidence from the supplied historical log."),
   step("workspace_read_file",{"path":"artifacts/reconciled.json"}, "authored lab input", "I will verify the reconciliation artifact and explicitly state what these inputs cannot establish."),
   step("network_curl",{"url":URL+"/login","method":"POST","data":"email=reviewer%40lab.test&password=incorrect","extra_args":"--max-time 5 -o /opt/workspace/artifacts/credential-rejected.txt"}, "exit_code", "A wrong fixture password is the negative control. A generic HTTP response or noisy scanner output must not be read as credential success."),
   step("workspace_read_file",{"path":"artifacts/credential-rejected.txt"}, "Credentials rejected", "I will verify the rejected response before testing the one supplied disposable account."),
   step("network_curl",{"url":URL+"/login","method":"POST","data":"email=reviewer%40lab.test&password=lab-only-password","extra_args":"--max-time 5 -D /opt/workspace/artifacts/credential-headers.txt -o /opt/workspace/artifacts/credential-accepted.txt"}, "exit_code", "I will test only the fixture credential supplied for this lab; this is not password spraying or a general credential audit."),
   step("workspace_read_file",{"path":"artifacts/credential-headers.txt"}, "303.*Set-Cookie|Set-Cookie.*atlas-session", "I will require the actual redirect and session header before marking the fixture account accepted.")]
 },
 "recovery": {
  "title":"Timeout and job recovery", "objective": "Preserve timeout output, check the job, and narrow the probe.", "prompt":"Run a bounded background probe, preserve timeout diagnostics, check the exact managed job ID, and narrow the request before concluding whether the service is available.",
  "summary":"The first request times out; a scoped health probe succeeds. The job inventory and partial output prevent a false outage claim.",
  "steps":[step("shell_exec_background",{"job_id":"lab-recovery","command":"mkdir -p /opt/workspace/artifacts; echo 'Starting scoped lab probe'; curl -sS --max-time 1 http://"+HOST+":8000/slow > /opt/workspace/artifacts/slow-partial.txt 2>&1; echo 'Slow endpoint exceeded the bounded request timeout'; sleep 1; echo 'Narrow the next check to /health'"}, "job_id", "I will start a bounded background request and retain its output. A slow service should not stall the entire investigation."),
   step("shell_check_job",{"job_id":"$job_id","tail_lines":30}, "status|running|completed", "I will inspect the job using the ID Hercules actually returned, keeping partial output visible.", dynamic="job"),
   step("system_list_sessions",{}, "job_inventory", "I will inspect Hercules's current managed-job inventory; a harness task identifier would not identify this shell job."),
   step("workspace_read_file",{"path":"artifacts/slow-partial.txt"}, "timed out|timeout", "The request exceeded its one-second budget. I will preserve that diagnostic and narrow the investigation rather than report the service as absent."),
   HTTP,
   step("workspace_read_file",{"path":"artifacts/health.txt"}, "status.*ok", "The narrow health request succeeded. This confirms a slow endpoint rather than a complete service outage."),
   step("shell_check_job",{"job_id":"$job_id","tail_lines":30}, "completed|finished|exit_code|not_found", "I will verify the background job's final state before cleanup and reporting.", dynamic="job"),
   shell("printf '%s\n' 'Recovery: slow request timed out at its explicit budget; fresh /health probe succeeded.' > /opt/workspace/artifacts/recovery.txt; cat /opt/workspace/artifacts/recovery.txt", "health probe succeeded", "I will record the revised scope and verified recovery alongside the partial output.")]
 },
 "recheck": {
  "title":"Remediation proof", "objective": "Compare before and after evidence for a local remediation.", "prompt":"Capture a vulnerable local baseline, apply the disposable fixture change, repeat identical requests, and prove that the debug route closes while the application stays healthy.",
  "summary":"Independent before/after artifacts prove the debug route closes, security headers appear, and the health endpoint remains available.",
  "steps":[step("network_curl",{"url":URL+"/debug","extra_args":"--max-time 5 -o /opt/workspace/artifacts/before.txt"}, "exit_code", "I will capture the baseline response before changing the disposable configuration."),
   step("workspace_read_file",{"path":"artifacts/before.txt"}, "debug.*true", "The baseline confirms the fixture debug endpoint. I will retain it for a direct before/after comparison."),
   step("network_curl",{"url":URL+"/lab-control/remediate","method":"POST","extra_args":"--max-time 5 -o /opt/workspace/artifacts/change.txt"}, "exit_code", "I will apply only the explicitly scoped fixture remediation. This changes no production or external service."),
   step("network_curl",{"url":URL+"/debug","extra_args":"--max-time 5 -o /opt/workspace/artifacts/after.txt"}, "exit_code", "I will repeat the same debug request after the change, keeping its response separate from the baseline."),
   step("workspace_read_file",{"path":"artifacts/after.txt"}, "404|Not found", "The endpoint now returns 404. I will verify the new headers and compare the two saved responses."),
   step("network_curl",{"url":URL+"/health","extra_args":"--max-time 5 -o /opt/workspace/artifacts/recheck-health.txt"}, "exit_code", "I will confirm that the application remains healthy after remediation."),
   shell("python3 - <<'PY'\nimport json\nfrom pathlib import Path\np=Path('/opt/workspace/artifacts'); before=(p/'before.txt').read_text(); after=(p/'after.txt').read_text(); assert '200 OK' in before and '404 Not Found' in after and 'Content-Security-Policy' in after and 'X-Content-Type-Options' in after; r={'baseline_debug':True,'debug_closed':True,'csp_present':True,'nosniff_present':True}; (p/'comparison.json').write_text(json.dumps(r,indent=2)); print(json.dumps(r,indent=2))\nPY", "debug_closed.*true", "I will require the expected before/after statuses and policy headers in the actual saved evidence before declaring remediation verified."),
   step("workspace_read_file",{"path":"artifacts/comparison.json"}, "debug_closed.*true", "The comparison artifact is present and readable. I will report the observed fix and the checks that were not performed.")]
 }
}


def catalog():
    return {key: {"title": case["title"], "objective": case["objective"], "prompt": case["prompt"], "summary": case["summary"],
                  "phases": ["Establish scope and start the runtime", "Investigate and verify the evidence", "Report and clean up the owned runtime"],
                  "operations": case["steps"]} for key, case in CASES.items()}


if __name__ == "__main__":
    print(json.dumps(catalog(), indent=2))
