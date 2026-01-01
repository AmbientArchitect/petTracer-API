import json
from unittest.mock import Mock

import pytest
import requests

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


class DummyResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f"HTTP {self.status_code}")


def test_get_ccs_status_parses_sample(monkeypatch):
    mock_get = Mock(return_value=DummyResponse(SAMPLE_JSON))
    monkeypatch.setattr("requests.Session.get", mock_get)

    devices = get_ccs_status()
    assert isinstance(devices, list)
    assert len(devices) == 1
    assert isinstance(devices[0], Device)
    assert devices[0].id == 14758
    assert devices[0].details.name == "Oreo"


def test_get_ccs_status_parses_fifo_entries(monkeypatch):
    # construct a sample with a fifo entry and ensure it's parsed into our types
    fifo_json = {
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
    }

    mock_get = Mock(return_value=DummyResponse([fifo_json]))
    monkeypatch.setattr("requests.Session.get", mock_get)

    devices = get_ccs_status()
    assert devices[0].fiFo is not None
    assert len(devices[0].fiFo) == 1
    entry = devices[0].fiFo[0]
    assert entry.telegram.id == 1767102243195
    assert entry.receivedBy[0].hsId == 10775
    assert entry.receivedBy[0].rssi == 158


def test_http_error_raises(monkeypatch):
    mock_get = Mock(side_effect=Exception("conn error"))
    monkeypatch.setattr("requests.Session.get", mock_get)

    with pytest.raises(PetTracerError):
        get_ccs_status()


def test_non_list_json_raises(monkeypatch):
    mock_get = Mock(return_value=DummyResponse({"ok": True}))
    monkeypatch.setattr("requests.Session.get", mock_get)

    with pytest.raises(PetTracerError):
        get_ccs_status()


def test_get_ccs_status_sets_auth_header(monkeypatch):
    captured = {}

    def mock_get(self, url, timeout, headers=None):
        captured['url'] = url
        captured['headers'] = headers
        return DummyResponse(SAMPLE_JSON)

    monkeypatch.setattr("requests.Session.get", mock_get)

    devices = get_ccs_status(token="dummy-token")
    assert devices[0].id == 14758
    assert captured['headers'] is not None
    assert captured['headers'].get('Authorization') == "Bearer dummy-token"


def test_get_ccinfo_posts_and_parses(monkeypatch):
    captured = {}

    def mock_post(self, url, json, timeout, headers=None):
        captured['url'] = url
        captured['json'] = json
        captured['headers'] = headers
        return DummyResponse(SAMPLE_JSON)

    monkeypatch.setattr("requests.Session.post", mock_post)

    # Pass integer device id and expect normalized payload
    resp = None
    try:
        resp = get_ccinfo(14758, token="another-token")
    except Exception as exc:
        pytest.fail(f"get_ccinfo raised unexpectedly: {exc}")

    assert captured['url'].endswith('/api/map/getccinfo')
    assert captured['json'] == {"devId": 14758}
    assert captured['headers'].get('Authorization') == "Bearer another-token"
    # ensure we returned typed Device objects
    assert isinstance(resp, list)
    assert isinstance(resp[0], Device)
    assert resp[0].id == 14758


def test_get_ccinfo_accepts_id_key(monkeypatch):
    captured = {}

    def mock_post(self, url, json, timeout, headers=None):
        captured['url'] = url
        captured['json'] = json
        captured['headers'] = headers
        return DummyResponse(SAMPLE_JSON)

    monkeypatch.setattr("requests.Session.post", mock_post)

    resp = None
    try:
        resp = get_ccinfo({"id": 14758}, token="another-token")
    except Exception as exc:
        pytest.fail(f"get_ccinfo raised unexpectedly: {exc}")

    assert captured['json'] == {"devId": 14758}
    assert isinstance(resp, list)
    assert isinstance(resp[0], Device)
    assert resp[0].id == 14758


