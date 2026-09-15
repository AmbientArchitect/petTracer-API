# PetTracer API Client

[![PyPI version](https://badge.fury.io/py/pettracer-client.svg)](https://badge.fury.io/py/pettracer-client)
[![Python](https://img.shields.io/pypi/pyversions/pettracer-client.svg)](https://pypi.org/project/pettracer-client/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/pypi/status/pettracer-client.svg)](https://pypi.org/project/pettracer-client/)

Async Python client library for the [PetTracer](https://www.pettracer.com) GPS pet collar portal. Provides a clean, object-oriented interface for managing devices, tracking positions, and accessing user information.

**Note:** This is an unofficial API for the petTracer service. You must own a collar and have an active subscription. Please treat the PetTracer service with respect.

## Features

- ⚡ **Async/await support** - Non-blocking I/O (version 0.2.0)
- 🎯 **Object-oriented design** - Clean class hierarchy for intuitive API usage
- 🔐 **Automatic authentication** - Login once, use everywhere
- 📍 **Position tracking** - Fetch device locations with time-range filtering
- 📡 **Realtime streaming** - Push updates over the same STOMP/SockJS channel the web portal uses, instead of polling
- 🎛️ **Device control** - Change tracking mode, activate search mode, toggle LED/buzzer
- 👤 **User management** - Access profile and subscription information
- 🐾 **Device management** - Control and monitor multiple pet collars
- 📊 **Typed data models** - Full dataclass support for all responses
- ✅ **Well tested** - Comprehensive test suite included

## Installation

Install from PyPI:

```bash
pip install pettracer-client
```

Or install the required dependencies for development:

```bash
pip install aiohttp
```

For development:

```bash
pip install -r requirements-dev.txt
```

## Quick Start

```python
import asyncio
from pettracer import PetTracerClient

async def main():
    # Create client and authenticate
    async with PetTracerClient() as client:
        await client.login("your_username", "your_password")
        
        # Access user information (cached from login)
        print(f"Welcome, {client.user_name}!")
        print(f"You have {client.device_count} device(s)")
        print(f"Subscription expires: {client.subscription_expires}")
        
        # Get all devices
        devices = await client.get_all_devices()
        for device in devices:
            print(f"{device.details.name}: Battery {device.bat}mV")
        
        # Work with a specific device
        pet_device = client.get_device(devices[0].id)
        positions = await pet_device.get_positions(
            filter_time=1767152926491,  # Unix timestamp in milliseconds
            to_time=1767174526491
        )

asyncio.run(main())
```

For complete examples, see:
- [examples/class_based_example.py](examples/class_based_example.py) - Full async usage (REST only)
- [examples/stream_example.py](examples/stream_example.py) - Command-line tool for exercising the realtime stream
- [examples/control_example.py](examples/control_example.py) - Command-line tool for tracking mode / search mode / LED / buzzer

## Realtime Streaming

Instead of polling `get_all_devices()`, you can subscribe to push updates
over the same channel the web portal uses:

```python
async with PetTracerClient() as client:
    await client.login(username, password)

    stream = client.get_stream()

    @stream.on_update
    def handle_update(device):
        print(f"{device.id}: battery={device.bat}mV, pos={device.lastPos}")

    await stream.start()   # or start(device_ids=[...]) for specific devices
    ...
    await stream.stop()
```

Test it against your own account from the command line with
`python examples/stream_example.py` (add `--debug` for verbose frame
logging). See [STREAMING.md](STREAMING.md) for how the protocol works,
how the merge/reconnect/callback model is implemented, and how to wire it
into a Home Assistant `DataUpdateCoordinator`.

## Device Control

Change how often a collar reports in, trade battery life for update
frequency, temporarily boost update frequency to help you find your cat,
or toggle its LED/buzzer:

```python
from pettracer import TrackingMode

async with PetTracerClient() as client:
    await client.login(username, password)
    device = client.get_device(device_id)

    await device.set_tracking_mode(TrackingMode.SLOW)  # battery-friendly
    await device.start_search_mode()                    # temporary, ~21s updates
    await device.set_led(True)
    await device.set_buzzer(False)
```

Test it against your own account with `python examples/control_example.py`
(see `--help`). See [CONTROLS.md](CONTROLS.md) for the full mode table,
how "Find nearby" actually works (mostly a client-side signal-strength
gauge, with a real "Search mode" behind the "make it report faster" part),
and why several collar modes aren't exposed yet.

## Home Assistant Integration

The client is designed to work seamlessly with Home Assistant:

```python
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pettracer import PetTracerClient

async def async_setup_entry(hass, entry):
    # Pass in Home Assistant's aiohttp session
    session = async_get_clientsession(hass)
    client = PetTracerClient(session=session)
    
    await client.login(
        entry.data["username"],
        entry.data["password"]
    )
    
    # Use the client...
    # Note: Don't call client.close() - HA manages the session
```

For the realtime stream specifically, use a **dedicated** session instead of
HA's shared one, so it can be torn down cleanly on unload/reload - see
[STREAMING.md](STREAMING.md#session-ownership-important-for-home-assistant)
for the full pattern with `DataUpdateCoordinator`.

## Architecture

The library uses a two-tier class architecture:

### Client Hierarchy

```
PetTracerClient (user-level operations)
    ├── Authentication & session management
    ├── User profile & subscription info
    └── Device discovery
         └── PetTracerDevice (device-specific operations)
              ├── Device information
              └── Position history
```

### Key Classes

#### `PetTracerClient`

The main entry point for all API operations. Manages authentication and provides access to user-level functionality.

**Initialization:**
```python
import asyncio
from pettracer import PetTracerClient

# Option 1: Context manager (recommended)
async with PetTracerClient() as client:
    await client.login(username, password)
    # Use client...

# Option 2: Manual session management
client = PetTracerClient()
await client.login(username, password)
# ... use client ...
await client.close()  # Clean up

# Option 3: Pass in existing aiohttp session (e.g., from Home Assistant)
import aiohttp
async with aiohttp.ClientSession() as session:
    client = PetTracerClient(session=session)
    await client.login(username, password)
    # Don't call close() - you manage the session
```

**Core Methods (all async):**
- `await login(username, password)` - Authenticate and store credentials
- `await get_all_devices()` - Retrieve all devices owned by the user
- `get_device(device_id)` - Get a device-specific client (not async)
- `await get_user_profile()` - Fetch detailed user profile (updates cached data)
- `get_stream()` - Get a `PetTracerStream` for realtime push updates (not async - see [STREAMING.md](STREAMING.md))
- `await close()` - Close the session if owned by this client

**Authentication:**
- `is_authenticated` - Check if logged in
- `token` - Current bearer token
- `token_expires` - Token expiration datetime
- `session` - aiohttp ClientSession object

**User Information (available after login):**
- `user_id`, `user_name`, `email`
- `partner_id`, `language`
- `country`, `country_id`
- `device_count` - Number of devices

**Subscription:**
- `subscription_id` - Subscription identifier
- `subscription_expires` - Expiration date
- `subscription_info` - Full `SubscriptionInfo` object

**Raw Data:**
- `login_info` - Complete `LoginInfo` dataclass with all login response data

#### `PetTracerDevice`

Represents a single pet tracker device. Created via `client.get_device(device_id)`.

**Methods (all async):**
- `await get_info()` - Fetch current device information
- `await get_positions(filter_time, to_time)` - Get position history within time range
- `await set_tracking_mode(mode)` - Change tracking mode (see `TrackingMode`, [CONTROLS.md](CONTROLS.md))
- `await start_search_mode()` - Activate temporary high-frequency Search mode
- `await set_led(on)` / `await set_buzzer(on)` - Toggle LED/buzzer

**Properties:**
- `device_id` - The device identifier

**Time Parameters:**
Position history methods use Unix timestamps in milliseconds:
```python
from datetime import datetime, timedelta

now = datetime.now()
yesterday = now - timedelta(days=1)

positions = await device.get_positions(
    filter_time=int(yesterday.timestamp() * 1000),
    to_time=int(now.timestamp() * 1000)
)
```

## Data Models

All API responses are parsed into typed dataclasses for easy access and IDE autocomplete support.

### Core Types

**`Device`** - Complete device information:
- `id`, `bat` (battery), `status`, `mode`
- `details` - `Details` object with name, image, birth date
- `lastPos` - `LastPos` object with most recent position
- `masterHs` - Master home station information
- `lastContact`, `homeSince` - Timestamps
- Many more fields for device state

**`LastPos`** - Position data:
- `posLat`, `posLong` - Coordinates
- `timeMeasure`, `timeDb` - Timestamps
- `sat` - Satellite count
- `rssi` - Signal strength
- `fixS`, `fixP`, `horiPrec` - GPS quality metrics
- `acc` - Accuracy
- `flags` - Status flags

**`Details`** - Device/pet details:
- `name` - Pet name
- `birth` - Birth date
- `image`, `img` - Image references
- `color` - Color code

**`UserProfile`** - User account information:
- `id`, `email`, `name`
- `street`, `street2`, `zip`, `city`
- `mobile`, `lang`, `country_id`
- Additional profile fields

**`LoginInfo`** - Complete login response data:
- User identification and account details
- Authentication tokens and expiration
- Subscription information via `abo` field
- Settings and preferences

**`SubscriptionInfo`** - Subscription details:
- `id`, `userId`, `odooId`
- `dateExpires` - Expiration date
- `paypalSubscriptionId`
- Raw subscription dict

### Working with Data

```python
# Device information
device = devices[0]
print(f"Pet: {device.details.name}")
print(f"Battery: {device.bat}mV")
print(f"Last seen: {device.lastContact}")

if device.lastPos:
    print(f"Location: {device.lastPos.posLat}, {device.lastPos.posLong}")
    print(f"Satellites: {device.lastPos.sat}")
    print(f"Time: {device.lastPos.timeMeasure}")

# Position history
for pos in positions:
    print(f"{pos.timeMeasure}: ({pos.posLat}, {pos.posLong})")
    print(f"  Accuracy: {pos.acc}m, Satellites: {pos.sat}")

# User profile
profile = client.get_user_profile()
print(f"{profile.name} - {profile.email}")
print(f"{profile.city}, {profile.zip}")
```

## Example Application

See [examples/class_based_example.py](examples/class_based_example.py) for a complete working example that demonstrates:

- Client initialization and login
- Accessing user information and subscription details
- Fetching and displaying all devices
- Working with device-specific clients
- Retrieving position history with time ranges
- Error handling and data validation

Run the example:
```bash
export PETTRACER_USERNAME="your_username"
export PETTRACER_PASSWORD="your_password"
python examples/class_based_example.py
```

## Security

⚠️ **Important:** Authentication tokens are secrets. Always:

- Store credentials in environment variables or secure vaults
- Never commit tokens or passwords to version control
- Use `.env` files (which are gitignored) for local development
- Rotate tokens regularly

The client supports token storage via environment variable:
```python
import os
os.environ['PETTRACER_TOKEN'] = 'your_token_here'
```

## Testing

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest -v

# Run specific test file
pytest tests/test_client.py -v

# Run with coverage
pytest --cov=pettracer tests/
```

The test suite uses `pytest` with `monkeypatch` to mock HTTP responses, ensuring tests run without actual API calls.

## VS Code Setup

This workspace is pre-configured for VS Code development. See [VSCODE_GUIDE.md](VSCODE_GUIDE.md) for detailed instructions.

### Quick Start in VS Code

1. Copy `.env.example` to `.env` and add your credentials
2. Open `examples/class_based_example.py`
3. Press `F5` to run with debugging
4. Choose **"Python: Run with .env"**

The workspace includes:
- Launch configurations for debugging
- Automatic PYTHONPATH setup in terminals
- pytest test discovery and debugging
- Python interpreter configuration

## Development

### Project Structure

```
pettracer/
├── __init__.py           # Package exports
├── client.py             # PetTracerClient and PetTracerDevice classes
├── stream.py             # PetTracerStream - realtime push updates
└── types.py              # Dataclass definitions, TrackingMode enum

examples/
├── class_based_example.py  # Complete REST usage example
├── stream_example.py       # CLI tool for testing the realtime stream
└── control_example.py      # CLI tool for tracking mode / search mode / LED / buzzer

tests/
├── test_client.py        # REST client + device control test suite
└── test_stream.py        # Stream protocol/codec test suite

.vscode/
├── settings.json         # VS Code configuration
└── launch.json          # Debug configurations
```

See [STREAMING.md](STREAMING.md) for details on `stream.py`, and
[CONTROLS.md](CONTROLS.md) for the device control (write) endpoints.

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

Issues and feature requests can be submitted via GitHub Issues.

## License

See repository for license information.

---

**Note:** This is an unofficial client library. PetTracer® is a trademark of its respective owner.
