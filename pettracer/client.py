"""Simple PetTracer client for fetching CCS status and other endpoints."""
from typing import Any, List, Optional
import os

import requests
import json

from .types import Device, LastPos


DEFAULT_URL = "https://portal.pettracer.com/api/map/getccs"
DEFAULT_CCINFO_URL = "https://portal.pettracer.com/api/map/getccinfo"
DEFAULT_CCPOSITIONS_URL = "https://portal.pettracer.com/api/map/getccpositions"
LOGIN_URL = "https://portal.pettracer.com/api/user/login"
USER_PROFILE_URL = "https://portal.pettracer.com/api/user/profile"


class PetTracerError(Exception):
    pass


def _request_headers(token: Optional[str]) -> dict:
    """Build request headers. Token may come from parameter or env var PETTRACER_TOKEN."""
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "User-Agent": "pettracer-python-client/0.1",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    }
    t = token or os.getenv("PETTRACER_TOKEN")
    if t:
        headers["Authorization"] = f"Bearer {t}"
    return headers


def _login_headers() -> dict:
    """Return minimal headers for the API login request.

    Use the same minimal headers as other API calls (no browser-specific headers).
    """
    headers = _request_headers(None)
    # ensure Authorization (if any) is not present for a login attempt
    headers.pop("Authorization", None)
    return headers


