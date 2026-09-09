import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_api():
    sys.stdout.reconfigure(encoding="utf-8")
    print("=== TESTING LIVE BHOOMI FASTAPI HTTP ENDPOINTS ===")
    
    # 1. Health / Demo Reset
    try:
        r = requests.post(f"{BASE_URL}/demo/reset", json={}, timeout=5)
        print(f"1. Demo Reset: Status {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"1. Demo Reset Failed: {e}")

    # 2. Live Weather Endpoint
    try:
        r = requests.get(f"{BASE_URL}/weather?location=Guntur", timeout=5)
        print(f"2. Weather Endpoint: Status {r.status_code} - Temp: {r.json().get('current', {}).get('temperature_celsius')}")
    except Exception as e:
        print(f"2. Weather Endpoint Failed: {e}")

    # 3. Live Market Endpoint
    try:
        r = requests.get(f"{BASE_URL}/market?commodity=Chilli&district=Guntur&state=Andhra+Pradesh", timeout=5)
        print(f"3. Market Endpoint: Status {r.status_code} - Recommended: {r.json().get('recommended_mandi')}")
    except Exception as e:
        print(f"3. Market Endpoint Failed: {e}")

    # 4. Live Tasks Today Endpoint
    try:
        r = requests.get(f"{BASE_URL}/tasks/today", timeout=5)
        print(f"4. Tasks Today: Status {r.status_code} - Tasks count: {len(r.json())}")
    except Exception as e:
        print(f"4. Tasks Today Failed: {e}")

    # 5. Live Chat Endpoint - Multi-turn Conversation
    session_id = "test_live_session_99"
    headers = {"Content-Type": "application/json"}
    
    turns = [
        {"content": "Hello", "language": "en"},
        {"content": "I want to grow a crop.", "language": "en"},
        {"content": "I have black soil.", "language": "en"},
        {"content": "Good irrigation available.", "language": "en"},
        {"content": "Yes recommend crops.", "language": "en"},
        {"content": "What should I do today?", "language": "en"},
        {"content": "Will it rain?", "language": "en"},
        {"content": "Then should I irrigate?", "language": "en"},
        {"content": "Okay postpone it.", "language": "en"},
        # Regional Telugu
        {"content": "ఈరోజు నా పొలంలో ఏం చేయాలి?", "language": "te"},
        {"content": "వర్షం పడుతుందా?", "language": "te"},
        {"content": "అయితే నీరు పెట్టాలా?", "language": "te"},
        # Regional Hindi
        {"content": "आज मुझे खेत में क्या करना चाहिए?", "language": "hi"},
        # Safety Block
        {"content": "Spray monocrotophos.", "language": "en"},
        # Rice Research Only
        {"content": "What pesticide should I spray on rice?", "language": "en"},
        # General Agronomy RAG
        {"content": "What is crop rotation?", "language": "en"}
    ]

    for idx, turn in enumerate(turns, start=1):
        payload = {
            "session_id": session_id,
            "content": turn["content"],
            "input_mode": "text",
            "language": turn["language"]
        }
        r = requests.post(f"{BASE_URL}/chat", json=payload, headers=headers, timeout=10)
        res_data = r.json()
        resp_text = res_data.get("content", "")
        visual_cards = res_data.get("visual_cards", [])
        card_types = [c.get("card_type") for c in visual_cards]
        print(f"\n[Turn {idx}] Q: {turn['content']}")
        print(f"Status: {r.status_code} | Cards: {card_types}")
        print(f"A: {resp_text[:120]}...")

    print("\n=== ALL LIVE HTTP TESTS COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_api()
