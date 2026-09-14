"""Realtime streaming client for PetTracer collar updates.

The petTracer web portal (portal.pettracer.com) does not poll for position
updates - it opens a persistent connection to a separate host
(upload.pettracer.com) and receives pushed updates as they happen. That
connection is a STOMP (https://stomp.github.io) conversation carried inside
SockJS's websocket envelope framing, authenticated with the same bearer
token used for the REST endpoints in :mod:`pettracer.client`.

This module re-implements that client so the same push updates can be
consumed from Python instead of polling ``get_all_devices()`` on a timer.

Protocol summary (reverse-engineered from the portal's JS bundle):

1. Open a WebSocket to ``wss://upload.pettracer.com/sc/<server>/<session>/websocket?access_token=<token>``.
   This is the SockJS "websocket" transport - both directions wrap a single
   frame of text in a JSON array, e.g. ``["CONNECT\\n...\\x00"]``. The server
   also sends bare ``o`` (open), ``h`` (heartbeat) and ``c[<code>,<reason>]``
   (close) frames outside of that envelope.
2. Once the SockJS socket is open, send a STOMP ``CONNECT`` frame.
3. On ``CONNECTED``, subscribe to ``/user/queue/messages`` (per-device
   updates) and ``/user/queue/portal`` (session control messages: forced
   logout, subscription changes), then send a ``SEND`` frame to
   ``/app/subscribe`` with ``{"deviceIds": [...]}`` to opt in to updates for
   specific devices. ``/app/unsubscribe`` takes the same body to opt back out.
4. Each message on ``/user/queue/messages`` is a **partial** device patch
   (at minimum ``id``, usually with ``lastContact``/``lastPos``) - not a full
   ``Device``. This client merges each patch onto a local cache seeded from
   ``get_all_devices()`` and emits the merged, fully-populated ``Device``.

This was validated against a live, unauthenticated probe of
``https://upload.pettracer.com/sc/info`` (confirms the SockJS endpoint and
that the websocket transport is enabled) and against the decompiled client
logic, but not against a live authenticated session. If the frame format
has drifted, enable logging for this module to see raw frames.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import random
import string
from typing import (
    TYPE_CHECKING,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Union,
)

import aiohttp

from .types import Device

if TYPE_CHECKING:
    from .client import PetTracerClient

logger = logging.getLogger(__name__)

STREAM_BASE_URL = "https://upload.pettracer.com/sc"

UpdateCallback = Callable[[Device], Union[None, Awaitable[None]]]
PortalCallback = Callable[[dict], Union[None, Awaitable[None]]]
ConnectCallback = Callable[[], Union[None, Awaitable[None]]]
DisconnectCallback = Callable[[BaseException], Union[None, Awaitable[None]]]


class PetTracerStreamError(Exception):
    pass


async def _maybe_await(callback: Callable, *args) -> None:
    result = callback(*args)
    if inspect.isawaitable(result):
        await result


def merge_device(base: Optional[Device], patch: Device) -> Device:
    """Return a copy of ``base`` with every non-``None`` field from ``patch`` applied.

    Push updates only carry the fields that changed (typically ``id``,
    ``lastContact`` and ``lastPos``); this reconstructs a fully-populated
    ``Device`` so callers never have to deal with partial objects.
    """
    if base is None:
        return patch
    import dataclasses

    updates = {
        f.name: getattr(patch, f.name)
        for f in dataclasses.fields(patch)
        if getattr(patch, f.name) is not None
    }
    return dataclasses.replace(base, **updates)


def _sockjs_session_url(wss_base: str) -> str:
    server_id = f"{random.randint(0, 999):03d}"
    session_id = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{wss_base}/{server_id}/{session_id}/websocket"


def _build_ws_url(base_url: str, token: str) -> str:
    wss_base = base_url.replace("https://", "wss://").replace("http://", "ws://")
    return f"{_sockjs_session_url(wss_base)}?access_token={token}"


def _encode_sockjs_frame(payload: str) -> str:
    return json.dumps([payload])


def _encode_stomp_frame(command: str, headers: Dict[str, str], body: str = "") -> str:
    header_lines = "".join(f"{k}:{v}\n" for k, v in headers.items())
    return f"{command}\n{header_lines}\n{body}\x00"


def _decode_stomp_frame(text: str):
    """Parse a raw STOMP frame into ``(command, headers, body)``.

    Returns ``("", {}, "")`` for a bare STOMP heartbeat (an empty frame).
    """
    text = text.rstrip("\x00")
    if not text:
        return "", {}, ""
    lines = text.split("\n")
    command = lines[0]
    headers: Dict[str, str] = {}
    i = 1
    while i < len(lines) and lines[i]:
        key, _, value = lines[i].partition(":")
        headers[key] = value
        i += 1
    body = "\n".join(lines[i + 1 :])
    return command, headers, body


class PetTracerStream:
    """Realtime push-update stream for one or more PetTracer devices.

    Create via :meth:`pettracer.client.PetTracerClient.get_stream` after
    logging in. Register callbacks with :meth:`on_update` /
    :meth:`on_portal_message` (and optionally :meth:`on_connect` /
    :meth:`on_disconnect`), then call :meth:`start`. The stream reconnects
    automatically on failure; call :meth:`stop` to shut it down for good.

    Example:
        >>> client = PetTracerClient()
        >>> await client.login(username, password)
        >>> stream = client.get_stream()
        >>> stream.on_update(lambda device: print(device.id, device.lastPos))
        >>> await stream.start()
        ...
        >>> await stream.stop()
    """

    def __init__(
        self,
        client: "PetTracerClient",
        session: Optional[aiohttp.ClientSession] = None,
        base_url: str = STREAM_BASE_URL,
        reconnect_delay: float = 5.0,
        heartbeat_timeout: float = 30.0,
        connect_timeout: float = 10.0,
    ):
        """Initialize the stream.

        Args:
            client: An authenticated PetTracerClient.
            session: Optional aiohttp.ClientSession to use for the socket.
                If omitted, a dedicated session is created and owned by this
                stream (closed on `stop()`). Prefer a dedicated session over
                sharing a long-lived HTTP session, since `stop()`/reconnect
                need to be able to close and recreate the socket freely.
            base_url: Override for the streaming host (mainly for tests).
            reconnect_delay: Seconds to wait between reconnect attempts.
            heartbeat_timeout: Seconds of silence (no frame, no heartbeat)
                before the connection is considered dead and recycled.
            connect_timeout: Seconds to wait for the WebSocket handshake.
        """
        self._client = client
        self._session = session
        self._owns_session = session is None
        self._base_url = base_url
        self._reconnect_delay = reconnect_delay
        self._read_timeout = heartbeat_timeout
        self._connect_timeout = connect_timeout

        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._connected_event = asyncio.Event()

        self._device_ids: Set[int] = set()
        self._cache: Dict[int, Device] = {}

        self._on_update: List[UpdateCallback] = []
        self._on_portal: List[PortalCallback] = []
        self._on_connect: List[ConnectCallback] = []
        self._on_disconnect: List[DisconnectCallback] = []

    # -- callback registration -------------------------------------------------

    def on_update(self, callback: UpdateCallback) -> UpdateCallback:
        """Register a callback invoked with a merged `Device` on every push update."""
        self._on_update.append(callback)
        return callback

    def on_portal_message(self, callback: PortalCallback) -> PortalCallback:
        """Register a callback invoked with the raw dict from `/user/queue/portal`.

        Known fields (from the portal's own handling of this queue):
        - `shouldRemoveCache`: the session was invalidated server-side; the
          portal logs out. Treat this as an auth failure and re-login.
        - `shouldReload`: the portal reloads the page.
        - `shouldReloadSubscription`: subscription data changed; re-fetch
          the user profile / subscription info.
        """
        self._on_portal.append(callback)
        return callback

    def on_connect(self, callback: ConnectCallback) -> ConnectCallback:
        """Register a callback invoked each time the stream (re)connects."""
        self._on_connect.append(callback)
        return callback

    def on_disconnect(self, callback: DisconnectCallback) -> DisconnectCallback:
        """Register a callback invoked with the exception each time the stream drops."""
        self._on_disconnect.append(callback)
        return callback

    # -- lifecycle ---------------------------------------------------------

    @property
    def connected(self) -> bool:
        """Whether the STOMP connection is currently established."""
        return self._connected_event.is_set()

    @property
    def devices(self) -> List[Device]:
        """Current cached (merged) state of every subscribed device."""
        return list(self._cache.values())

    async def start(self, device_ids: Optional[Iterable[int]] = None) -> None:
        """Seed the device cache and start the background connection task.

        Args:
            device_ids: Devices to subscribe to. Defaults to every device
                on the account (via `client.get_all_devices()`).
        """
        if self._task is not None:
            raise PetTracerStreamError("Stream already started")

        all_devices = await self._client.get_all_devices()
        if device_ids is None:
            wanted = {d.id for d in all_devices}
        else:
            wanted = set(device_ids)

        self._cache = {d.id: d for d in all_devices if d.id in wanted}
        self._device_ids = wanted
        self._stop_event.clear()
        self._task = asyncio.ensure_future(self._run())

    async def stop(self) -> None:
        """Stop the stream and release the socket/session."""
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        self._ws = None
        if self._owns_session and self._session is not None:
            await self._session.close()
            self._session = None
        self._connected_event.clear()

    async def subscribe(self, device_ids: Iterable[int]) -> None:
        """Add devices to the live subscription (fetches baseline state for new ids)."""
        new_ids = [i for i in device_ids if i not in self._device_ids]
        if not new_ids:
            return
        missing = [i for i in new_ids if i not in self._cache]
        if missing:
            for d in await self._client.get_all_devices():
                if d.id in missing:
                    self._cache[d.id] = d
        self._device_ids.update(new_ids)
        if self._ws is not None and self.connected:
            await self._send_stomp(
                self._ws,
                "SEND",
                {"destination": "/app/subscribe", "content-type": "application/json"},
                json.dumps({"deviceIds": new_ids}),
            )

    async def unsubscribe(self, device_ids: Iterable[int]) -> None:
        """Remove devices from the live subscription."""
        ids = [i for i in device_ids if i in self._device_ids]
        if not ids:
            return
        self._device_ids.difference_update(ids)
        if self._ws is not None and self.connected:
            await self._send_stomp(
                self._ws,
                "SEND",
                {"destination": "/app/unsubscribe", "content-type": "application/json"},
                json.dumps({"deviceIds": ids}),
            )

    async def __aenter__(self) -> "PetTracerStream":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        await self.stop()
        return False

    # -- connection loop -----------------------------------------------------

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._connect_and_listen()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - surfaced via on_disconnect
                logger.warning("PetTracer stream disconnected: %s", exc)
                self._connected_event.clear()
                for cb in self._on_disconnect:
                    await _maybe_await(cb, exc)
            if self._stop_event.is_set():
                break
            await asyncio.sleep(self._reconnect_delay)

    async def _connect_and_listen(self) -> None:
        token = self._client.token
        if not token:
            raise PetTracerStreamError("Client is not authenticated; call client.login() first")

        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True

        url = _build_ws_url(self._base_url, token)
        async with self._session.ws_connect(url, timeout=self._connect_timeout) as ws:
            self._ws = ws
            try:
                async for frame_type, payload in self._sockjs_frames(ws):
                    if frame_type == "o":
                        await self._send_stomp(
                            ws,
                            "CONNECT",
                            {"accept-version": "1.1,1.2", "heart-beat": "10000,10000"},
                        )
                    elif frame_type == "h":
                        continue
                    elif frame_type == "c":
                        raise PetTracerStreamError(f"Socket closed by server: {payload}")
                    elif frame_type == "a":
                        for raw in payload:
                            await self._handle_stomp_frame(ws, raw)
                raise PetTracerStreamError("Socket closed")
            finally:
                self._ws = None

    async def _sockjs_frames(self, ws: aiohttp.ClientWebSocketResponse):
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=self._read_timeout)
            except asyncio.TimeoutError as exc:
                raise PetTracerStreamError("No data received within heartbeat timeout") from exc

            if msg.type == aiohttp.WSMsgType.TEXT:
                data = msg.data
                if not data:
                    continue
                kind, rest = data[0], data[1:]
                if kind == "a":
                    yield "a", json.loads(rest)
                elif kind == "o":
                    yield "o", None
                elif kind == "h":
                    yield "h", None
                elif kind == "c":
                    yield "c", json.loads(rest) if rest else None
                else:
                    logger.debug("Unknown SockJS frame: %r", data[:80])
            elif msg.type in (
                aiohttp.WSMsgType.CLOSED,
                aiohttp.WSMsgType.CLOSE,
                aiohttp.WSMsgType.ERROR,
            ):
                raise PetTracerStreamError(f"WebSocket closed: {msg.type}")

    async def _send_stomp(
        self, ws: aiohttp.ClientWebSocketResponse, command: str, headers: Dict[str, str], body: str = ""
    ) -> None:
        await ws.send_str(_encode_sockjs_frame(_encode_stomp_frame(command, headers, body)))

    async def _handle_stomp_frame(self, ws: aiohttp.ClientWebSocketResponse, raw: str) -> None:
        command, headers, body = _decode_stomp_frame(raw)
        if command == "":
            return  # STOMP-level heartbeat
        if command == "CONNECTED":
            await self._on_stomp_connected(ws)
        elif command == "MESSAGE":
            await self._on_stomp_message(headers, body)
        elif command == "ERROR":
            raise PetTracerStreamError(f"STOMP error: {headers.get('message', body)}")
        else:
            logger.debug("Unhandled STOMP frame: %s", command)

    async def _on_stomp_connected(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        await self._send_stomp(ws, "SUBSCRIBE", {"id": "sub-messages", "destination": "/user/queue/messages"})
        await self._send_stomp(ws, "SUBSCRIBE", {"id": "sub-portal", "destination": "/user/queue/portal"})
        if self._device_ids:
            await self._send_stomp(
                ws,
                "SEND",
                {"destination": "/app/subscribe", "content-type": "application/json"},
                json.dumps({"deviceIds": list(self._device_ids)}),
            )
        self._connected_event.set()
        for cb in self._on_connect:
            await _maybe_await(cb)

    async def _on_stomp_message(self, headers: Dict[str, str], body: str) -> None:
        destination = headers.get("destination", "")
        try:
            data = json.loads(body) if body else {}
        except ValueError:
            logger.warning("Non-JSON STOMP message body on %s", destination)
            return

        if destination == "/user/queue/messages":
            await self._handle_device_update(data)
        elif destination == "/user/queue/portal":
            for cb in self._on_portal:
                await _maybe_await(cb, data)
        else:
            logger.debug("Unhandled STOMP destination: %s", destination)

    async def _handle_device_update(self, data: dict) -> None:
        dev_id = data.get("id")
        if dev_id is None:
            return
        patch = Device.from_dict(data)
        merged = merge_device(self._cache.get(dev_id), patch)
        self._cache[dev_id] = merged
        for cb in self._on_update:
            await _maybe_await(cb, merged)
