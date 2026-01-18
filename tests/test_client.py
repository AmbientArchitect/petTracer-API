"""Tests for the PetTracer async client."""
import json
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

import pytest
import aiohttp
from aiohttp import ClientError

from pettracer.client import get_ccs_status, get_ccinfo, get_ccpositions, login, get_user_profile, PetTracerError
from pettracer.types import Device, LastPos


SAMPLE_JSON = [
    {
        "id": 14758,
        "accuWarn": 3810,
        "safetyZone": False,
        "hw": 656643,
        "sw": 656393,
        "bl": 656386,
        "bat": 4207,
        "chg": 0,
        "userId": 15979,
        "masterHs": {
            "id": 10775,
            "posLat": 51.4000701,
            "posLong": -1.0842267,
            "hw": 656384,
            "sw": 656388,
            "bl": 656385,
            "bat": 0,
            "userId": None,
            "status": 0,
            "lastContact": "2025-12-27T21:51:40.310+0000",
            "devMode": False
        },
        "mode": 1,
        "modeSet": 1,
        "status": 0,
        "search": False,
        "lastTlgNr": -42,
        "lastContact": "2025-12-27T21:51:40.310+0000",
        "lastPos": {
            "id": 110294833,
            "posLat": 51.4000701,
            "posLong": -1.0842267,
            "fixS": 3,
            "fixP": 2,
            "horiPrec": 12,
            "sat": 8,
            "rssi": 111,
            "acc": 16,
            "flags": 32,
            "timeMeasure": "2025-12-27T09:59:41.000+0000",
            "timeDb": "2025-12-27T09:59:41.000+0000"
        },
        "devMode": False,
        "details": {
            "id": 14758,
            "image": None,
            "img": "img1570960283064022523",
            "color": 255,
            "birth": "2018-07-15T23:00:00.000+0000",
            "name": "Oreo"
        },
        "led": False,
        "ble": False,
        "buz": False,
        "lastRssi": -30,
        "flags": 2,
        "searchModeDuration": -1,
        "masterStatus": "ACTIVE",
        "home": True,
        "homeSince": "2025-12-27T19:07:17.721+0000",
        "owner": True,
        "fiFo": []
    }
]


class MockResponse:
    """Mock aiohttp response."""
    
    def __init__(self, json_data, status=200):
        self._json = json_data
        self.status = status
        self.headers = {}
    
    async def json(self):
        return self._json
    
    def raise_for_status(self):
        if not (200 <= self.status < 300):
            raise aiohttp.ClientError(f"HTTP {self.status} error")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


@pytest.mark.asyncio
async def test_get_ccs_status_parses_sample():
    """Test that get_ccs_status parses the sample JSON correctly."""
    response = MockResponse(SAMPLE_JSON)
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.get.return_value = response
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        devices = await get_ccs_status()
        
        assert isinstance(devices, list)
        assert len(devices) == 1
        assert isinstance(devices[0], Device)
        assert devices[0].id == 14758
        assert devices[0].details.name == "Oreo"


@pytest.mark.asyncio
async def test_get_ccs_status_parses_fifo_entries():
    """Test parsing FIFO entries."""
    fifo_json = [{
        "id": 14758,
        "fiFo": [
            {
                "telegram": {
                    "id": 1767102243195,
                    "deviceType": 0,
                    "deviceId": 14758,
                    "hsId": 10775,
                    "telegram": "000039a604071f20541027a40100010a04090a05030a040200002a17029e74",
                    "latitude": None,
                    "longitude": None,
                    "timeDb": "2025-12-30T13:44:03.195+0000",
                    "timeDev": None,
                    "cmd": 7,
                    "charging": False
                },
                "receivedBy": [
                    {"hsId": 10775, "rssi": 158}
                ]
            }
        ]
    }]
    
    response = MockResponse(fifo_json)
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.get.return_value = response
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        devices = await get_ccs_status()
        assert devices[0].fiFo is not None
        assert len(devices[0].fiFo) == 1
        entry = devices[0].fiFo[0]
        assert entry.telegram.id == 1767102243195
        assert entry.receivedBy[0].hsId == 10775
        assert entry.receivedBy[0].rssi == 158


