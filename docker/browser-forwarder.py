#!/usr/bin/python3
"""Loopback SOCKS5 forwarder that injects the operator's upstream-proxy creds.

NOT an SSRF boundary: it performs NO destination filtering and reaches whatever
the browser asks for. Its only job is proxy authentication. Obscura (Chromium)
cannot authenticate a proxy from the command line, so the launcher points it at
an unauthenticated SOCKS5 hop here; this forwarder chains each connection to the
operator's http/https/socks5 upstream, adding that upstream's credentials.

Run as:  browser-forwarder.py serve
with the upstream URL in HERCULES_FORWARD_UPSTREAM (kept off argv so it does not
appear in the process list). It binds 127.0.0.1 on an ephemeral port and prints
that port as the first stdout line so the launcher can wire Obscura to it.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import ctypes
import ipaddress
import os
import signal
import socket
import ssl
import struct
import sys
from urllib.parse import unquote, urlsplit


def proxy_settings(value: str) -> tuple:
    p = urlsplit(value)
    if (
        p.scheme not in {"http", "https", "socks5"}
        or not p.hostname
        or p.path not in {"", "/"}
        or p.query
        or p.fragment
    ):
        raise ValueError("unsupported upstream proxy")
    port = p.port or (443 if p.scheme == "https" else 1080 if p.scheme == "socks5" else 80)
    return p.scheme, p.hostname, port, unquote(p.username or ""), unquote(p.password or "")


async def pinned_connect(host: str, port: int):
    """Connect to a literal address; never perform an implicit second lookup."""
    ip = ipaddress.ip_address(host)
    return await asyncio.wait_for(
        asyncio.open_connection(
            str(ip), port, family=socket.AF_INET6 if ip.version == 6 else socket.AF_INET
        ),
        15,
    )


def socks_address(host: str) -> bytes:
    """IPv4/IPv6 as the matching SOCKS atyp; a hostname as a domain (socks5h)."""
    try:
        value = ipaddress.ip_address(host)
    except ValueError:
        # socks5h hostnames arrive already ASCII (punycode for IDN); keep them
        # opaque. idna re-encoding would reject routable names like a_b.internal.
        name = host.encode("ascii")
        return b"\x03" + bytes([len(name)]) + name
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
    scheme, host, proxy_port, user, password = proxy
    infos = await asyncio.get_running_loop().getaddrinfo(
        host, proxy_port, type=socket.SOCK_STREAM
    )
    reader, writer = await pinned_connect(infos[0][4][0], proxy_port)
    try:
        if scheme == "https":
            await writer.start_tls(
                ssl.create_default_context(), server_hostname=host, ssl_handshake_timeout=15
            )
        if scheme in {"http", "https"}:
            authority = f"[{address}]:{port}" if ":" in address else f"{address}:{port}"
            auth = ""
            if user or password:
                token = base64.b64encode(f"{user}:{password}".encode()).decode()
                auth = f"Proxy-Authorization: Basic {token}\r\n"
            writer.write(
                f"CONNECT {authority} HTTP/1.1\r\nHost: {authority}\r\n{auth}\r\n".encode()
            )
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
        with contextlib.suppress(OSError):
            await writer.wait_closed()
        raise


async def connection(proxy: tuple, reader, writer):
    remote = None
    established = False
    try:
        async with asyncio.timeout(30):
            version, count = await reader.readexactly(2)
            methods = await reader.readexactly(count)
            if version != 5 or 0 not in methods:
                raise ValueError("unauthenticated SOCKS5 required")
            writer.write(b"\x05\x00")
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
            upstream_reader, remote = await upstream_connect(proxy, host, port)
            writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
        established = True

        async def pump(source, destination):
            # No idle timeout: a browser legitimately holds quiet WebSocket/SSE
            # tunnels open. The setup phase above is bounded by the 30s timeout.
            while data := await source.read(65536):
                destination.write(data)
                await destination.drain()
            with contextlib.suppress(OSError):
                destination.write_eof()

        tasks = [
            asyncio.create_task(pump(reader, remote)),
            asyncio.create_task(pump(upstream_reader, writer)),
        ]
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    except (OSError, ValueError, TimeoutError, asyncio.IncompleteReadError,
            IndexError, asyncio.LimitOverrunError):
        # Only before the SOCKS success reply: once the tunnel is established and
        # real bytes are flowing, a failure reply here would corrupt the stream.
        if not established:
            with contextlib.suppress(OSError):
                writer.write(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")
                await writer.drain()
    finally:
        for stream in (remote, writer):
            if stream:
                stream.close()
                with contextlib.suppress(OSError):
                    await stream.wait_closed()


async def serve(upstream: str):
    proxy = proxy_settings(upstream)
    server = await asyncio.start_server(
        lambda r, w: connection(proxy, r, w), "127.0.0.1", 0, limit=32769
    )
    print(server.sockets[0].getsockname()[1], flush=True)
    async with server:
        await server.serve_forever()


def main():
    if sys.argv[1:] != ["serve"]:
        raise SystemExit("usage: browser-forwarder.py serve (upstream in HERCULES_FORWARD_UPSTREAM)")
    # PR_SET_PDEATHSIG (1): die with the launcher PID (which becomes Obscura via
    # exec), so a forwarder never outlives the browser it serves.
    with contextlib.suppress(OSError):
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGTERM)
    asyncio.run(serve(os.environ["HERCULES_FORWARD_UPSTREAM"]))


if __name__ == "__main__":
    main()