def test_get_ccinfo_returns_single_device_when_server_returns_dict(monkeypatch):
    captured = {}

    def mock_post(self, url, json, timeout, headers=None):
        captured['url'] = url
        captured['json'] = json
        captured['headers'] = headers
        # return a single device dict (not a list)
        return DummyResponse(SAMPLE_JSON[0])

    monkeypatch.setattr("requests.Session.post", mock_post)

    try:
        res = get_ccinfo(14758, token="tkn")
    except Exception as exc:
        pytest.fail(f"get_ccinfo raised unexpectedly: {exc}")

    assert isinstance(res, Device)
    assert res.id == 14758
    assert captured['json'] == {"devId": 14758}


def test_login_json_response_returns_token(monkeypatch):
    captured = {}

    def mock_post(self, url, json=None, timeout=None, headers=None):
        captured['url'] = url
        captured['json'] = json
        captured['headers'] = headers

        class R:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"access_token": "tok-123"}

        return R()

    monkeypatch.setattr("requests.Session.post", mock_post)

    res = None
    try:
        res = login("user", "pw")
    except Exception as exc:
        pytest.fail(f"login raised unexpectedly: {exc}")

    assert res['token'] == "tok-123"
    assert isinstance(res['session'], requests.Session)

    # expected payload and dynamically computed content-length
    expected_payload = {"login": "user", "password": "pw"}
    import json as _json
    expected_cl = str(len(_json.dumps(expected_payload).encode('utf-8')))

    expected_headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "User-Agent": "pettracer-python-client/0.1",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Content-Length": expected_cl,
    }

    assert captured['json'] == expected_payload
    assert captured['headers'] == expected_headers
    assert captured['url'].endswith('/user/login')


def test_login_json_missing_token_raises(monkeypatch):
    def mock_post(self, url, json=None, timeout=None, headers=None):
        class R:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {"status": "ok"}  # no token

        return R()

    monkeypatch.setattr("requests.Session.post", mock_post)

    with pytest.raises(PetTracerError):
        login("user", "pw")


def test_get_user_profile_parses(monkeypatch):
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

    def mock_get(self, url, timeout, headers=None):
        captured['url'] = url
        captured['headers'] = headers
        return DummyResponse(profile_json)

    monkeypatch.setattr("requests.Session.get", mock_get)

    from pettracer.types import UserProfile

    res = get_user_profile(token="tkn")
    assert isinstance(res, UserProfile)
    assert res.id == 19804
    assert res.email == "richard@egilius.net"
    assert captured['headers'].get('Authorization') == "Bearer tkn"


def test_get_ccpositions_parses_sample(monkeypatch):
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

    def mock_post(self, url, json, timeout, headers=None):
        captured['url'] = url
        captured['json'] = json
        captured['headers'] = headers
        return DummyResponse(positions_json)

    monkeypatch.setattr("requests.Session.post", mock_post)

    positions = get_ccpositions(14758, 1767152926491, 1767174526491, token="test-token")
    assert isinstance(positions, list)
    assert len(positions) == 2
    assert isinstance(positions[0], LastPos)
    assert positions[0].id == 110670824
    assert positions[0].posLat == 51.4000459
    assert positions[0].posLong == -1.0838738
    assert positions[1].id == 110670868
    assert captured['json'] == {"devId": 14758, "filterTime": 1767152926491, "toTime": 1767174526491}
    assert captured['headers'].get('Authorization') == "Bearer test-token"


def test_get_ccpositions_http_error_raises(monkeypatch):
    mock_post = Mock(side_effect=Exception("network error"))
    monkeypatch.setattr("requests.Session.post", mock_post)

    with pytest.raises(PetTracerError):
        get_ccpositions(14758, 1767152926491, 1767174526491)


