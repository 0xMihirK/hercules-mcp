"""Opt-in local-only browser compatibility and evidence gates."""

from __future__ import annotations

import asyncio
import hashlib
import os
import shlex
import socket
import subprocess
import time
from contextlib import closing
from pathlib import Path

import pytest
from fastmcp import Client
from test_docker_acceptance import (
    _assert_ports_released,
    _remove_exact_test_containers,
    _transport,
)
from test_docker_acceptance import (
    cached_runtime as runtime_fixture,
)
from test_docker_acceptance import (
    console_windows as console_fixture,
)

import docker
from hercules.core.workspace import WorkspaceManager

pytestmark = pytest.mark.skipif(os.getenv("HERCULES_RUN_DOCKER_ACCEPTANCE") != "1", reason="Opt-in local Docker/Obscura verification")


@pytest.fixture
def cached_runtime():
    runtime_fixture.__wrapped__()


@pytest.fixture
def console_windows():
    yield from console_fixture.__wrapped__()


FIXTURE = r'''
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import ssl, threading, socket, select, socketserver, struct, base64, ipaddress
ROOT = Path('/opt/workspace/browser-check')
BODY = bytes(range(256)) * 16
def relay(left, right):
    try:
        while True:
            ready,_,_ = select.select([left,right],[],[],15)
            if not ready: break
            for source in ready:
                data=source.recv(65536)
                if not data: return
                (right if source is left else left).sendall(data)
    finally: right.close()
def destination(host, port):
    # The proxy CONNECT target is the literal fixture host.
    assert str(ipaddress.ip_address(host)) == '127.0.0.1' and port in (18080,18081)
    return socket.create_connection((host,port),timeout=5)
class ConnectProxy(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_CONNECT(self):
        assert self.headers.get('Proxy-Authorization') == 'Basic '+base64.b64encode(b'fixture:local-proxy').decode()
        host,port=self.path.rsplit(':',1)
        peer=destination(host.strip('[]'),int(port))
        self.send_response(200);self.end_headers()
        relay(self.connection,peer)
class SocksProxy(socketserver.BaseRequestHandler):
    def exact(self,count):
        result=b''
        while len(result)<count:
            data=self.request.recv(count-len(result))
            if not data: raise EOFError()
            result+=data
        return result
    def handle(self):
        version,count=self.exact(2);assert version==5 and self.exact(count)==b'\x02'
        self.request.sendall(b'\x05\x02')
        version,count=self.exact(2);user=self.exact(count);password=self.exact(self.exact(1)[0])
        assert version==1 and user==b'fixture' and password==b'local-proxy'
        self.request.sendall(b'\x01\x00')
        assert self.exact(4)==b'\x05\x01\x00\x01'
        host=str(ipaddress.ip_address(self.exact(4)));port=struct.unpack('!H',self.exact(2))[0]
        peer=destination(host,port)
        self.request.sendall(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')
        relay(self.request,peer)
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        if self.path == '/dns-positive':
            (ROOT/'dns-positive.txt').write_text('contacted')
        if self.path == '/nested-redirect':
            self.send_response(302); self.send_header('Location','/redirect'); self.end_headers(); return
        if self.headers.get('Host', '').startswith('127.0.0.2'):
            with (ROOT/'forbidden-contacts.txt').open('a') as log: log.write(self.path+'\n')
        if self.path == '/redirect':
            self.send_response(302); self.send_header('Location','http://127.0.0.2:18080/forbidden'); self.end_headers(); return
        if self.path == '/rate':
            self.send_response(429); self.send_header('Retry-After','1'); self.end_headers(); return
        if self.path == '/private' and self.headers.get('Authorization') != 'Bearer local-fixture':
            self.send_response(401); self.end_headers(); return
        if self.path == '/download':
            if self.headers.get('Authorization') != 'Bearer local-fixture':
                self.send_response(401); self.end_headers(); return
            data = BODY
            content_type = 'application/octet-stream'
        elif self.path in ('/', '/private', '/frame'):
            data = b"""<!doctype html><title>Hercules Obscura fixture</title>
<input aria-label="Name" id="name"><button onclick="document.querySelector('#result').textContent=document.querySelector('#name').value">Apply</button>
<p id="result">ready</p><script>window.cspProbe='executed'</script>"""
            content_type = 'text/html'
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'none'")
        self.end_headers(); self.wfile.write(data)
class DeniedServer(ThreadingHTTPServer):
    def get_request(self):
        accepted = super().get_request()
        filename = 'control-contacts.txt' if self.server_address[1] == 18086 else 'forbidden-contacts.txt'
        with (ROOT/filename).open('a') as log: log.write('TCP contact\n')
        return accepted
class DeniedIPv6(DeniedServer):
    address_family = socket.AF_INET6
http = ThreadingHTTPServer(('127.0.0.1',18080),Handler)
denied = DeniedServer(('127.0.0.2',18080),Handler)
threading.Thread(target=denied.serve_forever,daemon=True).start()
denied6 = DeniedIPv6(('::1',18082),Handler)
threading.Thread(target=denied6.serve_forever,daemon=True).start()
controls = DeniedServer(('127.0.0.1',18086),Handler)
threading.Thread(target=controls.serve_forever,daemon=True).start()
tls = ThreadingHTTPServer(('127.0.0.1',18081),Handler)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(ROOT/'cert.pem', ROOT/'key.pem')
tls.socket = context.wrap_socket(tls.socket, server_side=True)
threading.Thread(target=tls.serve_forever,daemon=True).start()
for port,handler in ((18083,ConnectProxy),(18084,SocksProxy),(18085,ConnectProxy)):
    proxy = socketserver.ThreadingTCPServer(('127.0.0.1',port),handler) if port==18084 else ThreadingHTTPServer(('127.0.0.1',port),handler)
    if port==18085: proxy.socket=context.wrap_socket(proxy.socket,server_side=True)
    threading.Thread(target=proxy.serve_forever,daemon=True).start()
http.serve_forever()
'''


