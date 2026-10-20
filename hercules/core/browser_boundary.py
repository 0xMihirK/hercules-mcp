#!/usr/bin/python3
"""Container-only browser confinement; no host dependencies or TLS interception.

The controller remains trusted root. Only the engine runs as ENGINE_UID. Root
shell access can deliberately dismantle this boundary; web content cannot.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import ipaddress
import json
import os
import secrets
import socket
import ssl
import struct
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

try:
    from .target_policy import TargetPolicy
except ImportError:  # Executed from the image's deliberately tiny stdlib bundle.
    from target_policy import TargetPolicy

ENGINE_UID = 19731
STATE = Path("/run/hercules-browser")
CONTROL = STATE / "control.sock"
STATE_FILE = STATE / "state.json"
ENGINE = "/opt/hercules/browser/obscura"


def rules(table: str, port: int) -> str:
    """One atomic inet transaction covers IPv4, IPv6 and all protocols."""
    if not table.startswith("hc_browser_") or not table[11:].isalnum():
        raise ValueError("invalid owned firewall table")
    if not 1 <= port <= 65535:
        raise ValueError("invalid gateway port")
    return f"""table inet {table} {{
 chain output {{
  type filter hook output priority -150; policy accept;
  meta skuid {ENGINE_UID} ct state established ct direction reply accept
  meta skuid {ENGINE_UID} ip daddr 127.0.0.1 tcp dport {port} accept
  meta skuid {ENGINE_UID} reject
 }}
}}
"""


def nft(*args: str, input_text: str | None = None) -> str:
    return subprocess.run(["nft", *args], input=input_text, text=True,
                          capture_output=True, check=True, timeout=10).stdout


async def frame(reader: asyncio.StreamReader) -> dict:
    data = await asyncio.wait_for(reader.readline(), 10)
    if not data or len(data) > 32768:
        raise ValueError("invalid control frame")
    return json.loads(data)


async def control_request(request: dict) -> dict:
    reader, writer = await asyncio.open_unix_connection(str(CONTROL), limit=32769)
    try:
        writer.write(json.dumps(request).encode() + b"\n")
        await writer.drain()
        result = await frame(reader)
        if result.get("error"):
            raise ValueError(result["error"])
        return result
    finally:
        writer.close()
        await writer.wait_closed()


def proxy_settings(value: str) -> tuple:
    if not value:
        return ()
    p = urlsplit(value)
    if p.scheme not in {"http", "https", "socks5"} or not p.hostname or p.path not in {"", "/"} or p.query or p.fragment:
        raise ValueError("Only HTTP(S) CONNECT and locally resolved SOCKS5 upstream proxies are supported; remote DNS cannot be verified")
    port = p.port or (443 if p.scheme == "https" else 1080 if p.scheme == "socks5" else 80)
    return p.scheme, p.hostname, port, unquote(p.username or ""), unquote(p.password or "")


async def pinned_connect(host: str, port: int):
    """Connect to a literal address, never perform an implicit second lookup."""
    ip = ipaddress.ip_address(host)
    return await asyncio.wait_for(asyncio.open_connection(str(ip), port,
                family=socket.AF_INET6 if ip.version == 6 else socket.AF_INET), 15)


def socks_address(ip: str) -> bytes:
    value = ipaddress.ip_address(ip)
    return bytes([1 if value.version == 4 else 4]) + value.packed


async def socks_reply(reader):
    version, status, reserved, kind = await reader.readexactly(4)
    if version != 5 or status or reserved:
        raise ValueError("upstream SOCKS connection rejected")
    count = {1: 4, 4: 16}.get(kind)
    if kind == 3:
        count = (await reader.readexactly(1))[0]
    if count is None:
        raise ValueError("invalid upstream SOCKS reply")
    await reader.readexactly(count + 2)


async def upstream_connect(proxy: tuple, address: str, port: int):
    if not proxy:
        return await pinned_connect(address, port)
    scheme, host, proxy_port, user, password = proxy
    # The explicitly selected proxy is an operator endpoint, not a target. Pin
    # its address as well; destination authorization is done independently.
    infos = await asyncio.get_running_loop().getaddrinfo(host, proxy_port, type=socket.SOCK_STREAM)
    reader, writer = await pinned_connect(infos[0][4][0], proxy_port)
    try:
        if scheme == "https":
            await writer.start_tls(ssl.create_default_context(), server_hostname=host, ssl_handshake_timeout=15)
        if scheme in {"http", "https"}:
            authority = f"[{address}]:{port}" if ":" in address else f"{address}:{port}"
            auth = ""
            if user or password:
                token = base64.b64encode(f"{user}:{password}".encode()).decode()
                auth = f"Proxy-Authorization: Basic {token}\r\n"
            writer.write(f"CONNECT {authority} HTTP/1.1\r\nHost: {authority}\r\n{auth}\r\n".encode())
            await writer.drain()
            headers = await reader.readuntil(b"\r\n\r\n")
            if len(headers) > 16384 or headers.split(b"\r\n", 1)[0].split()[1] != b"200":
                raise ValueError("upstream proxy did not establish a CONNECT tunnel")
        else:
            writer.write(b"\x05\x01" + (b"\x02" if user or password else b"\x00"))
            await writer.drain()
            if await reader.readexactly(2) != (b"\x05\x02" if user or password else b"\x05\x00"):
                raise ValueError("upstream proxy authentication unavailable")
            if user or password:
                u, p = user.encode(), password.encode()
                if len(u) > 255 or len(p) > 255:
                    raise ValueError("proxy credentials too long")
                writer.write(b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p)
                await writer.drain()
                if await reader.readexactly(2) != b"\x01\x00":
                    raise ValueError("upstream proxy authentication rejected")
            writer.write(b"\x05\x01\x00" + socks_address(address) + struct.pack("!H", port))
            await writer.drain()
            await socks_reply(reader)
        return reader, writer
    except BaseException:
        writer.close()
        await writer.wait_closed()
        raise


class Gateway:
    def __init__(self, config: dict):
        self.config = config
        self.policy = TargetPolicy(config["allowed"], config["blocked"])
        self.tokens: dict[str, tuple] = {}
        self.protected: set[int] = set()
        self.port = 0
        self.table = "hc_browser_" + hashlib.sha256(config["generation"].encode()).hexdigest()[:16]
        self.slots = asyncio.Semaphore(128)
        self.rule_identity = None
        self.destinations: dict[asyncio.Task, int] = {}

    async def protect(self, port: int):
        if not 1 <= port <= 65535 or port == self.port:
            raise ValueError("invalid browser control port")
        self.protected.add(port)
        # Settle connections authorized before a new control endpoint existed.
        tasks = [task for task, destination in self.destinations.items() if destination == port]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def firewall_identity(document: dict) -> list:
        # Handles and nft version metadata are not policy. Everything else is.
        return [{kind: {k: v for k, v in value.items() if k != "handle"}}
                for entry in document["nftables"] for kind, value in entry.items()
                if kind in {"table", "chain", "rule"}]

    async def control(self, reader, writer):
        try:
            request = await frame(reader)
            if request.get("generation") != self.config["generation"]:
                raise ValueError("stale browser generation")
            # Verify the exact rules, not merely the existence of a table.
            observed = json.loads(await asyncio.to_thread(nft, "-j", "list", "table", "inet", self.table))
            if self.firewall_identity(observed) != self.rule_identity:
                raise ValueError("browser firewall unavailable")
            if request["op"] == "register":
                if request.get("allowed") != self.config["allowed"] or request.get("blocked") != self.config["blocked"]:
                    raise ValueError("browser policy changed; stop/start the runtime")
                proxy = proxy_settings(request.get("proxy", ""))
                for port in request.get("protected_ports", []):
                    await self.protect(int(port))
                token = next((k for k, v in self.tokens.items() if v == proxy), None) or secrets.token_hex(24)
                self.tokens[token] = proxy
                result = {"proxy": f"socks5h://{token}:x@127.0.0.1:{self.port}", "generation": self.config["generation"], "scope_enforced": True}
            elif request["op"] == "protect":
                port = int(request["port"])
                await self.protect(port)
                result = {"protected": True}
            else:
                raise ValueError("unsupported boundary operation")
        except Exception:
            # Never log request URLs, proxy credentials or target values.
            result = {"error": "browser boundary unavailable or configuration rejected"}
        writer.write(json.dumps(result).encode() + b"\n")
        with contextlib.suppress(ConnectionError):
            await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def connection(self, reader, writer):
        remote = None
        try:
            async with self.slots:
                async with asyncio.timeout(20):
                    version, count = await reader.readexactly(2)
                    methods = await reader.readexactly(count)
                    if version != 5 or 2 not in methods:
                        raise ValueError("SOCKS authentication required")
                    writer.write(b"\x05\x02")
                    await writer.drain()
                    version, count = await reader.readexactly(2)
                    token = (await reader.readexactly(count)).decode("ascii")
                    length = (await reader.readexactly(1))[0]
                    password = await reader.readexactly(length)
                    if version != 1 or token not in self.tokens or password != b"x":
                        raise ValueError("invalid browser gateway token")
                    writer.write(b"\x01\x00")
                    await writer.drain()
                    version, command, reserved, kind = await reader.readexactly(4)
                    if version != 5 or command != 1 or reserved:
                        raise ValueError("only TCP CONNECT supported")
                    if kind == 3:
                        length = (await reader.readexactly(1))[0]
                        host = (await reader.readexactly(length)).decode("ascii")
                    elif kind in {1, 4}:
                        host = str(ipaddress.ip_address(await reader.readexactly(4 if kind == 1 else 16)))
                    else:
                        raise ValueError("invalid SOCKS address")
                    port = struct.unpack("!H", await reader.readexactly(2))[0]
                    addresses = await asyncio.to_thread(self.policy.resolve_destination, host, port)
                    self.destinations[asyncio.current_task()] = port
                    # Deny control ports on every address, including Docker's
                    # bridge address and host aliases, not just 127.0.0.1.
                    if port == self.port or port in self.protected:
                        raise ValueError("protected browser control endpoint")
                    upstream_reader, remote = await upstream_connect(self.tokens[token], addresses[0], port)
                    writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
                    await writer.drain()
                async def pump(source, destination):
                    while data := await asyncio.wait_for(source.read(65536), 120):
                        destination.write(data)
                        await destination.drain()
                    with contextlib.suppress(OSError):
                        destination.write_eof()
                tasks = [asyncio.create_task(pump(reader, remote)), asyncio.create_task(pump(upstream_reader, writer))]
                try:
                    await asyncio.gather(*tasks)
                finally:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
        except (OSError, ValueError, TimeoutError, asyncio.IncompleteReadError):
            with contextlib.suppress(OSError):
                writer.write(b"\x05\x02\x00\x01\x00\x00\x00\x00\x00\x00")
                await writer.drain()
        finally:
            self.destinations.pop(asyncio.current_task(), None)
            for stream in (remote, writer):
                if stream:
                    stream.close()
                    with contextlib.suppress(OSError):
                        await stream.wait_closed()

    async def run(self):
        server = await asyncio.start_server(self.connection, "127.0.0.1", 0, limit=32769)
        self.port = server.sockets[0].getsockname()[1]
        # Fail before exposing the root control socket; no engine can start yet.
        transaction = rules(self.table, self.port)
        old_table = self.config.get("previous_table")
        if old_table and old_table != self.table:
            try:
                await asyncio.to_thread(nft, "list", "table", "inet", old_table)
            except subprocess.CalledProcessError:
                pass
            else:
                transaction += f"delete table inet {old_table}\n"
        await asyncio.to_thread(nft, "-f", "-", input_text=transaction)
        self.rule_identity = self.firewall_identity(json.loads(await asyncio.to_thread(nft, "-j", "list", "table", "inet", self.table)))
        CONTROL.unlink(missing_ok=True)
        control = await asyncio.start_unix_server(self.control, str(CONTROL), limit=32769)
        os.chmod(CONTROL, 0o600)
        try:
            async with server, control:
                await asyncio.gather(server.serve_forever(), control.serve_forever())
        finally:
            # Leave the deny rules on failure. Only stopping/removing the exact
            # container clears them; never create a direct-connect interval.
            CONTROL.unlink(missing_ok=True)


def ensure(config: dict) -> dict:
    import fcntl

    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if STATE.is_symlink() or STATE.stat().st_uid != 0 or STATE.stat().st_mode & 0o077:
        raise ValueError("unsafe browser state directory")
    with (STATE / "lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        request = {**config, "op": "register"}
        if CONTROL.exists():
            try:
                return asyncio.run(control_request(request))
            except (ConnectionRefusedError, FileNotFoundError):
                CONTROL.unlink(missing_ok=True)
        if STATE_FILE.exists():
            # A dead gateway leaves deny rules. Do not resurrect an old engine
            # or silently reconfigure it; a container stop/start is required.
            old = json.loads(STATE_FILE.read_text())
            if old["generation"] == config["generation"]:
                raise ValueError("browser gateway failed; stop/start the container")
            config["previous_table"] = "hc_browser_" + hashlib.sha256(old["generation"].encode()).hexdigest()[:16]
        STATE_FILE.write_text(json.dumps(config))
        os.chmod(STATE_FILE, 0o600)
        subprocess.Popen([sys.executable, __file__, "serve"], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False,
                         start_new_session=True, close_fds=True)
        for _ in range(300):  # ~15s; outer exec_command timeout is 20s
            if CONTROL.exists():
                return asyncio.run(control_request(request))
            time.sleep(0.05)
        raise ValueError("browser firewall/gateway failed to initialize; retry, or stop/start the container")


def launch(args: list[str]):
    if args == ["--version"]:
        os.execv(ENGINE, [ENGINE, *args])
    if len(args) < 5 or args[:3] != ["serve", "--host", "127.0.0.1"]:
        raise ValueError("unsupported engine launch")
    port = int(args[args.index("--port") + 1])
    proxy = args[args.index("--proxy") + 1] if "--proxy" in args else ""
    config = json.loads(STATE_FILE.read_text())
    parsed = urlsplit(proxy)
    proof = asyncio.run(control_request({**config, "op": "register", "proxy": os.environ.get("HERCULES_BROWSER_UPSTREAM", "")}))
    expected = urlsplit(proof["proxy"])
    if parsed.scheme != "socks5h" or parsed.hostname != "127.0.0.1" or parsed.port != expected.port or parsed.username or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("engine must use its generation-owned gateway")
    # The controller strips URI credentials and routes them through HTTP CDP
    # auth, which cannot authenticate SOCKS. Only this trusted launcher injects
    # the internal capability token; no user/website credentials are replayed.
    args[args.index("--proxy") + 1] = proof["proxy"]
    asyncio.run(control_request({"op": "protect", "generation": config["generation"], "port": port}))
    env = dict(os.environ, OBSCURA_ALLOW_PRIVATE_NETWORK="1", OBSCURA_BLOCK_TRACKERS="0", HOME="/tmp/hercules-browser-home")
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy", "HERCULES_BROWSER_UPSTREAM"):
        env.pop(key, None)
    os.execve("/usr/bin/setpriv", ["setpriv", f"--reuid={ENGINE_UID}", f"--regid={ENGINE_UID}",
              "--clear-groups", "--bounding-set=-all", "--inh-caps=-all", "--ambient-caps=-all",
              "--no-new-privs", ENGINE, *args], env)


def main():
    if os.geteuid() != 0:
        raise ValueError("browser launcher requires trusted root controller")
    if sys.argv[1:] == ["serve"]:
        asyncio.run(Gateway(json.loads(STATE_FILE.read_text())).run())
    elif sys.argv[1:] == ["ensure"]:
        print(json.dumps(ensure(json.loads(os.environ["HERCULES_BOUNDARY_CONFIG"]))))
    else:
        launch(sys.argv[1:])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # These launch errors contain no target URLs or proxy credentials.
        reason = str(exc) if isinstance(exc, ValueError) and not isinstance(exc, json.JSONDecodeError) else type(exc).__name__
        print(f"Browser boundary unavailable ({reason}); stop/start the container or inspect runtime verification.", file=sys.stderr)
        sys.exit(1)