def test_get_ccpositions_non_list_json_raises(monkeypatch):
    mock_post = Mock(return_value=DummyResponse({"error": "not a list"}))
    monkeypatch.setattr("requests.Session.post", mock_post)

    with pytest.raises(PetTracerError):
        get_ccpositions(14758, 1767152926491, 1767174526491)


# ============================================================================
# PetTracerClient and PetTracerDevice class tests
# ============================================================================

def test_pettracer_client_init_without_credentials():
    """Test creating a client without auto-login."""
    from pettracer.client import PetTracerClient
    
    client = PetTracerClient()
    assert client.token is None
    assert client.session is None
    assert not client.is_authenticated


def test_pettracer_client_login(monkeypatch):
    """Test client login stores token and session."""
    from pettracer.client import PetTracerClient
    
    def mock_post(self, url, json=None, timeout=None, headers=None):
        class R:
            status_code = 200
            def raise_for_status(self):
                return None
            def json(self):
                return {"access_token": "test-token-123"}
        return R()
    
    monkeypatch.setattr("requests.Session.post", mock_post)
    
    client = PetTracerClient()
    client.login("testuser", "testpass")
    
    assert client.token == "test-token-123"
    assert client.session is not None
    assert client.is_authenticated


def test_pettracer_client_auto_login(monkeypatch):
    """Test client with auto-login in constructor."""
    from pettracer.client import PetTracerClient
    
    def mock_post(self, url, json=None, timeout=None, headers=None):
        class R:
            status_code = 200
            def raise_for_status(self):
                return None
            def json(self):
                return {"access_token": "auto-token"}
        return R()
    
    monkeypatch.setattr("requests.Session.post", mock_post)
    
    client = PetTracerClient("user", "pass")
    assert client.token == "auto-token"
    assert client.is_authenticated


def test_pettracer_client_get_all_devices_requires_auth():
    """Test that get_all_devices raises if not authenticated."""
    from pettracer.client import PetTracerClient
    
    client = PetTracerClient()
    with pytest.raises(PetTracerError) as exc:
        client.get_all_devices()
    assert "Not authenticated" in str(exc.value)


def test_pettracer_client_get_all_devices(monkeypatch):
    """Test fetching all devices through client."""
    from pettracer.client import PetTracerClient
    
    def mock_post(self, url, json=None, timeout=None, headers=None):
        class R:
            status_code = 200
            def raise_for_status(self):
                return None
            def json(self):
                return {"access_token": "token-xyz"}
        return R()
    
    def mock_get(self, url, timeout, headers=None):
        return DummyResponse(SAMPLE_JSON)
    
    monkeypatch.setattr("requests.Session.post", mock_post)
    monkeypatch.setattr("requests.Session.get", mock_get)
    
    client = PetTracerClient()
    client.login("user", "pass")
    devices = client.get_all_devices()
    
    assert isinstance(devices, list)
    assert len(devices) == 1
    assert isinstance(devices[0], Device)
    assert devices[0].id == 14758


def test_pettracer_client_get_device_requires_auth():
    """Test that get_device raises if not authenticated."""
    from pettracer.client import PetTracerClient
    
    client = PetTracerClient()
    with pytest.raises(PetTracerError) as exc:
        client.get_device(14758)
    assert "Not authenticated" in str(exc.value)


def test_pettracer_client_get_device(monkeypatch):
    """Test getting a device-specific client."""
    from pettracer.client import PetTracerClient, PetTracerDevice
    
    def mock_post(self, url, json=None, timeout=None, headers=None):
        class R:
            status_code = 200
            def raise_for_status(self):
                return None
            def json(self):
                return {"access_token": "token"}
        return R()
    
    monkeypatch.setattr("requests.Session.post", mock_post)
    
    client = PetTracerClient()
    client.login("user", "pass")
    device = client.get_device(14758)
    
    assert isinstance(device, PetTracerDevice)
    assert device.device_id == 14758