def _local_contracts(tmp_path: Path, record_property, *, browser_checks: bool):
    sessions = set()

    async def scenario():
        transport = _transport(tmp_path)
        transport.env.update(BROWSER_STREAM_PORT="18484", BROWSER_LOCALE="", BROWSER_TIMEZONE="")
        async with Client(transport, timeout=180) as client:
            async def call(tool_name, **arguments):
                result = (await client.call_tool(tool_name, arguments)).structured_content
                assert isinstance(result, dict), (tool_name, result)
                return result

            before_start = time.monotonic()
            started = await call("system_start_container")
            assert started["status"] == "success", started
            startup_seconds = time.monotonic() - before_start
            session = started["session_id"]
            sessions.add(session)
            record_property("startup_seconds", startup_seconds)

            def memory_samples():
                with closing(docker.from_env(timeout=15)) as engine:
                    owned = engine.containers.get(f"hercules-{session}")
                    assert owned.labels.get("hercules.session_id") == session
                    assert owned.labels.get("hercules.managed") == "true"
                    samples = []
                    stable = False
                    for _ in range(30):
                        memory = owned.stats(stream=False)["memory_stats"]
                        cache = memory.get("stats", {}).get("inactive_file", 0)
                        samples.append(max(0, memory["usage"] - cache))
                        if len(samples) >= 5 and max(samples[-3:]) - min(samples[-3:]) <= max(4 * 1024**2, min(samples[-3:]) * 0.05):
                            stable = True
                            break
                        time.sleep(1)
                    return {"samples": samples, "stabilized": stable}

            await asyncio.sleep(5)
            idle = await asyncio.to_thread(memory_samples)
            record_property("idle_container_memory", idle)
            if os.name == "nt":
                measured = await asyncio.to_thread(subprocess.run, ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"Name LIKE 'vmmem%'\" | Select-Object Name,ProcessId,WorkingSetSize | ConvertTo-Json -Compress"], capture_output=True, text=True, check=False, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
                record_property("docker_wsl_host_memory_unattributed", measured.stdout.strip() if measured.returncode == 0 else "blocked")
            workspace = WorkspaceManager(tmp_path)
            workspace.atomic_write(session, "browser-check/server.py", FIXTURE.encode(), mode=0o700)
            setup = await call("shell_exec", command="openssl req -x509 -newkey rsa:2048 -nodes -keyout /opt/workspace/browser-check/key.pem -out /opt/workspace/browser-check/cert.pem -days 1 -subj /CN=127.0.0.1 -addext subjectAltName=IP:127.0.0.1", timeout=60)
            assert setup["exit_code"] == 0, setup
            await call("shell_exec_background", command="python3 /opt/workspace/browser-check/server.py", job_id="browser-contract-fixture")
            ready = await call("shell_exec", command="for i in $(seq 1 30); do curl -fsS http://127.0.0.1:18080/ >/dev/null && exit 0; sleep 1; done; exit 1", timeout=40)
            assert ready["exit_code"] == 0, ready
            try:
                if browser_checks:
                    opened = await call("browser_open", url="http://127.0.0.1:18080/", session="alpha")
                    assert opened.get("exit_code") == 0, opened
                    assert opened["browser_backend"] == "obscura" and opened["csp_enforced"] is False
                    probe = await call("browser_eval", js="window.cspProbe", session="alpha")
                    assert "executed" in str(probe), probe
                    snapshot = await call("browser_snapshot", session="alpha")
                    assert snapshot["exit_code"] == 0 and "Apply" in str(snapshot), snapshot
                    assert (await call("browser_act", action="fill", target="#name", target_type="css", value="local-check", session="alpha"))["exit_code"] == 0
                    assert (await call("browser_act", action="click", target="button", target_type="css", session="alpha"))["exit_code"] == 0
                    read = await call("browser_read", what="text", target="#result", target_type="css", session="alpha")
                    assert "local-check" in str(read), read
                    for condition, value in (("selector", "#result"), ("text", "local-check"), ("ms", "1"), ("load", "domcontentloaded")):
                        waited = await call("browser_wait", condition=condition, value=value, session="alpha")
                        assert waited["exit_code"] == 0, waited
                    skill = await call("browser_skill", name="core", full=False)
                    assert skill["exit_code"] == 0, skill
                    advanced = await call("browser_cmd", args="get title", session="alpha")
                    assert advanced["exit_code"] == 0 and "fixture" in str(advanced), advanced
                    for action in ("current", "list"):
                        assert (await call("browser_session", action=action, session="alpha"))["exit_code"] == 0
                    shot = await client.call_tool("browser_screenshot", {"session": "alpha", "full": True, "annotate": True})
                    assert any(item.type == "image" for item in shot.content), shot.structured_content
                    assert shot.structured_content["csp_enforced"] is False
                    active = await asyncio.to_thread(memory_samples)
                    record_property("active_browser_container_memory", active)
                    stream = await call("browser_session", action="stream", session="alpha")
                    assert stream.get("stream_active") is True, stream
                    with socket.create_connection(("127.0.0.1", int(stream["stream_port"])), timeout=10) as connected:
                        connected.sendall(b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n\r\n")
                        assert b"101" in connected.recv(4096).split(b"\r\n", 1)[0]
                    await call("browser_eval", js="document.cookie='identity=alpha'; localStorage.setItem('identity','alpha'); 'saved'", session="alpha")
                    assert (await call("browser_open", url="http://127.0.0.1:18080/", session="beta"))["exit_code"] == 0
                    isolated = await call("browser_eval", js="JSON.stringify({cookie:document.cookie,identity:localStorage.getItem('identity')})", session="beta")
                    assert "identity=alpha" not in str(isolated), isolated
                    untrusted = await call("browser_open", url="https://127.0.0.1:18081/", session="untrusted-tls")
                    assert untrusted.get("exit_code", -1) != 0, "Browser accepted an untrusted TLS fixture"
                    assert (await call("browser_session", action="close", session="untrusted-tls"))["exit_code"] == 0
                    trusted = await call("shell_exec", command="cp /opt/workspace/browser-check/cert.pem /usr/local/share/ca-certificates/hercules-local-fixture.crt && update-ca-certificates", timeout=60)
                    assert trusted["exit_code"] == 0, trusted
                    secured = await call("browser_open", url="https://127.0.0.1:18081/", session="trusted-tls")
                    assert secured.get("exit_code") == 0, secured
                    assert (await call("browser_session", action="close", session="trusted-tls"))["exit_code"] == 0
                    for scheme,port in (("http",18083),("socks5",18084),("https",18085)):
                        proxied = await call("browser_open", url="https://127.0.0.1:18081/", session="proxy-"+scheme,
                                             proxy=f"{scheme}://fixture:local-proxy@127.0.0.1:{port}")
                        assert proxied.get("exit_code") == 0, proxied
                        assert "local-proxy" not in str(proxied), "Proxy credentials leaked"
                        assert (await call("browser_session", action="close", session="proxy-"+scheme))["exit_code"] == 0
                    rejected_proxy = await call("browser_open", url="http://127.0.0.1:18080/", proxy="socks5h://127.0.0.1:18084")
                    assert rejected_proxy["status"] == "unsupported_option"
                    privilege_probe = r"""
import pathlib
found = []
for process in pathlib.Path('/proc').glob('[0-9]*'):
    try:
        if not (process/'cmdline').read_bytes().startswith(b'/opt/hercules/browser/obscura\0'): continue
        status = dict(line.split(':',1) for line in (process/'status').read_text().splitlines() if ':' in line)
        assert set(status['Uid'].split()) == {'19731'}
        assert set(status['Gid'].split()) == {'19731'}
        assert not status['Groups'].strip()
        assert status['NoNewPrivs'].strip() == '1'
        for field in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb'): assert int(status[field],16) == 0
        found.append(process.name)
    except FileNotFoundError: pass
assert found, 'No confined engine observed'
print('confined-engine-processes', ','.join(found))
"""
                    privilege = await call("shell_exec", command="python3 -c " + shlex.quote(privilege_probe))
                    assert privilege["exit_code"] == 0, privilege
                script = "import hashlib,pathlib,requests; p=pathlib.Path('/opt/workspace/browser-check/download.bin'); r=requests.get('https://127.0.0.1:18081/download',headers={'Authorization':'Bearer local-fixture'},verify='/opt/workspace/browser-check/cert.pem',timeout=10); r.raise_for_status(); p.write_bytes(r.content); assert r.content==bytes(range(256))*16; print(hashlib.sha256(r.content).hexdigest())"
                downloaded = await call("shell_exec", command="/opt/hercules-python/bin/python -c " + shlex.quote(script), timeout=30)
                assert downloaded["exit_code"] == 0, downloaded
                assert hashlib.sha256(bytes(range(256))*16).hexdigest() in downloaded["stdout"]
                exported = workspace.transfer(session, "browser-check/download.bin", tmp_path / "authenticated-download.bin", direction="export")
                assert exported["sha256"] == hashlib.sha256(bytes(range(256))*16).hexdigest()
                raw_client = r"""
import pathlib, socket, ssl
context = ssl.create_default_context(cafile='/opt/workspace/browser-check/cert.pem')
data = bytearray()
with socket.create_connection(('127.0.0.1',18081),timeout=5) as raw:
    with context.wrap_socket(raw,server_hostname='127.0.0.1') as client:
        client.sendall(b'GET / HTTP/1.0\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n')
        while True:
            chunk = client.recv(4096)
            if not chunk: break
            data.extend(chunk)
            assert len(data) <= 65536
pathlib.Path('/opt/workspace/browser-check/raw-tls-response.bin').write_bytes(data)
assert data.startswith(b'HTTP/1.0 200') and b'Hercules Obscura fixture' in data
print('raw-tls-ok')
"""
                workspace.atomic_write(session, "browser-check/raw-client.py", raw_client.encode(), mode=0o700)
                raw = await call("shell_exec", command="python3 /opt/workspace/browser-check/raw-client.py", timeout=15)
                assert raw["exit_code"] == 0 and "raw-tls-ok" in raw["stdout"], raw
                controls = "import requests; base='http://127.0.0.1:18080'; assert requests.get(base+'/',timeout=5).status_code==200; assert requests.get(base+'/private',timeout=5).status_code==401; assert requests.get(base+'/private',headers={'Authorization':'Bearer local-fixture'},timeout=5).status_code==200; assert requests.get(base+'/absent',timeout=5).status_code==404; r=requests.get(base+'/rate',timeout=5); assert r.status_code==429 and r.headers['Retry-After']=='1'; print('controls-ok')"
                controlled = await call("shell_exec", command="/opt/hercules-python/bin/python -c " + shlex.quote(controls), timeout=30)
                assert controlled["exit_code"] == 0 and "controls-ok" in controlled["stdout"]
                scan = await call("nmap_scan", mode="port", target="127.0.0.1", ports="18080", extra_args="-sT -Pn")
                assert scan["exit_code"] == 0, scan
                workspace.atomic_write(session, "browser-check/paths.txt", b"private\nabsent\nrate\n", mode=0o600)
                fuzz = await call("fuzz_dirs", tool="ffuf", target_url="http://127.0.0.1:18080/FUZZ", wordlist="/opt/workspace/browser-check/paths.txt", threads=1, extra_args="-rate 2 -maxtime 10 -mc all", include_raw=True)
                assert fuzz["exit_code"] == 0, fuzz
                print(f"Measured explicit startup: {startup_seconds:.3f}s (full profile; browser initially lazy)")
                killed = await call("shell_kill_job", job_id="browser-contract-fixture")
                assert killed["confirmed"] is True, killed
                assert (await call("shell_kill_job", job_id="browser-contract-fixture"))["confirmed"] is True
            finally:
                network = await call("system_network_info")
                stopped = await call("system_stop_container")
                assert stopped["cleanup"]["confirmed"] is True, stopped
                _assert_ports_released(network)
    try:
        asyncio.run(scenario())
    finally:
        _remove_exact_test_containers(sessions)



def test_obscura_local_contracts(tmp_path, cached_runtime, console_windows, record_property):
    _local_contracts(tmp_path, record_property, browser_checks=True)


def test_local_protocol_download_and_custom_tools(tmp_path, cached_runtime, console_windows, record_property):
    _local_contracts(tmp_path, record_property, browser_checks=False)
