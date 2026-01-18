""" PetTracer client for interacting with a petTracer collar.
    You need to own a collar, have a valid subscription, and an account.
    www.pettracer.com provides the web interface and mobile apps.
"""
from typing import Any, List, Optional, TYPE_CHECKING
from datetime import datetime
import os

import aiohttp
import json

from .types import Device, LastPos

if TYPE_CHECKING:
    from .types import LoginInfo, SubscriptionInfo, UserProfile


GETCCS_URL = "https://portal.pettracer.com/api/map/getccs"
CCINFO_URL = "https://portal.pettracer.com/api/map/getccinfo"
CCPOSITIONS_URL = "https://portal.pettracer.com/api/map/getccpositions"
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


async def get_ccs_status(session: Optional[aiohttp.ClientSession] = None, token: str = None, timeout: int = 10) -> List[Device]:
    """Fetch the CCS status list from PetTracer and return parsed Device objects.

    Args:
        session: Optional aiohttp.ClientSession to use
        token: Optional bearer token (or set PETTRACER_TOKEN env var)
        timeout: Request timeout in seconds

    Returns:
        List[Device]: parsed devices

    Raises:
        PetTracerError: for network or parsing issues
    """
    headers = _request_headers(token)
    close_session = session is None
    sess = session or aiohttp.ClientSession()

    try:
        async with sess.get(GETCCS_URL, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
            resp.raise_for_status()
            try:
                data = await resp.json()
            except ValueError as exc:
                raise PetTracerError("Invalid JSON response") from exc
    except aiohttp.ClientError as exc:
        raise PetTracerError(f"HTTP error while fetching CCS status: {exc}") from exc
    finally:
        if close_session:
            await sess.close()

    if not isinstance(data, list):
        raise PetTracerError("Unexpected JSON structure: expected a list")

    devices = []
    for item in data:
        try:
            devices.append(Device.from_dict(item))
        except Exception as exc:
            raise PetTracerError(f"Failed to parse device item: {exc}") from exc

    return devices


async def get_ccinfo(payload: Any, session: Optional[aiohttp.ClientSession] = None, token: Optional[str] = None, timeout: int = 10) -> Any:
    """Call the `getccinfo` endpoint with the device id payload.

    The `getccinfo` endpoint expects a JSON body of the form `{"devId": <int>}`.
    This helper accepts either an integer `payload`, a dict containing `id` or
    `devId`, or a full payload dict. It normalizes the payload to `{"devId": ...}`
    and validates input to provide helpful errors.

    Args:
        payload: device id (int) or payload dict containing `devId` or `id`
        session: Optional aiohttp.ClientSession to use
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

    headers = _request_headers(token)
    close_session = session is None
    sess = session or aiohttp.ClientSession()

    try:
        async with sess.post(CCINFO_URL, json=body, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
            resp.raise_for_status()
            try:
                data = await resp.json()
            except ValueError as exc:
                raise PetTracerError("Invalid JSON response from getccinfo") from exc
    except aiohttp.ClientError as exc:
        raise PetTracerError(f"HTTP error while calling getccinfo: {exc}") from exc
    finally:
        if close_session:
            await sess.close()

    # Normalize and parse response into typed Device objects
    if isinstance(data, dict):
        return Device.from_dict(data)
    if isinstance(data, list):
        return [Device.from_dict(item) for item in data]

    raise PetTracerError("Unexpected JSON structure from getccinfo: expected dict or list")


async def login(username: str, password: str, session: Optional[aiohttp.ClientSession] = None, token_env: bool = False, timeout: int = 10) -> dict:
    """Authenticate against the PetTracer site using JSON credentials.

    This helper performs a single JSON POST to `LOGIN_URL` with
    {"username":..., "password":...}. The response MUST be JSON and
    contain a token in one of the fields: `access_token`, `token`, or
    `id_token`. On success returns {"token": <token>, "session": <aiohttp.ClientSession>}.

    Raises `PetTracerError` for HTTP errors, non-JSON responses, or when
    no access token is present in the response.

    If `token_env` is True the discovered token is stored in the
    `PETTRACER_TOKEN` environment variable.
    """
    close_session = session is None
    sess = session or aiohttp.ClientSession()
    # API expects JSON payload with keys `login` and `password` (not `username`).
    payload = {"login": username, "password": password}
    body = json.dumps(payload)
    headers = _login_headers()
    # ensure Content-Length matches the JSON body we are sending
    headers["Content-Length"] = str(len(body.encode("utf-8")))

    try:
        async with sess.post(LOGIN_URL, json=payload, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
            resp.raise_for_status()
            try:
                j = await resp.json()
            except ValueError:
                raise PetTracerError("Login response is not JSON; JSON login required")
    except aiohttp.ClientError as exc:
        raise PetTracerError(f"HTTP error during login: {exc}") from exc
    finally:
        if close_session:
            await sess.close()

    token = j.get("access_token") or j.get("token") or j.get("id_token")
    if not token:
        raise PetTracerError("Login response did not contain an access token")

    if token_env:
        os.environ["PETTRACER_TOKEN"] = token

    return {"token": token, "session": sess, "data": j}


async def get_ccpositions(dev_id: int, filter_time: int, to_time: int, session: Optional[aiohttp.ClientSession] = None, token: Optional[str] = None, timeout: int = 10) -> List[LastPos]:
    """Fetch device positions for a given time range.

    The `getccpositions` endpoint returns device positions with a time range filter.

    Args:
        dev_id: Device ID to fetch positions for
        filter_time: Start time in milliseconds (Unix timestamp * 1000)
        to_time: End time in milliseconds (Unix timestamp * 1000)
        session: Optional aiohttp.ClientSession to use
        token: Optional bearer token (or set PETTRACER_TOKEN env var)
        timeout: Request timeout in seconds

    Returns:
        List[LastPos]: list of position records

    Raises:
        PetTracerError: for network, validation, or parsing issues
    """
    body = {"devId": dev_id, "filterTime": filter_time, "toTime": to_time}
    headers = _request_headers(token)
    close_session = session is None
    sess = session or aiohttp.ClientSession()

    try:
        async with sess.post(CCPOSITIONS_URL, json=body, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
            resp.raise_for_status()
            try:
                data = await resp.json()
            except ValueError as exc:
                raise PetTracerError("Invalid JSON response from getccpositions") from exc
    except aiohttp.ClientError as exc:
        raise PetTracerError(f"HTTP error while calling getccpositions: {exc}") from exc
    finally:
        if close_session:
            await sess.close()

    if not isinstance(data, list):
        raise PetTracerError("Unexpected JSON structure from getccpositions: expected a list")

    positions = []
    for item in data:
        try:
            positions.append(LastPos.from_dict(item))
        except Exception as exc:
            raise PetTracerError(f"Failed to parse position item: {exc}") from exc

    return positions


async def get_user_profile(session: Optional[aiohttp.ClientSession] = None, token: Optional[str] = None, timeout: int = 10) -> 'UserProfile':
    """Fetch the account profile for the current token and return a typed UserProfile."""
    headers = _request_headers(token)
    close_session = session is None
    sess = session or aiohttp.ClientSession()

    try:
        async with sess.get(USER_PROFILE_URL, timeout=aiohttp.ClientTimeout(total=timeout), headers=headers) as resp:
            resp.raise_for_status()
            try:
                data = await resp.json()
            except ValueError as exc:
                raise PetTracerError("Invalid JSON response from user profile") from exc
    except aiohttp.ClientError as exc:
        raise PetTracerError(f"HTTP error while fetching user profile: {exc}") from exc
    finally:
        if close_session:
            await sess.close()

    # expect a dict
    if not isinstance(data, dict):
        raise PetTracerError("Unexpected JSON structure from user profile: expected a dict")

    from .types import UserProfile
    return UserProfile.from_dict(data)


class PetTracerClient:
    """Client for PetTracer API user-level operations.
    
    Manages authentication and provides access to user-level operations like
    fetching all devices and user profile information.
    
    Example:
        >>> client = PetTracerClient()
        >>> await client.login("username", "password")
        >>> print(client.user_name)
        >>> print(client.subscription_expires)
        >>> devices = await client.get_all_devices()
        >>> device = client.get_device(14758)
        >>> positions = await device.get_positions(1767152926491, 1767174526491)
    """
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """Initialize PetTracer client.
        
        Args:
            session: Optional aiohttp.ClientSession to reuse (e.g., from Home Assistant)
        """
        self._token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = session
        self._login_info: Optional['LoginInfo'] = None
        self._owns_session: bool = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes session if owned."""
        await self.close()
        return False
    
    @property
    def token(self) -> Optional[str]:
        """Get the current authentication token."""
        return self._token
    
    @property
    def session(self) -> Optional[aiohttp.ClientSession]:
        """Get the current aiohttp session."""
        return self._session
    
    @property
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        return self._token is not None
    
    @property
    def login_info(self) -> Optional['LoginInfo']:
        """Get the full login information dataclass."""
        return self._login_info
    
    @property
    def user_id(self) -> Optional[int]:
        """Get the user ID."""
        return self._login_info.id if self._login_info else None
    
    @property
    def user_name(self) -> Optional[str]:
        """Get the user's name."""
        return self._login_info.name if self._login_info else None
    
    @property
    def email(self) -> Optional[str]:
        """Get the user's email address."""
        return self._login_info.login if self._login_info else None
    
    @property
    def partner_id(self) -> Optional[int]:
        """Get the partner ID."""
        return self._login_info.partnerId if self._login_info else None
    
    @property
    def language(self) -> Optional[str]:
        """Get the user's language preference."""
        return self._login_info.lang if self._login_info else None
    
    @property
    def country(self) -> Optional[str]:
        """Get the user's country name."""
        if self._login_info and self._login_info.country_id and len(self._login_info.country_id) > 1:
            return self._login_info.country_id[1]
        return None
    
    @property
    def country_id(self) -> Optional[int]:
        """Get the user's country ID."""
        if self._login_info and self._login_info.country_id and len(self._login_info.country_id) > 0:
            return self._login_info.country_id[0]
        return None
    
    @property
    def device_count(self) -> Optional[int]:
        """Get the number of devices owned by the user."""
        return self._login_info.numberOfCCs if self._login_info else None
    
    @property
    def token_expires(self) -> Optional[datetime]:
        """Get the token expiration date."""
        return self._login_info.expires if self._login_info else None
    
    @property
    def subscription_info(self) -> Optional['SubscriptionInfo']:
        """Get the subscription information."""
        return self._login_info.abo if self._login_info else None
    
    @property
    def subscription_expires(self) -> Optional[datetime]:
        """Get the subscription expiration date."""
        if self._login_info and self._login_info.abo:
            return self._login_info.abo.dateExpires
        return None
    
    @property
    def subscription_id(self) -> Optional[int]:
        """Get the subscription ID."""
        if self._login_info and self._login_info.abo:
            return self._login_info.abo.id
        return None
    
    async def login(self, username: str, password: str, timeout: int = 10) -> None:
        """Authenticate with PetTracer API and store credentials.
        
        Args:
            username: PetTracer account username
            password: PetTracer account password
            timeout: Request timeout in seconds
            
        Raises:
            PetTracerError: If login fails
        """
        # If we don't have a session, create one that we'll own
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        
        result = await login(username, password, session=self._session, timeout=timeout)
        self._token = result["token"]
        
        # Parse and store login info
        from .types import LoginInfo
        self._login_info = LoginInfo.from_dict(result["data"])
    
    async def close(self) -> None:
        """Close the aiohttp session if owned by this client.
        
        Call this when done with the client to properly clean up resources.
        Only closes the session if it was created by this client (not passed in).
        """
        if self._owns_session and self._session:
            await self._session.close()
            self._session = None
    
    async def get_all_devices(self, timeout: int = 10) -> List[Device]:
        """Fetch all devices for the authenticated user.
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            List of Device objects
            
        Raises:
            PetTracerError: If not authenticated or request fails
        """
        if not self.is_authenticated:
            raise PetTracerError("Not authenticated. Call login() first.")
        
        return await get_ccs_status(
            session=self._session,
            token=self._token,
            timeout=timeout
        )
    
    def get_device(self, device_id: int) -> "PetTracerDevice":
        """Get a device-specific client for the given device ID.
        
        Args:
            device_id: The device ID to operate on
            
        Returns:
            PetTracerDevice instance for device-specific operations
            
        Raises:
            PetTracerError: If not authenticated
        """
        if not self.is_authenticated:
            raise PetTracerError("Not authenticated. Call login() first.")
        
        return PetTracerDevice(device_id, self)
    
    async def get_user_profile(self, timeout: int = 10):
        """Fetch the user profile information and update stored login data.
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            UserProfile object
            
        Raises:
            PetTracerError: If not authenticated or request fails
        """
        if not self.is_authenticated:
            raise PetTracerError("Not authenticated. Call login() first.")
        
        profile = await get_user_profile(
            session=self._session,
            token=self._token,
            timeout=timeout
        )
        
        # Update stored login info with profile data
        if self._login_info:
            self._login_info.name = profile.name
            self._login_info.login = profile.email
            self._login_info.lang = profile.lang
            if profile.country_id:
                self._login_info.country_id = [profile.country_id, None]
        
        return profile


class PetTracerDevice:
    """Device-specific client for PetTracer API operations.
    
    Provides access to device-specific operations like fetching device info
    and position history. Should be created via PetTracerClient.get_device().
    
    Example:
        >>> client = PetTracerClient()
        >>> await client.login("username", "password")
        >>> device = client.get_device(14758)
        >>> info = await device.get_info()
        >>> positions = await device.get_positions(1767152926491, 1767174526491)
    """
    
    def __init__(self, device_id: int, client: PetTracerClient):
        """Initialize device client.
        
        Args:
            device_id: The device ID this client operates on
            client: Parent PetTracerClient instance for authentication
        """
        self._device_id = device_id
        self._client = client
    
    @property
    def device_id(self) -> int:
        """Get the device ID."""
        return self._device_id
    
    async def get_info(self, timeout: int = 10):
        """Fetch detailed information for this device.
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            Device object or list of Device objects
            
        Raises:
            PetTracerError: If request fails
        """
        return await get_ccinfo(
            payload=self._device_id,
            session=self._client.session,
            token=self._client.token,
            timeout=timeout
        )
    
    async def get_positions(
        self,
        filter_time: int,
        to_time: int,
        timeout: int = 10
    ) -> List[LastPos]:
        """Fetch position history for this device within a time range.
        
        Args:
            filter_time: Start time in milliseconds since epoch
            to_time: End time in milliseconds since epoch
            timeout: Request timeout in seconds
            
        Returns:
            List of LastPos objects with position data
            
        Raises:
            PetTracerError: If request fails
        """
        return await get_ccpositions(
            dev_id=self._device_id,
            filter_time=filter_time,
            to_time=to_time,
            session=self._client.session,
            token=self._client.token,
            timeout=timeout
        )
