import urllib.request
import json
import time
import io
from PIL import Image

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(name, method, path, data=None, headers=None):
    url = f"{BASE_URL}{path}"
    h = headers or {}
    payload = None
    if data is not None and not isinstance(data, (bytes, bytearray)):
        payload = json.dumps(data).encode("utf-8")
        h["Content-Type"] = "application/json"
    elif isinstance(data, (bytes, bytearray)):
        payload = data

    req = urllib.request.Request(url, data=payload, headers=h, method=method)
    start = time.time()
    try:
        with urllib.request.urlopen(req) as resp:
            elapsed = time.time() - start
            body = resp.read().decode("utf-8", errors="replace")
            print(f"=== {name} ===")
            print(f"REQUEST: {method} {path}")
            print(f"STATUS: {resp.status}")
            print(f"TIME: {elapsed:.3f}s")
            print(f"BODY: {body[:300]}")
            return resp.status, elapsed, body
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        body = e.read().decode("utf-8", errors="replace")
        print(f"=== {name} ===")
        print(f"REQUEST: {method} {path}")
        print(f"STATUS: {e.code}")
        print(f"TIME: {elapsed:.3f}s")
        print(f"BODY: {body[:300]}")
        return e.code, elapsed, body
    except Exception as e:
        elapsed = time.time() - start
        print(f"=== {name} ===")
        print(f"REQUEST: {method} {path}")
        print(f"ERROR: {e}")
        print(f"TIME: {elapsed:.3f}s")
        return 0, elapsed, str(e)

if __name__ == "__main__":
    # Create sample valid 300x300 image
    img = Image.new("RGB", (300, 300), color=(34, 139, 34))
    img_buf = io.BytesIO()
    img.save(img_buf, format="JPEG")
    img_bytes = img_buf.getvalue()

    boundary = "----WebKitFormBoundaryVisionTest123"
    vision_body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="leaf.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + img_bytes + (
        f"\r\n--{boundary}--\r\n"
    ).encode("utf-8")

    # 5. POST /api/v1/vision/analyze with real image file
    test_endpoint(
        "5b. POST /api/v1/vision/analyze (with JPEG image)",
        "POST",
        "/api/v1/vision/analyze",
        data=vision_body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )

    # 6b. GET /api/v1/weather (real route)
    test_endpoint("6b. GET /api/v1/weather", "GET", "/api/v1/weather?location=Guntur")

    # 7b. GET /api/v1/market (real route)
    test_endpoint("7b. GET /api/v1/market", "GET", "/api/v1/market?commodity=Chilli&state=Andhra%20Pradesh&district=Guntur")
