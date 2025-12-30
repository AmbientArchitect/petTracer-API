import json
import requests

URL = "https://portal.pettracer.com/en/login"
PAYLOAD = {"username": "user", "password": "pw"}

login_headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    # Intentionally omitting Content-Length here so requests sets it appropriately
    "Content-Type": "application/json",
    "Host": "portal.pettracer.com",
    "Origin": "https://portal.pettracer.com",
    "Referer": "https://portal.pettracer.com/en/login",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

print("1) OPTIONS request to see allowed methods and server response headers")
try:
    r = requests.options(URL, headers=login_headers, timeout=10)
    print(r.status_code, r.reason)
    print("Allow header:", r.headers.get("Allow"))
    print("Response headers:\n", json.dumps(dict(r.headers), indent=2)[:1000])
    print("Response body (truncated):\n", r.text[:500])
except Exception as exc:
    print("OPTIONS request failed:", exc)

print('\n2) POST with JSON via requests.json=payload (requests sets content-type and content-length)')
try:
    r = requests.post(URL, json=PAYLOAD, headers=login_headers, timeout=10)
    print(r.status_code, r.reason)
    print("Response headers:\n", json.dumps(dict(r.headers), indent=2)[:1000])
    print("Response body (truncated):\n", r.text[:1000])
except Exception as exc:
    print("POST json failed:", exc)

print('\n3) POST with form data (application/x-www-form-urlencoded)')
try:
    form_headers = login_headers.copy()
    form_headers["Content-Type"] = "application/x-www-form-urlencoded"
    r = requests.post(URL, data=PAYLOAD, headers=form_headers, timeout=10)
    print(r.status_code, r.reason)
    print("Response headers:\n", json.dumps(dict(r.headers), indent=2)[:1000])
    print("Response body (truncated):\n", r.text[:1000])
except Exception as exc:
    print("POST form failed:", exc)

print('\n4) POST with JSON but with explicit Content-Length header (may be wrong)')
try:
    json_body = json.dumps(PAYLOAD)
    bad_headers = login_headers.copy()
    bad_headers["Content-Length"] = "9999"  # intentionally wrong
    r = requests.post(URL, data=json_body, headers=bad_headers, timeout=10)
    print(r.status_code, r.reason)
    print("Response headers:\n", json.dumps(dict(r.headers), indent=2)[:1000])
    print("Response body (truncated):\n", r.text[:1000])
except Exception as exc:
    print("POST json with bad length failed:", exc)

print('\nDone')
