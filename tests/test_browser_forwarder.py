"""The loopback auth-forwarder must inject upstream proxy credentials.

This is the off-image self-check for the path that broke when the SSRF gateway
was deleted: Obscura (Chromium) cannot authenticate a proxy from the CLI, so the
forwarder speaks an unauthenticated SOCKS5 hop and chains to the operator's
authenticated http(s)/socks5 upstream. Runs on the host; no Docker image.
"""

import asyncio
import base64
import importlib.util
import socket
import struct
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "browser_forwarder", Path(__file__).resolve().parents[1] / "docker" / "browser-forwarder.py"
)
fwd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fwd)

CREDS = base64.b64encode(b"fixture:local-proxy").decode()


async def _echo(reader, writer):
    while data := await reader.read(4096):
        writer.write(data)
        await writer.drain()
    writer.close()


async def _connect_proxy(saw, reader, writer):
    # Minimal HTTP CONNECT proxy that REQUIRES Basic auth, then tunnels.
    request = await reader.readuntil(b"\r\n\r\n")
    saw["auth"] = f"Proxy-Authorization: Basic {CREDS}".encode() in request
    authority = request.split(b" ", 2)[1].decode()
    host, port = authority.rsplit(":", 1)
    if not saw["auth"]:
        writer.write(b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n")
        await writer.drain()
        writer.close()
        return
    up_r, up_w = await asyncio.open_connection(host, int(port))
    writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
    await writer.drain()

    async def pump(src, dst):
        # Close the peer when a direction ends so the tunnel tears down and the
        # server's wait_closed() (Python 3.13 waits for handlers) does not hang.
        try:
            while data := await src.read(4096):
                dst.write(data)
                await dst.drain()
        finally:
            dst.close()

    tasks = [asyncio.create_task(pump(reader, up_w)), asyncio.create_task(pump(up_r, writer))]
    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


async def _scenario():
    echo = await asyncio.start_server(_echo, "127.0.0.1", 0)
    echo_port = echo.sockets[0].getsockname()[1]
    saw = {"auth": False}
    proxy = await asyncio.start_server(
        lambda r, w: _connect_proxy(saw, r, w), "127.0.0.1", 0
    )
    proxy_port = proxy.sockets[0].getsockname()[1]
    upstream = f"http://fixture:local-proxy@127.0.0.1:{proxy_port}"
    settings = fwd.proxy_settings(upstream)
    forwarder = await asyncio.start_server(
        lambda r, w: fwd.connection(settings, r, w), "127.0.0.1", 0
    )
    fwd_port = forwarder.sockets[0].getsockname()[1]

    async with echo, proxy, forwarder:
        r, w = await asyncio.open_connection("127.0.0.1", fwd_port)
        # SOCKS5 no-auth greeting.
        w.write(b"\x05\x01\x00")
        await w.drain()
        assert await r.readexactly(2) == b"\x05\x00"
        # CONNECT to the echo target (IPv4).
        w.write(b"\x05\x01\x00\x01" + socket.inet_aton("127.0.0.1") + struct.pack("!H", echo_port))
        await w.drain()
        reply = await r.readexactly(10)
        assert reply[0:2] == b"\x05\x00", reply
        # Bytes must round-trip through forwarder -> authed proxy -> echo.
        w.write(b"ping-through-proxy")
        await w.drain()
        assert await r.readexactly(18) == b"ping-through-proxy"
        w.close()
    return saw["auth"]


def test_forwarder_injects_upstream_credentials():
    assert asyncio.run(_scenario()) is True


def test_proxy_settings_rejects_unsupported_scheme():
    import pytest

    for bad in ("socks5h://127.0.0.1:1080", "ftp://127.0.0.1:21", "http://127.0.0.1/path"):
        with pytest.raises(ValueError):
            fwd.proxy_settings(bad)


def test_socks_address_keeps_hostnames_ascii():
    # Punycode (IDN) and underscore hosts must pass through unchanged, not be
    # idna-re-encoded (which mangles punycode and rejects underscores).
    for host in ("xn--bcher-kva.example", "a_b.internal"):
        out = fwd.socks_address(host)
        assert out[0] == 3 and out[2:] == host.encode("ascii")


async def _auth_failure_scenario():
    # An upstream that always rejects auth must surface as a SOCKS5 failure reply
    # (connection never established), not a crash or a silent hang.
    async def deny(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(b"HTTP/1.1 407 Proxy Authentication Required\r\n\r\n")
        await writer.drain()
        writer.close()

    proxy = await asyncio.start_server(deny, "127.0.0.1", 0)
    proxy_port = proxy.sockets[0].getsockname()[1]
    settings = fwd.proxy_settings(f"http://u:p@127.0.0.1:{proxy_port}")
    forwarder = await asyncio.start_server(
        lambda r, w: fwd.connection(settings, r, w), "127.0.0.1", 0
    )
    fwd_port = forwarder.sockets[0].getsockname()[1]
    async with proxy, forwarder:
        r, w = await asyncio.open_connection("127.0.0.1", fwd_port)
        w.write(b"\x05\x01\x00")
        await w.drain()
        assert await r.readexactly(2) == b"\x05\x00"
        w.write(b"\x05\x01\x00\x01" + socket.inet_aton("127.0.0.1") + struct.pack("!H", 80))
        await w.drain()
        reply = await r.readexactly(10)
        w.close()
    return reply


def test_forwarder_reports_upstream_auth_failure():
    reply = asyncio.run(_auth_failure_scenario())
    assert reply[0] == 5 and reply[1] != 0