def get_ccs_status(url: str = DEFAULT_URL, session: Optional[requests.Session] = None, token: Optional[str] = None, timeout: int = 10) -> List[Device]:
    """Fetch the CCS status list from PetTracer and return parsed Device objects.

    Args:
        url: Full URL to call (defaults to the documented endpoint)
        session: Optional requests.Session to use
        token: Optional bearer token (or set PETTRACER_TOKEN env var)
        timeout: Request timeout in seconds

    Returns:
        List[Device]: parsed devices

    Raises:
        PetTracerError: for network or parsing issues
    """
    sess = session or requests.Session()

    # Validate URL type early and provide a clearer error message that helps
    # callers who mistakenly pass the `login()` result as the first argument.
    if not isinstance(url, str):
        raise PetTracerError(
            "Invalid 'url' parameter supplied to get_ccs_status; expected a string URL."
            " Did you pass the result of `login()` as the first argument? Use"
            " `login_res = login(...); get_ccs_status(token=login_res['token'], session=login_res['session'])`"
        )

    headers = _request_headers(token)

    try:
        resp = sess.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()
    except Exception as exc:
        raise PetTracerError(f"HTTP error while fetching CCS status: {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise PetTracerError("Invalid JSON response") from exc

    if not isinstance(data, list):
        raise PetTracerError("Unexpected JSON structure: expected a list")

    devices = []
    for item in data:
        try:
            devices.append(Device.from_dict(item))
        except Exception as exc:
            raise PetTracerError(f"Failed to parse device item: {exc}") from exc

    return devices


def get_ccinfo(payload: Any, url: str = DEFAULT_CCINFO_URL, session: Optional[requests.Session] = None, token: Optional[str] = None, timeout: int = 10) -> Any:
    """Call the `getccinfo` endpoint with the device id payload.

    The `getccinfo` endpoint expects a JSON body of the form `{"devId": <int>}`.
    This helper accepts either an integer `payload`, a dict containing `id` or
    `devId`, or a full payload dict. It normalizes the payload to `{"devId": ...}`
    and validates input to provide helpful errors.

    Args:
        payload: device id (int) or payload dict containing `devId` or `id`
        url: endpoint URL
        session: Optional requests.Session to use
        token: Optional bearer token (or set PETTRACER_TOKEN env var)
        timeout: Request timeout in seconds

    Returns:
        Parsed JSON response (dict/list)

    Raises:
        PetTracerError: for network, validation, or parsing issues
    """
    # Normalize payload
    if isinstance(payload, int):
        body = {"devId": payload}
    elif isinstance(payload, dict):
        if "devId" in payload:
            body = payload
        elif "id" in payload:
            body = {"devId": payload["id"]}
        else:
            raise PetTracerError("get_ccinfo expects payload to be an int or a dict containing 'devId' or 'id'.")
    else:
        raise PetTracerError("get_ccinfo expects payload to be an int or a dict containing 'devId' or 'id'.")

    sess = session or requests.Session()
    headers = _request_headers(token)

    try:
        resp = sess.post(url, json=body, timeout=timeout, headers=headers)
        resp.raise_for_status()
    except Exception as exc:
        raise PetTracerError(f"HTTP error while calling getccinfo: {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise PetTracerError("Invalid JSON response from getccinfo") from exc

    # Normalize and parse response into typed Device objects
    if isinstance(data, dict):
        return Device.from_dict(data)
    if isinstance(data, list):
        return [Device.from_dict(item) for item in data]

    raise PetTracerError("Unexpected JSON structure from getccinfo: expected dict or list")


def login(username: str, password: str, session: Optional[requests.Session] = None, token_env: bool = False, timeout: int = 10) -> dict:
    """Authenticate against the PetTracer site using JSON credentials.

    This helper performs a single JSON POST to `LOGIN_URL` with
    {"username":..., "password":...}. The response MUST be JSON and
    contain a token in one of the fields: `access_token`, `token`, or
    `id_token`. On success returns {"token": <token>, "session": <requests.Session>}.

    Raises `PetTracerError` for HTTP errors, non-JSON responses, or when
    no access token is present in the response.

    If `token_env` is True the discovered token is stored in the
    `PETTRACER_TOKEN` environment variable.
    """
    sess = session or requests.Session()
    # API expects JSON payload with keys `login` and `password` (not `username`).
    payload = {"login": username, "password": password}
    body = json.dumps(payload)
    headers = _login_headers()
    # ensure Content-Length matches the JSON body we are sending
    headers["Content-Length"] = str(len(body.encode("utf-8")))

    try:
        resp = sess.post(LOGIN_URL, json=payload, timeout=timeout, headers=headers)
        resp.raise_for_status()
    except Exception as exc:
        raise PetTracerError(f"HTTP error during login: {exc}") from exc

    try:
        j = resp.json()
    except ValueError:
        raise PetTracerError("Login response is not JSON; JSON login required")

    token = j.get("access_token") or j.get("token") or j.get("id_token")
    if not token:
        raise PetTracerError("Login response did not contain an access token")

    if token_env:
        os.environ["PETTRACER_TOKEN"] = token

    return {"token": token, "session": sess}


def get_ccpositions(dev_id: int, filter_time: int, to_time: int, url: str = DEFAULT_CCPOSITIONS_URL, session: Optional[requests.Session] = None, token: Optional[str] = None, timeout: int = 10) -> List[LastPos]:
    """Fetch device positions for a given time range.

    The `getccpositions` endpoint returns device positions with a time range filter.

    Args:
        dev_id: Device ID to fetch positions for
        filter_time: Start time in milliseconds (Unix timestamp * 1000)
        to_time: End time in milliseconds (Unix timestamp * 1000)
        url: endpoint URL
        session: Optional requests.Session to use
        token: Optional bearer token (or set PETTRACER_TOKEN env var)
        timeout: Request timeout in seconds

    Returns:
        List[LastPos]: list of position records

    Raises:
        PetTracerError: for network, validation, or parsing issues
    """
    body = {"devId": dev_id, "filterTime": filter_time, "toTime": to_time}
    sess = session or requests.Session()
    headers = _request_headers(token)

    try:
        resp = sess.post(url, json=body, timeout=timeout, headers=headers)
        resp.raise_for_status()
    except Exception as exc:
        raise PetTracerError(f"HTTP error while calling getccpositions: {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise PetTracerError("Invalid JSON response from getccpositions") from exc

    if not isinstance(data, list):
        raise PetTracerError("Unexpected JSON structure from getccpositions: expected a list")

    positions = []
    for item in data:
        try:
            positions.append(LastPos.from_dict(item))
        except Exception as exc:
            raise PetTracerError(f"Failed to parse position item: {exc}") from exc

    return positions


def get_user_profile(url: str = USER_PROFILE_URL, session: Optional[requests.Session] = None, token: Optional[str] = None, timeout: int = 10) -> 'UserProfile':
    """Fetch the account profile for the current token and return a typed UserProfile."""
    sess = session or requests.Session()
    headers = _request_headers(token)

    try:
        resp = sess.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()
    except Exception as exc:
        raise PetTracerError(f"HTTP error while fetching user profile: {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise PetTracerError("Invalid JSON response from user profile") from exc

    # expect a dict
    if not isinstance(data, dict):
        raise PetTracerError("Unexpected JSON structure from user profile: expected a dict")

    from .types import UserProfile
    return UserProfile.from_dict(data)
