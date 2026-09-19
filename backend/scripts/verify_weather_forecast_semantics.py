"""
BHOOMI — Weather Forecast Semantic Validation Script
Executes all 5 queries in English and Telugu:
1. Current weather query ("What is the current weather?", "ప్రస్తుత వాతావరణం ఎలా ఉంది?")
2. Tomorrow rain query ("Will it rain tomorrow?", "రేపు వర్షం పడుతుందా?")
3. Tomorrow spray query ("Can I spray tomorrow?", "రేపు మందు పిచికారీ చేయవచ్చా?")
4. Temperature query ("What is the temperature in Warangal?", "వరంగల్‌లో ఉష్ణోగ్రత ఎంత?")
5. Irrigation query ("Should I irrigate my crops tomorrow?", "రేపు పంటకు నీరు పెట్టాలా?")

Reports:
- Exact provider calls
- Forecast timestamps
- Response metadata
"""

import os
import sys
import json
import asyncio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.agents.orchestrator import BhoomiAgentOrchestrator
from app.services.memory.digital_twin import DigitalTwinContext
from app.services.weather.real_provider import RealWeatherProvider

async def run_weather_validation():
    print("=" * 80)
    print("TASK 1: WEATHER FORECAST SEMANTIC VALIDATION")
    print("=" * 80)

    # 1. Inspect direct provider calls first
    provider = RealWeatherProvider()
    print("\n--- 1. Direct RealWeatherProvider Inspection ---")
    print(f"Active Provider: {provider.__class__.__name__} (Engine: Open-Meteo & OpenWeatherMap fallback)")

    weather_res = await provider.get_current_and_forecast("Warangal, Telangana", lat=17.9784, lon=79.5941)
    curr = weather_res.current
    print(f"Current Observation: temp={curr.temperature_c}°C, humidity={curr.humidity_percent}%, wind={curr.wind_speed_kmh} km/h, condition='{curr.weather_condition}', rain={curr.rainfall_mm}mm, timestamp={curr.timestamp}")

    print(f"Forecast Daily Count: {len(weather_res.forecast_3_days)} days")
    for idx, df in enumerate(weather_res.forecast_3_days):
        print(f"  Day {idx} [{df.date}]: max_temp={df.temp_max}°C, min_temp={df.temp_min}°C, rain_prob={df.rain_probability}%, rain_mm={df.rainfall_mm}mm, wind={df.wind_speed_kmh} km/h, condition='{df.condition}'")

    # 2. Test semantic queries through BhoomiAgentOrchestrator
    twin = DigitalTwinContext(
        farmer_id="farmer_weather_eval",
        farmer_name="Evaluator Farmer",
        state="Telangana",
        district="Warangal",
        location="Warangal, Telangana",
        latitude=17.9784,
        longitude=79.5941,
        total_land_acres=3.0,
        active_crops=[{"crop_name": "chilli", "acres": 3.0, "stage": "flowering"}],
        soil_type="Black Cotton Soil"
    )

    test_queries = [
        # (Category, English Query, Telugu Query)
        ("1. Current Weather", "What is the current weather?", "ప్రస్తుత వాతావరణం ఎలా ఉంది?"),
        ("2. Tomorrow Rain", "Will it rain tomorrow?", "రేపు వర్షం పడుతుందా?"),
        ("3. Tomorrow Spray", "Can I spray tomorrow?", "రేపు మందు పిచికారీ చేయవచ్చా?"),
        ("4. Temperature", "What is the temperature in Warangal?", "వరంగల్‌లో ఉష్ణోగ్రత ఎంత?"),
        ("5. Irrigation", "Should I irrigate my crops tomorrow?", "రేపు పంటకు నీరు పెట్టాలా?")
    ]

    results_report = []

    for cat, en_q, te_q in test_queries:
        print(f"\n--- Category: {cat} ---")
        
        # Test English
        en_res = await BhoomiAgentOrchestrator.orchestrate(
            user_text=en_q,
            session_id=f"sess_en_{cat[:1]}",
            farmer_id=twin.farmer_id,
            farm_id="farm_weather_01",
            context=twin,
            language="en"
        )
        en_cards = [c.get("card_type", c.get("type", "unknown")) for c in en_res.visual_cards]
        print(f"[EN Query]: \"{en_q}\"")
        print(f"  Visual Cards: {en_cards}")
        print(f"  Response: {en_res.response_text}")

        # Test Telugu
        te_res = await BhoomiAgentOrchestrator.orchestrate(
            user_text=te_q,
            session_id=f"sess_te_{cat[:1]}",
            farmer_id=twin.farmer_id,
            farm_id="farm_weather_01",
            context=twin,
            language="te"
        )
        te_cards = [c.get("card_type", c.get("type", "unknown")) for c in te_res.visual_cards]
        print(f"[TE Query]: \"{te_q}\"")
        print(f"  Visual Cards: {te_cards}")
        print(f"  Response: {te_res.response_text}")

        results_report.append({
            "category": cat,
            "en": {"query": en_q, "cards": en_cards, "response": en_res.response_text},
            "te": {"query": te_q, "cards": te_cards, "response": te_res.response_text}
        })

    with open(os.path.join(REPO_ROOT, "weather_forecast_verification.json"), "w", encoding="utf-8") as f:
        json.dump(results_report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("TASK 1 VERIFICATION COMPLETED — Full results saved to weather_forecast_verification.json")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_weather_validation())
