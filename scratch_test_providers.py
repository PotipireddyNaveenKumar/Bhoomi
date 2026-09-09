import os
import urllib.request
import urllib.parse
import json
import time
from app.core.config import settings

def test_openai():
    key = settings.OPENAI_API_KEY
    if not key:
        return "MISSING KEY"
    url = "https://api.openai.com/v1/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return f"OK (HTTP {resp.status}, {time.time()-start:.2f}s)"
    except urllib.error.HTTPError as e:
        return f"FAILED (HTTP {e.code}: {e.read().decode('utf-8')[:100]})"
    except Exception as e:
        return f"FAILED ({e})"

def test_gemini():
    key = settings.GEMINI_API_KEY
    if not key:
        return "MISSING KEY"
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    req = urllib.request.Request(url)
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return f"OK (HTTP {resp.status}, {time.time()-start:.2f}s)"
    except urllib.error.HTTPError as e:
        return f"FAILED (HTTP {e.code}: {e.read().decode('utf-8')[:100]})"
    except Exception as e:
        return f"FAILED ({e})"

def test_groq():
    key = settings.GROQ_API_KEY
    if not key:
        return "MISSING KEY"
    url = "https://api.groq.com/openai/v1/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return f"OK (HTTP {resp.status}, {time.time()-start:.2f}s)"
    except urllib.error.HTTPError as e:
        return f"FAILED (HTTP {e.code}: {e.read().decode('utf-8')[:100]})"
    except Exception as e:
        return f"FAILED ({e})"

def test_sarvam():
    key = settings.SARVAM_API_KEY
    if not key:
        return "MISSING KEY"
    # Test Sarvam with a trivial text-to-speech request or headers check
    url = "https://api.sarvam.ai/text-to-speech"
    payload = json.dumps({
        "inputs": ["Hello"],
        "target_language_code": "hi-IN",
        "speaker": "meera"
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"api-subscription-key": key, "Content-Type": "application/json"},
        method="POST"
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return f"OK (HTTP {resp.status}, {time.time()-start:.2f}s)"
    except urllib.error.HTTPError as e:
        return f"FAILED (HTTP {e.code}: {e.read().decode('utf-8')[:100]})"
    except Exception as e:
        return f"FAILED ({e})"

def test_openweathermap():
    key = settings.WEATHER_API_KEY
    if not key:
        return "MISSING KEY"
    url = f"https://api.openweathermap.org/data/2.5/weather?q=Guntur&appid={key}"
    req = urllib.request.Request(url)
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return f"OK (HTTP {resp.status}, {time.time()-start:.2f}s)"
    except urllib.error.HTTPError as e:
        return f"FAILED (HTTP {e.code}: {e.read().decode('utf-8')[:100]})"
    except Exception as e:
        return f"FAILED ({e})"

def test_data_gov():
    key = settings.DATA_GOV_API_KEY
    if not key:
        return "MISSING KEY"
    url = f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key={key}&format=json&limit=1"
    req = urllib.request.Request(url)
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return f"OK (HTTP {resp.status}, {time.time()-start:.2f}s)"
    except urllib.error.HTTPError as e:
        return f"FAILED (HTTP {e.code}: {e.read().decode('utf-8')[:100]})"
    except Exception as e:
        return f"FAILED ({e})"

if __name__ == "__main__":
    print("OpenAI:", test_openai())
    print("Gemini:", test_gemini())
    print("Groq:", test_groq())
    print("Sarvam AI:", test_sarvam())
    print("OpenWeatherMap:", test_openweathermap())
    print("Data.gov.in:", test_data_gov())
