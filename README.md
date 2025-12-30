# pettracer

Minimal Python client for the PetTracer portal.

## Installation

This project uses `requests` as a runtime dependency. Install with pip:

```bash
pip install requests
```

For running tests you'll also need `pytest`:

```bash
pip install pytest
```

## Usage

```python
from pettracer import get_ccs_status

devices = get_ccs_status()
for d in devices:
    print(d.id, d.details.name, d.lastPos.posLat)
```

`get_ccs_status()` returns a `List[Device]` where `Device` is a dataclass with nested `MasterHs`, `LastPos`, and `Details` objects.

## Authentication

Some endpoints require a bearer token. You can provide it directly to calls as the `token` argument, or set an environment variable `PETTRACER_TOKEN` and the client will use it automatically.

Authentication helper:

```python
from pettracer import login

# JSON-based login that returns a token and session
res = login("username", "password")
print(res['token'])
```

Note: The `login()` helper performs a **JSON** login only — it posts credentials as JSON and expects a JSON response containing an access token in one of `access_token`, `token`, or `id_token`.

Example for other calls:

```python
from pettracer import get_ccs_status, get_ccinfo

# pass token directly
devices = get_ccs_status(token="YOUR_TOKEN")

# or set environment variable
# export PETTRACER_TOKEN=YOUR_TOKEN
devices = get_ccs_status()

# POST call
info = get_ccinfo({"id": 123})
```

**Security note:** Treat bearer tokens as secrets—store them in environment variables or a secure vault, and avoid committing them to source control.

## Tests

Run the test suite with:

```bash
pytest -q
```

Tests are simple and use `monkeypatch` to mock HTTP responses.