def test_pettracer_client_get_user_profile_requires_auth():
    """Test that get_user_profile raises if not authenticated."""
    from pettracer.client import PetTracerClient
    
    client = PetTracerClient()
    with pytest.raises(PetTracerError) as exc:
        client.get_user_profile()
    assert "Not authenticated" in str(exc.value)


def test_pettracer_client_get_user_profile(monkeypatch):
    """Test fetching user profile through client."""
    from pettracer.client import PetTracerClient
    
    profile_json = {
        "id": 19804,
        "email": "test@example.com",
        "name": "Test User",
    }
    
    def mock_post(self, url, json=None, timeout=None, headers=None):
        class R:
            status_code = 200
            def raise_for_status(self):
                return None
            def json(self):
                return {"access_token": "token"}
        return R()
    
    def mock_get(self, url, timeout, headers=None):
        return DummyResponse(profile_json)
    
    monkeypatch.setattr("requests.Session.post", mock_post)
    monkeypatch.setattr("requests.Session.get", mock_get)
    
    from pettracer.types import UserProfile
    
    client = PetTracerClient()
    client.login("user", "pass")
    profile = client.get_user_profile()
    
    assert isinstance(profile, UserProfile)
    assert profile.id == 19804
    assert profile.email == "test@example.com"


def test_pettracer_device_get_info(monkeypatch):
    """Test fetching device info through device client."""
    from pettracer.client import PetTracerClient
    
    captured = {}
    
    def mock_post(self, url, json=None, timeout=None, headers=None):
        captured['url'] = url
        captured['json'] = json
        
        if 'login' in url:
            class R:
                status_code = 200
                def raise_for_status(self):
                    return None
                def json(self):
                    return {"access_token": "token"}
            return R()
        else:
            # getccinfo
            return DummyResponse(SAMPLE_JSON)
    
    monkeypatch.setattr("requests.Session.post", mock_post)
    
    client = PetTracerClient()
    client.login("user", "pass")
    device = client.get_device(14758)
    
    info = device.get_info()
    
    assert isinstance(info, list)
    assert info[0].id == 14758
    assert captured['json'] == {"devId": 14758}


def test_pettracer_device_get_positions(monkeypatch):
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
    
    def mock_post(self, url, json=None, timeout=None, headers=None):
        captured['url'] = url
        captured['json'] = json
        
        if 'login' in url:
            class R:
                status_code = 200
                def raise_for_status(self):
                    return None
                def json(self):
                    return {"access_token": "token"}
            return R()
        else:
            # getccpositions
            return DummyResponse(positions_json)
    
    monkeypatch.setattr("requests.Session.post", mock_post)
    
    client = PetTracerClient()
    client.login("user", "pass")
    device = client.get_device(14758)
    
    positions = device.get_positions(1767152926491, 1767174526491)
    
    assert isinstance(positions, list)
    assert isinstance(positions[0], LastPos)
    assert positions[0].id == 110670824
    assert positions[0].posLat == 51.4000459
    assert captured['json'] == {"devId": 14758, "filterTime": 1767152926491, "toTime": 1767174526491}


def test_pettracer_device_id_property():
    """Test device_id property."""
    from pettracer.client import PetTracerClient, PetTracerDevice
    
    client = PetTracerClient()
    client._token = "fake-token"
    client._session = requests.Session()
    
    device = PetTracerDevice(12345, client)
    assert device.device_id == 12345


def test_pettracer_client_login_info_properties(monkeypatch):
    """Test that login stores and exposes user information via properties."""
    from pettracer.client import PetTracerClient
    
    def mock_post(self, url, json=None, timeout=None, headers=None):
        class R:
            status_code = 200
            def raise_for_status(self):
                return None
            def json(self):
                return {
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
                }
        return R()
    
    monkeypatch.setattr("requests.Session.post", mock_post)
    
    client = PetTracerClient()
    client.login("user", "pass")
    
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


def test_pettracer_client_login_info_none_before_login():
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
