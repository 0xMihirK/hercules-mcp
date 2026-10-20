from __future__ import annotations

import asyncio
import socket
import struct
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from hercules.core.browser_boundary import ENGINE_UID, Gateway, proxy_settings, rules
from hercules.core.docker_manager import DockerManager
from hercules.core.target_policy import TargetPolicy


def test_policy_resolves_once_and_denies_private(monkeypatch):
    lookup = Mock(return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 1234))])
    monkeypatch.setattr(socket, "getaddrinfo", lookup)
    # One DNS resolution, and loopback is refused unconditionally — there is no
    # allow-list override any more.
    with pytest.raises(ValueError, match="private"):
        TargetPolicy().resolve_destination("loop.test", 1234)
    assert lookup.call_count == 1


def test_all_dns_addresses_are_checked_against_private_deny(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.2", 80)),
    ])
    # A public first address does not excuse a private second address.
    with pytest.raises(ValueError, match="private"):
        TargetPolicy().resolve_destination("alias.test", 80)


@pytest.mark.parametrize("proxy", ["socks5h://localhost:1080", "socks4://localhost", "http://localhost/path"])
def test_unverifiable_proxy_is_not_silently_changed(proxy):
    with pytest.raises(ValueError):
        proxy_settings(proxy)


def test_rules_cover_both_families_and_only_reply_control_traffic():
    text = rules("hc_browser_123abc", 12345)
    assert "table inet" in text
    assert "ct direction reply accept" in text
    assert f"meta skuid {ENGINE_UID} reject" in text
    assert "ip daddr 127.0.0.1 tcp dport 12345 accept" in text
    assert "ip6 daddr" not in text  # No IPv6/direct-DNS exception.
    for table in ("other", "hc_browser_bad;flush ruleset"):
        with pytest.raises(ValueError):
            rules(table, 12345)


def test_socks_gateway_denies_private_and_control_ports_without_contact():
    async def scenario():
        contacts = []
        async def target(reader, writer):
            contacts.append(True)
            writer.write(b"fixture")
            await writer.drain()
            writer.close()
        server = await asyncio.start_server(target, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        gateway = Gateway({"generation": "test:1"})
        gateway.tokens["token"] = ()
        relay = await asyncio.start_server(gateway.connection, "127.0.0.1", 0)
        gateway.port = relay.sockets[0].getsockname()[1]
        async def connect(host):
            reader, writer = await asyncio.open_connection("127.0.0.1", gateway.port)
            try:
                writer.write(b"\x05\x01\x02")
                await writer.drain()
                assert await reader.readexactly(2) == b"\x05\x02"
                writer.write(b"\x01\x05token\x01x")
                await writer.drain()
                assert await reader.readexactly(2) == b"\x01\x00"
                writer.write(b"\x05\x01\x00\x03" + bytes([len(host)]) + host.encode() + struct.pack("!H", port))
                await writer.drain()
                return await reader.readexactly(10)
            finally:
                writer.close()
                await writer.wait_closed()
        try:
            # Loopback is refused by the unconditional private-IP deny, so the
            # fixture server is never contacted — with or without a protected port.
            assert (await connect("127.0.0.2"))[1] == 2
            gateway.protected.add(port)
            assert (await connect("127.0.0.1"))[1] == 2
            assert contacts == []
        finally:
            relay.close()
            server.close()
            await relay.wait_closed()
            await server.wait_closed()
    asyncio.run(scenario())


@pytest.mark.parametrize("mode,driver", [("host", "bridge"), ("container:other", "bridge"), ("lab", "macvlan")])
def test_no_firewall_command_on_unsafe_network(mode, driver):
    async def scenario():
        manager = DockerManager.__new__(DockerManager)
        manager._generation = 1
        manager.ensure_ready = AsyncMock()
        manager._container = SimpleNamespace(id="exact", reload=Mock(), attrs={
            "HostConfig": {"NetworkMode": mode}, "NetworkSettings": {"Networks": {"lab": {}}}})
        manager._client = SimpleNamespace(networks=SimpleNamespace(get=Mock(return_value=SimpleNamespace(attrs={"Driver": driver}))))
        manager.exec_command = AsyncMock()
        with pytest.raises(RuntimeError, match="bridge"):
            await manager.ensure_browser_boundary()
        manager.exec_command.assert_not_called()
    asyncio.run(scenario())