@pytest.mark.asyncio
async def test_http_error_raises():
    """Test that HTTP errors are caught and wrapped."""
    @asynccontextmanager
    async def mock_get(url, timeout, headers=None):
        response = MockResponse({}, status=500)
        yield response
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        with pytest.raises(PetTracerError):
            await get_ccs_status()


@pytest.mark.asyncio
async def test_non_list_json_raises():
    """Test that non-list JSON response raises an error."""
    response = MockResponse({"ok": True})
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.get.return_value = response
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        with pytest.raises(PetTracerError):
            await get_ccs_status()


@pytest.mark.asyncio
async def test_get_ccs_status_sets_auth_header():
    """Test that authorization header is set correctly."""
    captured = {}
    
    @asynccontextmanager
    async def capture_get(url, timeout, headers=None):
        captured['url'] = url
        captured['headers'] = headers
        yield MockResponse(SAMPLE_JSON)
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.get = capture_get
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        devices = await get_ccs_status(token="dummy-token")
        assert devices[0].id == 14758
        assert captured['headers'] is not None
        assert captured['headers'].get('Authorization') == "Bearer dummy-token"


@pytest.mark.asyncio
async def test_get_ccinfo_posts_and_parses():
    """Test get_ccinfo posts and parses correctly."""
    captured = {}
    
    @asynccontextmanager
    async def capture_post(url, json, timeout, headers=None):
        captured['url'] = url
        captured['json'] = json
        captured['headers'] = headers
        yield MockResponse(SAMPLE_JSON)
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = capture_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        resp = await get_ccinfo(14758, token="another-token")
        
        assert captured['url'].endswith('/api/map/getccinfo')
        assert captured['json'] == {"devId": 14758}
        assert captured['headers'].get('Authorization') == "Bearer another-token"
        assert isinstance(resp, list)
        assert isinstance(resp[0], Device)
        assert resp[0].id == 14758


@pytest.mark.asyncio
async def test_get_ccinfo_accepts_id_key():
    """Test get_ccinfo accepts dict with 'id' key."""
    captured = {}
    
    @asynccontextmanager
    async def capture_post(url, json, timeout, headers=None):
        captured['json'] = json
        yield MockResponse(SAMPLE_JSON)
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = capture_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        resp = await get_ccinfo({"id": 14758}, token="another-token")
        
        assert captured['json'] == {"devId": 14758}
        assert isinstance(resp, list)
        assert isinstance(resp[0], Device)
        assert resp[0].id == 14758


@pytest.mark.asyncio
async def test_get_ccinfo_returns_single_device_when_server_returns_dict():
    """Test get_ccinfo handles single device dict response."""
    @asynccontextmanager
    async def mock_post(url, json, timeout, headers=None):
        yield MockResponse(SAMPLE_JSON[0])
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        res = await get_ccinfo(14758, token="tkn")
        
        assert isinstance(res, Device)
        assert res.id == 14758


@pytest.mark.asyncio
async def test_login_json_response_returns_token():
    """Test login returns token from JSON response."""
    captured = {}
    
    @asynccontextmanager
    async def capture_post(url, json=None, timeout=None, headers=None):
        captured['url'] = url
        captured['json'] = json
        captured['headers'] = headers
        yield MockResponse({"access_token": "tok-123"})
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = capture_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        res = await login("user", "pw")
        
        assert res['token'] == "tok-123"
        
        # Verify payload
        expected_payload = {"login": "user", "password": "pw"}
        assert captured['json'] == expected_payload
        assert captured['url'].endswith('/user/login')


@pytest.mark.asyncio
async def test_login_json_missing_token_raises():
    """Test login raises error when token is missing."""
    @asynccontextmanager
    async def mock_post(url, json=None, timeout=None, headers=None):
        yield MockResponse({"status": "ok"})  # no token
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        with pytest.raises(PetTracerError):
            await login("user", "pw")


@pytest.mark.asyncio
async def test_get_user_profile_parses():
    """Test get_user_profile parses response correctly."""
    captured = {}
    
    profile_json = {
        "id": 19804,
        "email": "richard@egilius.net",
        "street": "Webster House",
        "street2": "Shortheath Lane",
        "zip": "RG7 4EQ",
        "city": "Reading",
        "name": "Richard Giles",
        "mobile": "07710900362",
        "lang": "en_GB",
        "country_id": 231,
        "title": None,
        "image_1920": None,
        "x_studio_newsletter": False,
    }
    
    @asynccontextmanager
    async def capture_get(url, timeout, headers=None):
        captured['url'] = url
        captured['headers'] = headers
        yield MockResponse(profile_json)
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.get = capture_get
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        from pettracer.types import UserProfile
        
        res = await get_user_profile(token="tkn")
        assert isinstance(res, UserProfile)
        assert res.id == 19804
        assert res.email == "richard@egilius.net"
        assert captured['headers'].get('Authorization') == "Bearer tkn"


