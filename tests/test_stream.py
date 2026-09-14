"""Tests for the PetTracer realtime stream (SockJS/STOMP protocol handling)."""
import asyncio
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from pettracer.stream import (
    PetTracerStream,
    PetTracerStreamError,
    _decode_stomp_frame,
    _encode_sockjs_frame,
    _encode_stomp_frame,
    merge_device,
)
from pettracer.types import Device


# -- pure codec tests ---------------------------------------------------------


def test_stomp_frame_roundtrip():
    frame = _encode_stomp_frame(
        "SEND", {"destination": "/app/subscribe", "content-type": "application/json"}, '{"deviceIds": [1, 2]}'
    )
    assert frame.endswith("\x00")

    command, headers, body = _decode_stomp_frame(frame)
    assert command == "SEND"
    assert headers == {"destination": "/app/subscribe", "content-type": "application/json"}
    assert body == '{"deviceIds": [1, 2]}'


def test_stomp_frame_with_no_body():
    frame = _encode_stomp_frame("CONNECT", {"accept-version": "1.1,1.2"})
    command, headers, body = _decode_stomp_frame(frame)
    assert command == "CONNECT"
    assert headers == {"accept-version": "1.1,1.2"}
    assert body == ""


def test_stomp_heartbeat_frame_decodes_as_empty():
    command, headers, body = _decode_stomp_frame("\n")
    assert (command, headers, body) == ("", {}, "")


def test_sockjs_envelope_wraps_single_message_array():
    frame = _encode_stomp_frame("CONNECT", {})
    envelope = _encode_sockjs_frame(frame)
    assert json.loads(envelope) == [frame]


def test_merge_device_applies_only_non_none_patch_fields():
    base = Device.from_dict({"id": 5, "bat": 4000, "status": 1, "mode": 2})
    patch = Device.from_dict({"id": 5, "bat": 3990, "lastContact": "2025-12-27T21:51:40.310+0000"})

    merged = merge_device(base, patch)

    assert merged.id == 5
    assert merged.bat == 3990  # updated by patch
    assert merged.status == 1  # preserved from base
    assert merged.mode == 2  # preserved from base
    assert merged.lastContact is not None  # added by patch


def test_merge_device_with_no_base_returns_patch():
    patch = Device.from_dict({"id": 5})
    assert merge_device(None, patch) is patch


# -- fake transport helpers ----------------------------------------------------


class FakeMessage:
    def __init__(self, type_, data=None):
        self.type = type_
        self.data = data


class FakeWebSocket:
    """Minimal stand-in for aiohttp.ClientWebSocketResponse."""

    def __init__(self, frames):
        self._frames = list(frames)
        self.sent = []
        self.closed = False

    async def receive(self):
        if not self._frames:
            return FakeMessage(aiohttp.WSMsgType.CLOSED)
        return self._frames.pop(0)

    async def send_str(self, data):
        self.sent.append(data)

    async def close(self):
        self.closed = True


class FakeClient:
    """Minimal stand-in for PetTracerClient - only what PetTracerStream needs."""

    def __init__(self, token, devices):
        self.token = token
        self._devices = devices

    async def get_all_devices(self):
        return list(self._devices)


def _sockjs_open_frame():
    return FakeMessage(aiohttp.WSMsgType.TEXT, "o")


def _sockjs_message_frame(*stomp_frames):
    return FakeMessage(aiohttp.WSMsgType.TEXT, "a" + json.dumps(list(stomp_frames)))


def _decode_sent_frame(raw_envelope: str):
    (stomp_text,) = json.loads(raw_envelope)
    return _decode_stomp_frame(stomp_text)


def _patch_session(fake_ws):
    @asynccontextmanager
    async def fake_ws_connect(url, timeout=None):
        yield fake_ws

    mock_session = MagicMock()
    mock_session.ws_connect = fake_ws_connect
    mock_session.close = AsyncMock()
    return patch("aiohttp.ClientSession", return_value=mock_session)


