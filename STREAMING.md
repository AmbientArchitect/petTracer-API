# Realtime Streaming

**This is an unofficial API for the petTracer service. You must own a
collar and have an active subscription. Please treat the PetTracer service
with respect.**

`pettracer.stream.PetTracerStream` gives you push updates for collar
position/status changes instead of polling `get_all_devices()` on a timer.
This document explains where it comes from, how it works, how to test it,
and how to wire it into a Home Assistant integration.

## Background: how the web portal does it

The petTracer web portal (`portal.pettracer.com/en/dashboard`) doesn't poll.
Its Angular bundle loads `stomp.min.js` and `sockjs.min.js` and, once you're
logged in, opens a persistent connection to a *second* host,
`upload.pettracer.com`, separate from the `portal.pettracer.com` REST API
this library already talks to.

That connection is:

- **Transport:** [SockJS](https://github.com/sockjs/sockjs-client)'s
  `websocket` transport - a WebSocket at
  `wss://upload.pettracer.com/sc/<server>/<session>/websocket?access_token=<token>`,
  authenticated with the same bearer token used for the REST endpoints.
  SockJS wraps every frame: the server sends bare `o` (open), `h`
  (heartbeat) and `c[<code>,<reason>]` (close) frames, and wraps actual
  payloads as a JSON array of strings, e.g. `a["<payload>"]`.
- **Protocol:** [STOMP](https://stomp.github.io) frames carried as the
  string payload inside that SockJS envelope. After the SockJS socket opens,
  the client sends a STOMP `CONNECT` frame; the server replies `CONNECTED`.
- **Subscriptions:** the client subscribes to two STOMP destinations:
  - `/user/queue/messages` - per-device push updates.
  - `/user/queue/portal` - session control messages (forced logout,
    subscription changed, etc).
  It then sends a `SEND` frame to `/app/subscribe` with a JSON body
  `{"deviceIds": [...]}` to opt in to updates for specific devices
  (`/app/unsubscribe` takes the same body to opt back out - the server
  does *not* push updates for devices you haven't subscribed to).
- **Message shape:** each message on `/user/queue/messages` is a **partial
  patch**, not a full device record - typically just `{"id": ..., "lastContact":
  ..., "lastPos": {...}}`. The portal merges this onto its cached device
  list rather than replacing it wholesale.

This was documented as part of this unofficial API, confirmed live against
`https://upload.pettracer.com/sc/info` (a real SockJS endpoint,
`{"websocket":true,...}`), and confirmed end-to-end against a live
authenticated account via `examples/stream_example.py` - connect, subscribe,
and merged push updates all work as implemented.

## How `PetTracerStream` implements it

`pettracer/stream.py` re-implements the above directly on top of `aiohttp`'s
WebSocket client (already a dependency - no new package required):

- A small SockJS envelope codec (`_encode_sockjs_frame` /
  frame-type dispatch in `_sockjs_frames`) and STOMP frame codec
  (`_encode_stomp_frame` / `_decode_stomp_frame`) - both pure functions,
  covered by `tests/test_stream.py` without needing a network connection.
- A **merge cache**: `start()` seeds a local `{device_id: Device}` cache
  from `client.get_all_devices()`, and every incoming patch is merged onto
  it with `merge_device()` (a copy of the cached `Device` with only the
  patch's non-`None` fields overwritten). Callbacks always receive a fully
  populated `Device`, never a partial one.
- **Auto-reconnect**: on any error (socket close, STOMP `ERROR` frame, or a
  heartbeat timeout - no frame at all for `heartbeat_timeout` seconds), the
  connection is torn down and retried after `reconnect_delay` seconds
  (mirrors the portal's own flat 5s retry).
- **Callbacks**, registered before `start()`:
  - `on_update(device)` - a merged `Device` for every push update.
  - `on_portal_message(dict)` - raw payload from `/user/queue/portal`
    (see docstring for known fields, notably `shouldRemoveCache` which
    means the server force-logged-out the session).
  - `on_connect()` / `on_disconnect(exc)` - connection lifecycle, useful for
    surfacing availability state.

  Callbacks may be sync or async functions.

### Usage

```python
from pettracer import PetTracerClient

async with PetTracerClient() as client:
    await client.login(username, password)

    stream = client.get_stream()

    @stream.on_update
    def handle_update(device):
        print(f"{device.id}: battery={device.bat}mV, pos={device.lastPos}")

    await stream.start()          # subscribes to every device on the account
    # await stream.start(device_ids=[14758])   # or just specific devices

    ...  # do other work; updates arrive via the callback

    await stream.stop()
```

`client.get_stream()` raises `PetTracerError` if called before `login()`.
By default the stream creates and owns a **dedicated** `aiohttp.ClientSession`
(closed on `stop()`) rather than reusing the client's REST session - see
[Session ownership](#session-ownership-important-for-home-assistant) for why.

## Testing it from the command line

`examples/stream_example.py` logs in, prints the current device list, opens
the stream, and prints every update/portal message/connection event to
stdout until you press Ctrl+C. This is the fastest way to validate the
protocol against your own account:

```bash
export PETTRACER_USERNAME="your_username"
export PETTRACER_PASSWORD="your_password"
python examples/stream_example.py

# Only specific devices:
python examples/stream_example.py 14758

# Verbose logging (every raw frame, every reconnect attempt):
python examples/stream_example.py --debug
```

### If it stops working later

The portal is free to change its push protocol without notice. If a
previously-working setup starts looping on `stream disconnected: ...`, run
`examples/stream_example.py --debug` and compare the logged raw frames
against the shapes described above - the STOMP command names, headers, or
SockJS frame markers most likely to drift are: frame-type dispatch in
`_sockjs_frames()`, the two `SUBSCRIBE` destinations, and the
`/app/subscribe` body shape in `_on_stomp_connected()` (all in
`pettracer/stream.py`).

## Home Assistant integration

Home Assistant supports push-style data sources directly:
[`DataUpdateCoordinator`](https://developers.home-assistant.io/docs/integration_fetching_data/)
doesn't require polling - set `update_interval=None` and call
`coordinator.async_set_updated_data(data)` whenever new data arrives from an
external push source. That's exactly what `PetTracerStream`'s callback
model is designed to feed.

```python
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import aiohttp

async def async_setup_entry(hass, entry):
    # Dedicated session for the long-lived stream - see below.
    stream_session = aiohttp.ClientSession()

    client = PetTracerClient(session=async_get_clientsession(hass))
    await client.login(entry.data["username"], entry.data["password"])

    coordinator = DataUpdateCoordinator(
        hass, logger, name="pettracer", update_interval=None
    )
    coordinator.data = {d.id: d for d in await client.get_all_devices()}

    stream = client.get_stream(session=stream_session)

    @stream.on_update
    def _handle_update(device):
        coordinator.data[device.id] = device
        coordinator.async_set_updated_data(coordinator.data)

    @stream.on_disconnect
    def _handle_disconnect(exc):
        coordinator.last_update_success = False
        coordinator.async_update_listeners()

    @stream.on_portal_message
    def _handle_portal(data):
        if data.get("shouldRemoveCache"):
            # Session was invalidated server-side - trigger reauth.
            raise ConfigEntryAuthFailed("PetTracer session was invalidated")

    entry.runtime_data = (client, stream, stream_session)
    await stream.start()
    entry.async_create_background_task(hass, ..., "pettracer-stream")


async def async_unload_entry(hass, entry):
    client, stream, stream_session = entry.runtime_data
    await stream.stop()
    await stream_session.close()
    await client.close()
    return True
```

Two things matter here beyond the general callback wiring:

### Event loop, not threads

`PetTracerStream` is plain `asyncio`/`aiohttp` - its read loop runs as a task
on whichever event loop `start()` was awaited from. Home Assistant runs a
single event loop for the whole instance, so as long as `start()`/`stop()`
are awaited from HA's own async context (which `async_setup_entry` /
`async_unload_entry` already are), callbacks fire correctly on HA's loop with
no extra plumbing (no `call_soon_threadsafe`, no executor jobs).

### Session ownership (important for Home Assistant)

The REST-only guidance elsewhere in this project (share HA's default
`aiohttp` session, never call `close()`) is right for short request/response
calls, but wrong for a long-lived socket: a shared session outlives any one
config entry, so a reload or reauth of *this* integration has no clean way
to tear down *just* the stream's socket without also risking other users of
that shared session.

Give the stream its own `aiohttp.ClientSession`, created in
`async_setup_entry` and explicitly closed in `async_unload_entry` (as shown
above). This is why `client.get_stream()` creates and owns its own session
by default when you don't pass one in - do the same explicitly in HA so you
control exactly when it's closed.

### Why polling isn't fully retired

Keep a slow-interval REST reconciliation pass (e.g. every 15-30 minutes)
alongside the stream, calling `get_all_devices()` and replacing
`coordinator.data` wholesale. This is belt-and-braces against a dropped
message or a `deviceIds` subscription that silently didn't take effect
server-side - the same reason the portal itself calls `getccs` on load
before ever opening the socket, rather than relying on the socket alone.