@pytest.mark.asyncio
async def test_get_ccpositions_parses_sample():
    """Test get_ccpositions parses positions correctly."""
    captured = {}
    
    positions_json = [
        {
            "id": 110670824,
            "posLat": 51.4000459,
            "posLong": -1.0838738,
            "fixS": 3,
            "fixP": 1,
            "horiPrec": 12,
            "sat": 9,
            "rssi": 103,
            "acc": 2,
            "flags": 32,
            "timeMeasure": "2025-12-31T09:45:47.000+0000",
            "timeDb": "2025-12-31T09:45:48.000+0000"
        },
        {
            "id": 110670868,
            "posLat": 51.3999838,
            "posLong": -1.0838921,
            "fixS": 3,
            "fixP": 1,
            "horiPrec": 9,
            "sat": 9,
            "rssi": 102,
            "acc": 2,
            "flags": 0,
            "timeMeasure": "2025-12-31T09:46:18.000+0000",
            "timeDb": "2025-12-31T09:46:18.000+0000"
        }
    ]
    
    @asynccontextmanager
    async def capture_post(url, json, timeout, headers=None):
        captured['url'] = url
        captured['json'] = json
        captured['headers'] = headers
        yield MockResponse(positions_json)
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = capture_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        positions = await get_ccpositions(14758, 1767152926491, 1767174526491, token="test-token")
        
        assert isinstance(positions, list)
        assert len(positions) == 2
        assert isinstance(positions[0], LastPos)
        assert positions[0].id == 110670824
        assert positions[0].posLat == 51.4000459
        assert positions[0].posLong == -1.0838738
        assert positions[1].id == 110670868
        assert captured['json'] == {"devId": 14758, "filterTime": 1767152926491, "toTime": 1767174526491}
        assert captured['headers'].get('Authorization') == "Bearer test-token"


@pytest.mark.asyncio
async def test_get_ccpositions_http_error_raises():
    """Test get_ccpositions raises on HTTP error."""
    @asynccontextmanager
    async def mock_post(url, json, timeout, headers=None):
        response = MockResponse({}, status=500)
        yield response
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        with pytest.raises(PetTracerError):
            await get_ccpositions(14758, 1767152926491, 1767174526491)


@pytest.mark.asyncio
async def test_get_ccpositions_non_list_json_raises():
    """Test get_ccpositions raises when response is not a list."""
    response = MockResponse({"error": "not a list"})
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post.return_value = response
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        with pytest.raises(PetTracerError):
            await get_ccpositions(14758, 1767152926491, 1767174526491)


# ============================================================================
# PetTracerClient and PetTracerDevice class tests
# ============================================================================

@pytest.mark.asyncio
async def test_pettracer_client_init_without_credentials():
    """Test creating a client without auto-login."""
    from pettracer.client import PetTracerClient
    
    client = PetTracerClient()
    assert client.token is None
    assert client.session is None
    assert not client.is_authenticated


@pytest.mark.asyncio
async def test_pettracer_client_login():
    """Test client login stores token and session."""
    from pettracer.client import PetTracerClient
    
    @asynccontextmanager
    async def mock_post(url, json=None, timeout=None, headers=None):
        yield MockResponse({"access_token": "test-token-123"})
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        client = PetTracerClient()
        await client.login("testuser", "testpass")
        
        assert client.token == "test-token-123"
        assert client.session is not None
        assert client.is_authenticated
        
        await client.close()


@pytest.mark.asyncio
async def test_pettracer_client_get_all_devices_requires_auth():
    """Test that get_all_devices raises if not authenticated."""
    from pettracer.client import PetTracerClient
    
    client = PetTracerClient()
    with pytest.raises(PetTracerError) as exc:
        await client.get_all_devices()
    assert "Not authenticated" in str(exc.value)