# -- end-to-end (mocked transport) tests ---------------------------------------


@pytest.mark.asyncio
async def test_stream_connects_subscribes_and_emits_merged_update():
    device = Device.from_dict({"id": 14758, "bat": 4207, "status": 0})
    client = FakeClient(token="tok", devices=[device])

    connected_frame = _encode_stomp_frame("CONNECTED", {"version": "1.2"})
    message_frame = _encode_stomp_frame(
        "MESSAGE",
        {"destination": "/user/queue/messages", "subscription": "sub-messages"},
        json.dumps({"id": 14758, "lastContact": "2025-12-27T21:51:40.310+0000", "bat": 4100}),
    )

    fake_ws = FakeWebSocket(
        [
            _sockjs_open_frame(),
            _sockjs_message_frame(connected_frame),
            _sockjs_message_frame(message_frame),
        ]
    )

    received = asyncio.Event()
    updates = []

    with _patch_session(fake_ws):
        stream = PetTracerStream(client, reconnect_delay=0.01)

        @stream.on_update
        def _on_update(dev):
            updates.append(dev)
            received.set()

        await stream.start()
        try:
            await asyncio.wait_for(received.wait(), timeout=1)
        finally:
            await stream.stop()

    assert len(updates) == 1
    updated = updates[0]
    assert updated.id == 14758
    assert updated.bat == 4100  # patched
    assert updated.status == 0  # preserved from baseline

    # First send should be the STOMP CONNECT frame.
    connect_cmd, _, _ = _decode_sent_frame(fake_ws.sent[0])
    assert connect_cmd == "CONNECT"

    # After CONNECTED, we should subscribe to both queues and opt in the device.
    sent_commands = [_decode_sent_frame(f) for f in fake_ws.sent[1:]]
    destinations = {headers.get("destination") for _, headers, _ in sent_commands}
    assert "/user/queue/messages" in destinations
    assert "/user/queue/portal" in destinations

    subscribe_send = next(
        (headers, body) for _, headers, body in sent_commands if headers.get("destination") == "/app/subscribe"
    )
    assert json.loads(subscribe_send[1]) == {"deviceIds": [14758]}


@pytest.mark.asyncio
async def test_stream_dispatches_portal_messages():
    device = Device.from_dict({"id": 1, "bat": 1000})
    client = FakeClient(token="tok", devices=[device])

    connected_frame = _encode_stomp_frame("CONNECTED", {"version": "1.2"})
    portal_frame = _encode_stomp_frame(
        "MESSAGE",
        {"destination": "/user/queue/portal", "subscription": "sub-portal"},
        json.dumps({"shouldRemoveCache": True}),
    )

    fake_ws = FakeWebSocket(
        [
            _sockjs_open_frame(),
            _sockjs_message_frame(connected_frame),
            _sockjs_message_frame(portal_frame),
        ]
    )

    received = asyncio.Event()
    portal_messages = []

    with _patch_session(fake_ws):
        stream = PetTracerStream(client, reconnect_delay=0.01)

        @stream.on_portal_message
        def _on_portal(data):
            portal_messages.append(data)
            received.set()

        await stream.start()
        try:
            await asyncio.wait_for(received.wait(), timeout=1)
        finally:
            await stream.stop()

    assert portal_messages == [{"shouldRemoveCache": True}]


@pytest.mark.asyncio
async def test_stream_requires_authenticated_client():
    client = FakeClient(token=None, devices=[])
    fake_ws = FakeWebSocket([])

    disconnects = []
    received = asyncio.Event()

    with _patch_session(fake_ws):
        stream = PetTracerStream(client, reconnect_delay=0.01)

        @stream.on_disconnect
        def _on_disconnect(exc):
            disconnects.append(exc)
            received.set()

        await stream.start()
        try:
            await asyncio.wait_for(received.wait(), timeout=1)
        finally:
            await stream.stop()

    assert len(disconnects) == 1
    assert isinstance(disconnects[0], PetTracerStreamError)
