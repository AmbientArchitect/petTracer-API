# PetTracer API Client

[![PyPI version](https://badge.fury.io/py/pettracer-client.svg)](https://badge.fury.io/py/pettracer-client)
[![Python](https://img.shields.io/pypi/pyversions/pettracer-client.svg)](https://pypi.org/project/pettracer-client/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/pypi/status/pettracer-client.svg)](https://pypi.org/project/pettracer-client/)

Async Python client library for the [PetTracer](https://www.pettracer.com) GPS pet collar portal. Provides a clean, object-oriented interface for managing devices, tracking positions, and accessing user information.

**Note:** This is an unofficial API derived from the petTracer web site. Use with caution and respect for their service. You need to own a pet collar, have an account and paid subscription for this client to be useful.

## Features

- ⚡ **Async/await support** - Non-blocking I/O (version 0.2.0)
- 🎯 **Object-oriented design** - Clean class hierarchy for intuitive API usage
- 🔐 **Automatic authentication** - Login once, use everywhere
- 📍 **Position tracking** - Fetch device locations with time-range filtering
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
- [examples/class_based_example.py](examples/class_based_example.py) - Full async usage
- [examples/home_assistant_example.py](examples/home_assistant_example.py) - Home Assistant integration pattern

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
└── types.py              # Dataclass definitions

examples/
└── class_based_example.py  # Complete usage example

tests/
└── test_client.py        # Test suite

.vscode/
├── settings.json         # VS Code configuration
└── launch.json          # Debug configurations
```

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
