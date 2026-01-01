# pettracer - www.pettracer.com

Minimal Python client for the PetTracer portal.

## Installation ✅

Install runtime deps:

```bash
pip install requests
```

For development and running tests, install the dev requirements:

```bash
pip install -r requirements-dev.txt
```

## Quick usage examples ✨

### Class-based API (Recommended)

The easiest way to use the library is with the `PetTracerClient` and `PetTracerDevice` classes:

```python
from pettracer import PetTracerClient

# Create client and login
client = PetTracerClient()
client.login("username", "password")

# Get all devices
devices = client.get_all_devices()
for device in devices:
    print(f"{device.id}: {device.details.name}")

# Work with a specific device
device = client.get_device(14758)

# Get device info
info = device.get_info()
print(f"Battery: {info.bat if isinstance(info, list) else info[0].bat}")

# Get position history (timestamps in milliseconds since epoch)
positions = device.get_positions(
    filter_time=1767152926491,
    to_time=1767174526491
)
for pos in positions:
    print(f"Position at {pos.timeMeasure}: {pos.posLat}, {pos.posLong}")

# Get user profile
profile = client.get_user_profile()
print(f"User: {profile.name} ({profile.email})")
```

Auto-login on instantiation:

```python
from pettracer import PetTracerClient

# Login automatically when creating the client
client = PetTracerClient("username", "password")

# Now you can immediately use the API
devices = client.get_all_devices()
```

## Authentication

The `PetTracerClient` class handles authentication automatically:

```python
from pettracer import PetTracerClient

client = PetTracerClient()
client.login("username", "password")

# Token and session are stored internally
# All subsequent API calls use them automatically
devices = client.get_all_devices()

# Access user information from login response
print(f"Welcome, {client.user_name}!")
print(f"Devices: {client.device_count}")
print(f"Subscription expires: {client.subscription_expires}")
```


## API Reference

### Class-based API

#### PetTracerClient

User-level operations for managing authentication and accessing devices.

**Methods:**
- `__init__(username=None, password=None)` - Create client, optionally with auto-login
- `login(username, password)` - Authenticate with PetTracer API
- `get_all_devices()` - Fetch all devices for the authenticated user
- `get_device(device_id)` - Get a device-specific client
- `get_user_profile()` - Fetch user profile information (updates cached data)

**Authentication Properties:**
- `token` - Current authentication token
- `session` - Current requests session
- `is_authenticated` - Whether the client is authenticated
- `token_expires` - Token expiration date

**User Information Properties (available after login):**
- `user_id` - User ID
- `user_name` - User's full name
- `email` - User's email address
- `partner_id` - Partner ID
- `language` - User's language preference
- `country` - User's country name
- `country_id` - User's country ID
- `device_count` - Number of devices owned

**Subscription Properties (available after login):**
- `subscription_info` - Full SubscriptionInfo object
- `subscription_id` - Subscription ID
- `subscription_expires` - Subscription expiration date

**Raw Data Access:**
- `login_info` - Full LoginInfo dataclass with all login response data

#### PetTracerDevice

Device-specific operations for a single device.

**Methods:**
- `get_info()` - Fetch detailed information for this device
- `get_positions(filter_time, to_time)` - Fetch position history within a time range (milliseconds since epoch)

**Properties:**
- `device_id` - The device ID

## Security
- Tokens are secrets — store them securely (env var `PETTRACER_TOKEN` is supported).

**Security note:** Treat bearer tokens as secrets—store them in environment variables or a secure vault, and avoid committing them to source control.

## Tests

Run the test suite:

```bash
pip install -r requirements-dev.txt
pytest -q
```

Tests use `pytest` and `monkeypatch` to stub HTTP responses. See `requirements-dev.txt` for dev dependencies.

## VS Code Configuration

This workspace is pre-configured for VS Code with the following features:

### Running Examples and Scripts

The workspace includes launch configurations in [.vscode/launch.json](.vscode/launch.json) for easy debugging:

1. **Python: Current File** - Run/debug any Python file with F5
2. **Python: Class-based Example** - Run the example with prompted credentials
3. **Python: Run with .env** - Run scripts using credentials from `.env` file

#### Option 1: Using .env file (Recommended)

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```bash
   PETTRACER_USERNAME=your_username
   PETTRACER_PASSWORD=your_password
   ```

3. Open `examples/class_based_example.py` in VS Code
4. Press `F5` or select **Run > Start Debugging**
5. Choose **"Python: Run with .env"**

#### Option 2: Using Terminal

The workspace automatically sets `PYTHONPATH` in new terminals:

```bash
# Activate virtual environment
source .venv/bin/activate

# Set credentials
export PETTRACER_USERNAME="your_username"
export PETTRACER_PASSWORD="your_password"

# Run the example
python examples/class_based_example.py
```

#### Option 3: Prompted Credentials

1. Open `examples/class_based_example.py`
2. Press `F5`
3. Choose **"Python: Class-based Example"**
4. VS Code will prompt for username and password

### Testing

The workspace is configured for pytest:

- Tests are automatically discovered in the `tests/` directory
- Use the Testing sidebar (beaker icon) to run/debug tests
- Or run from terminal: `pytest -v`

### Python Interpreter

The workspace uses the local virtual environment at `.venv/`. If you need to create it:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

---

Contributions welcome — please open issues or PRs if you want improvements or additional typed return objects.