@pytest.mark.asyncio
async def test_pettracer_client_get_all_devices():
    """Test fetching all devices through client."""
    from pettracer.client import PetTracerClient
    
    call_count = {'login': 0, 'get': 0}
    
    @asynccontextmanager
    async def mock_post(url, json=None, timeout=None, headers=None):
        call_count['login'] += 1
        yield MockResponse({"access_token": "token-xyz"})
    
    @asynccontextmanager
    async def mock_get(url, timeout, headers=None):
        call_count['get'] += 1
        yield MockResponse(SAMPLE_JSON)
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.get = mock_get
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        client = PetTracerClient()
        await client.login("user", "pass")
        devices = await client.get_all_devices()
        
        assert isinstance(devices, list)
        assert len(devices) == 1
        assert isinstance(devices[0], Device)
        assert devices[0].id == 14758
        
        await client.close()


@pytest.mark.asyncio
async def test_pettracer_client_get_device_requires_auth():
    """Test that get_device raises if not authenticated."""
    from pettracer.client import PetTracerClient
    
    client = PetTracerClient()
    with pytest.raises(PetTracerError) as exc:
        client.get_device(14758)
    assert "Not authenticated" in str(exc.value)


@pytest.mark.asyncio
async def test_pettracer_client_get_device():
    """Test getting a device-specific client."""
    from pettracer.client import PetTracerClient, PetTracerDevice
    
    @asynccontextmanager
    async def mock_post(url, json=None, timeout=None, headers=None):
        yield MockResponse({"access_token": "token"})
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        client = PetTracerClient()
        await client.login("user", "pass")
        device = client.get_device(14758)
        
        assert isinstance(device, PetTracerDevice)
        assert device.device_id == 14758
        
        await client.close()


@pytest.mark.asyncio
async def test_pettracer_client_get_user_profile_requires_auth():
    """Test that get_user_profile raises if not authenticated."""
    from pettracer.client import PetTracerClient
    
    client = PetTracerClient()
    with pytest.raises(PetTracerError) as exc:
        await client.get_user_profile()
    assert "Not authenticated" in str(exc.value)


@pytest.mark.asyncio
async def test_pettracer_client_get_user_profile():
    """Test fetching user profile through client."""
    from pettracer.client import PetTracerClient
    
    profile_json = {
        "id": 19804,
        "email": "test@example.com",
        "name": "Test User",
    }
    
    @asynccontextmanager
    async def mock_post(url, json=None, timeout=None, headers=None):
        yield MockResponse({"access_token": "token"})
    
    @asynccontextmanager
    async def mock_get(url, timeout, headers=None):
        yield MockResponse(profile_json)
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.get = mock_get
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        from pettracer.types import UserProfile
        
        client = PetTracerClient()
        await client.login("user", "pass")
        profile = await client.get_user_profile()
        
        assert isinstance(profile, UserProfile)
        assert profile.id == 19804
        assert profile.email == "test@example.com"
        
        await client.close()


@pytest.mark.asyncio
async def test_pettracer_device_get_info():
    """Test fetching device info through device client."""
    from pettracer.client import PetTracerClient
    
    captured = {}
    
    @asynccontextmanager
    async def mock_post(url, json=None, timeout=None, headers=None):
        captured['url'] = url
        captured['json'] = json
        
        if 'login' in url:
            yield MockResponse({"access_token": "token"})
        else:
            yield MockResponse(SAMPLE_JSON)
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        client = PetTracerClient()
        await client.login("user", "pass")
        device = client.get_device(14758)
        
        info = await device.get_info()
        
        assert isinstance(info, list)
        assert info[0].id == 14758
        assert captured['json'] == {"devId": 14758}
        
        await client.close()


