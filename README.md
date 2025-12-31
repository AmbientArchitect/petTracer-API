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

Basic CCS status fetch:

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

Login + using the returned session/token (preferred):

```python
from pettracer import login, get_ccs_status

res = login("username", "password")
# res == {"token": "...", "session": <requests.Session>} 

devices = get_ccs_status(token=res['token'], session=res['session'])
```

Pretty-printing returned dataclasses:

```python
from dataclasses import asdict
import json

print(json.dumps(asdict(devices[0]), indent=2, default=str))
```

## get_ccinfo — device details (typed)

The `/api/map/getccinfo` endpoint expects a payload with `devId`.
The client accepts either an `int` or a dict containing `id`/`devId`, and will
normalize it to `{"devId": <int>}`.

```python
from pettracer import get_ccinfo

# pass device id directly
devices = get_ccinfo(14758)        # returns List[Device]

# or pass an id key
devices = get_ccinfo({"id": 14758})
```

The function returns typed `Device` objects (or a single `Device` if the server responds with a single dict).

## get_user_profile — account info

Fetch the current account profile (returns `UserProfile` dataclass):

```python
from pettracer import get_user_profile

profile = get_user_profile(token="YOUR_TOKEN")
print(profile.email, profile.name)
```

## Authentication details

- `login()` performs a JSON POST with keys `login` and `password` and returns `{"token":..., "session": <requests.Session>}`.
- Prefer passing `token` and `session` explicitly to other calls rather than passing the `login()` result as the first positional argument.
- Tokens are secrets — store them securely (env var `PETTRACER_TOKEN` is supported).

**Security note:** Treat bearer tokens as secrets—store them in environment variables or a secure vault, and avoid committing them to source control.

## Tests

Run the test suite:

```bash
pip install -r requirements-dev.txt
pytest -q
```

Tests use `pytest` and `monkeypatch` to stub HTTP responses. See `requirements-dev.txt` for dev dependencies.

## VS Code workspace

This workspace includes recommended VS Code settings to pin the interpreter to the workspace `.venv` and enable pytest in the Testing panel. See `.vscode/settings.json`.

---

Contributions welcome — please open issues or PRs if you want improvements or additional typed return objects.
