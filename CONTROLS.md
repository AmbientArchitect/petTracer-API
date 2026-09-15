# Device Controls (Tracking Mode, Search Mode, LED, Buzzer)

**This is an unofficial API for the petTracer service. You must own a
collar and have an active subscription. Please treat the PetTracer service
with respect.**

The library was read-only until now. This documents the write endpoints
covered by this unofficial API - the same one used for
[STREAMING.md](STREAMING.md) - what they do, and what's deliberately left
out for now.

## What "tracking mode" actually is

The collar reports its position on a schedule, and how tight that schedule
is trades battery life for how current your location data is. The portal
calls this the tracking mode, and setting it is a single endpoint:

```
POST {apiEndpoint}/map/setccmode
Body: {"devType": 0, "devId": <id>, "cmdNr": <mode id>}
Response: text (not JSON)
```

The collar firmware supports many more mode ids than the portal's main
selector exposes (direction-finding "Radio" modes, several Slow/Fast
variants, an automatic low-battery fallback, a factory test mode, and an
off-until-docked state). This library exposes only the modes the main UI
surfaces as everyday choices, plus Search mode:

| `TrackingMode` | id | ~poll interval | ~GPS fix interval |
|---|---|---|---|
| `FAST` | 1 | 60s | 1h |
| `NORMAL` | 2 | 180s (3 min) | 3h |
| `SLOW` | 3 | 900s (15 min) | 24h |
| `SUPER_SLOW` | 4 | 180s | 4h |
| `SEARCH` | 11 | 21s | 21s |

The rest (ids 6, 7, 8, 9, 14, 16-19, the low-battery and off states) are
intentionally **not** in the `TrackingMode` enum yet - either their
behavior wasn't fully confirmed, or (in the case of the off state)
recovering from them requires physically placing the collar in its home
station. They can be added later; passing a raw `int` to
`set_cc_mode()`/`set_tracking_mode()` still works if you want to experiment,
it just isn't a named, supported option.

A mode change is **asynchronous**: setting it updates `Device.modeSet`
optimistically on the portal's side; the collar acknowledges on its own
schedule, at which point `Device.mode` catches up. Watch this via a
follow-up `get_info()`/`get_all_devices()` call, or - better - the
[realtime stream](STREAMING.md), which will push the confirmed `mode` as
soon as the collar checks in.

## Search mode = the real "Find nearby" control

The portal's "Find nearby" screen is a signal-strength gauge that is almost
entirely a client-side visualization: it reads fields the REST/stream API
already gives you (`lastRssi`, `fiFo`, `mode`, `lastContact`), converts RSSI
to a percentage, and buckets it into distance bands. No server call is
required to reproduce that display - see below for the formula. It also
never calls any control endpoint on its own; the countdown you see just
reflects whatever interval the collar's *current* mode already implies.

But there is a genuine, separate device-side control behind the "make my
collar report faster right now" idea: **Search mode** (`TrackingMode.SEARCH`,
id 11). Activating it is the same `setccmode` call as any other mode
change, and it's temporary/self-expiring - `Device.search` becomes `True`
once acknowledged, and `Device.searchModeDuration` counts down until it
reverts. Use `PetTracerDevice.start_search_mode()` for this rather than
`set_tracking_mode(TrackingMode.SEARCH)` directly - same call, clearer intent.

### Reproducing the signal-strength gauge

If you want an equivalent "how close is my cat" reading without polling
anything new, this is the exact formula the portal uses:

```python
def format_rssi(raw: int) -> float:
    return (raw & 255) / 2 - 130

def rssi_to_percent(rssi: float) -> int:
    import math
    pct = 1.35 * (1 - math.exp(-(rssi + 115) * 0.015))
    return round(100 * max(0, min(1, pct)))

# Distance bands, in percent:
#   >= 85           -> very close
#   58 <= x < 85    -> close
#   56 <= x < 58    -> average
#   0  <= x < 56    -> weak
#   otherwise       -> no signal
```

`Device.lastRssi` from the REST/stream API is already the raw value
`format_rssi()` expects (the portal applies `formatRSSI` when parsing the
device, same as the raw field). This isn't wired into the library as a
helper yet - it's simple enough to inline in a Home Assistant sensor, or
ask for it to be added as `pettracer.signal` if useful.

## LED and buzzer

```
POST {apiEndpoint}/map/setccled/<devId>/<0-or-1>
POST {apiEndpoint}/map/setccbuz/<devId>/<0-or-1>
```

Both take the device id and on/off state as URL path segments, no body.
`PetTracerDevice.set_led(on)` / `set_buzzer(on)` wrap these.

**Confirmed live:** not every collar generation has a physical buzzer.
Calling `set_buzzer()` against a collar without one returns success with no
physical effect - it does not raise. Treat a successful `set_buzzer()` call
as "the request was accepted," not as confirmation the collar actually made
a sound; there's no separate hardware-capability field to check in advance.

## API

```python
async with PetTracerClient() as client:
    await client.login(username, password)
    device = client.get_device(device_id)

    await device.set_tracking_mode(TrackingMode.SLOW)   # battery-friendly
    await device.start_search_mode()                     # temporary, ~21s updates
    await device.set_led(True)
    await device.set_buzzer(False)
```

Module-level functions (`set_cc_mode`, `set_cc_led`, `set_cc_buz` in
`pettracer.client`) are also available directly, following the same
pattern as `get_ccs_status`/`get_ccinfo`/`get_ccpositions`.

## Testing it from the command line

`examples/control_example.py` exercises all four actions against a real
account/device:

```bash
export PETTRACER_USERNAME="your_username"
export PETTRACER_PASSWORD="your_password"

python examples/control_example.py list
python examples/control_example.py mode <device_id> slow
python examples/control_example.py search <device_id>
python examples/control_example.py led <device_id> on
python examples/control_example.py buzzer <device_id> off
```

These calls have real-world effects (battery drain, an audible buzzer,
faster/slower location updates) - run them against a device you're
comfortable testing on, and expect `mode`/`search` in the printed state to
lag `modeSet`/the requested state until the collar acknowledges.