@pytest.mark.asyncio
async def test_pettracer_device_get_positions():
    """Test fetching device positions through device client."""
    from pettracer.client import PetTracerClient
    
    captured = {}
    
    positions_json = [
        {
            "id": 110670824,
            "posLat": 51.4000459,
            "posLong": -1.0838738,
            "fixS": 3,
            "fixP": 1,
            "horiPrec": 12,
            "sat": 9,
            "rssi": 103,
            "acc": 2,
            "flags": 32,
            "timeMeasure": "2025-12-31T09:45:47.000+0000",
            "timeDb": "2025-12-31T09:45:48.000+0000"
        }
    ]
    
    @asynccontextmanager
    async def mock_post(url, json=None, timeout=None, headers=None):
        captured['url'] = url
        captured['json'] = json
        
        if 'login' in url:
            yield MockResponse({"access_token": "token"})
        else:
            yield MockResponse(positions_json)
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        client = PetTracerClient()
        await client.login("user", "pass")
        device = client.get_device(14758)
        
        positions = await device.get_positions(1767152926491, 1767174526491)
        
        assert isinstance(positions, list)
        assert isinstance(positions[0], LastPos)
        assert positions[0].id == 110670824
        assert positions[0].posLat == 51.4000459
        assert captured['json'] == {"devId": 14758, "filterTime": 1767152926491, "toTime": 1767174526491}
        
        await client.close()


@pytest.mark.asyncio
async def test_pettracer_device_id_property():
    """Test device_id property."""
    from pettracer.client import PetTracerClient, PetTracerDevice
    
    client = PetTracerClient()
    client._token = "fake-token"
    client._session = MagicMock()
    
    device = PetTracerDevice(12345, client)
    assert device.device_id == 12345


@pytest.mark.asyncio
async def test_pettracer_client_context_manager():
    """Test client works as async context manager."""
    from pettracer.client import PetTracerClient
    
    @asynccontextmanager
    async def mock_post(url, json=None, timeout=None, headers=None):
        yield MockResponse({"access_token": "token"})
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        async with PetTracerClient() as client:
            await client.login("user", "pass")
            assert client.is_authenticated
        
        # Session should be closed after context manager exits
        mock_session.close.assert_called()


@pytest.mark.asyncio
async def test_pettracer_client_with_provided_session():
    """Test client doesn't close session it doesn't own."""
    from pettracer.client import PetTracerClient
    
    @asynccontextmanager
    async def mock_post(url, json=None, timeout=None, headers=None):
        yield MockResponse({"access_token": "token"})
    
    mock_session = MagicMock()
    mock_session.post = mock_post
    mock_session.close = AsyncMock()
    
    client = PetTracerClient(session=mock_session)
    await client.login("user", "pass")
    
    assert client.is_authenticated
    assert client.session is mock_session
    
    # Closing client shouldn't close the provided session
    await client.close()
    mock_session.close.assert_not_called()


@pytest.mark.asyncio
async def test_pettracer_client_login_info_properties():
    """Test that login stores and exposes user information via properties."""
    from pettracer.client import PetTracerClient
    
    @asynccontextmanager
    async def mock_post(url, json=None, timeout=None, headers=None):
        yield MockResponse({
            'id': 15979,
            'login': 'test@example.com',
            'name': 'Test User',
            'lang': 'en_GB',
            'country_id': [231, 'United Kingdom'],
            'numberOfCCs': 2,
            'partnerId': 19804,
            'access_token': 'test-token-123',
            'expires': '2026-01-31',
            'abo': {
                'id': 4649776,
                'userId': 15979,
                'dateExpires': '2026-09-03',
                'odooId': 28565,
            }
        })
    
    with patch('aiohttp.ClientSession') as mock_session_class:
        mock_session = MagicMock()
        mock_session.post = mock_post
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session
        
        client = PetTracerClient()
        await client.login("user", "pass")
        
        # Test all properties
        assert client.user_id == 15979
        assert client.user_name == "Test User"
        assert client.email == "test@example.com"
        assert client.partner_id == 19804
        assert client.language == "en_GB"
        assert client.country == "United Kingdom"
        assert client.country_id == 231
        assert client.device_count == 2
        assert client.token_expires.strftime("%Y-%m-%d") == "2026-01-31"
        assert client.subscription_expires.strftime("%Y-%m-%d") == "2026-09-03"
        assert client.subscription_id == 4649776
        assert client.login_info is not None
        assert client.subscription_info is not None
        
        await client.close()


@pytest.mark.asyncio
async def test_pettracer_client_login_info_none_before_login():
    """Test that properties return None before login."""
    from pettracer.client import PetTracerClient
    
    client = PetTracerClient()
    
    assert client.user_id is None
    assert client.user_name is None
    assert client.email is None
    assert client.partner_id is None
    assert client.device_count is None
    assert client.token_expires is None
    assert client.subscription_expires is None
    assert client.login_info is None
