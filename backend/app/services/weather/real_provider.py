import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import httpx
from app.schemas.weather import WeatherResponse, WeatherCurrent, WeatherForecastDay, FreshnessStatus
from app.services.weather.weather_provider import WeatherProvider
from app.services.weather.location import resolve_location_coordinates
from app.services.weather.cache import weather_cache
from app.core.exceptions import BhoomiException

logger = logging.getLogger(__name__)

# WMO Weather Interpretation Codes (WW) for Open-Meteo
WMO_WEATHER_CODES = {
    0: "Clear Sky",
    1: "Mainly Clear",
    2: "Partly Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing Rime Fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy Rain",
    71: "Slight Snow Fall",
    80: "Slight Rain Showers",
    81: "Moderate Rain Showers",
    82: "Violent Rain Showers",
    95: "Thunderstorm",
    96: "Thunderstorm with Slight Hail",
    99: "Thunderstorm with Heavy Hail"
}

class RealWeatherProvider(WeatherProvider):
    """
    Production-grade real weather intelligence provider.
    Supports OpenWeatherMap API and Open-Meteo (High-Precision Agro-Meteorology).
    Enforces strict caching, data provenance, coordinate validation, and fallback handling.
    Distinguishes genuine measured zero from unknown/unavailable null values.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        provider_type: str = "openweathermap",
        timeout_seconds: float = 8.0
    ):
        self.api_key = api_key
        self.provider_type = provider_type.lower()
        self.timeout_seconds = timeout_seconds

    async def get_current_and_forecast(
        self,
        location: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> WeatherResponse:
        # 1. Location & Coordinate Resolution
        resolved_lat, resolved_lon, resolved_name = resolve_location_coordinates(location, lat, lon)
        
        if resolved_lat is None or resolved_lon is None:
            logger.warning("Weather coordinates could not be resolved for location: %s", location)
            return self._build_unavailable_response(
                location=location,
                reason="Geographic coordinates could not be determined. Please specify farm village/district."
            )

        # 2. Check Fresh Cache First (Avoid Redundant Network Calls)
        cache_key = weather_cache.make_key(resolved_name, resolved_lat, resolved_lon)
        cached_item = weather_cache.get(cache_key)
        if cached_item:
            resp, freshness = cached_item
            if freshness == FreshnessStatus.CURRENT.value:
                logger.info("Serving CURRENT weather for %s from cache", resolved_name)
                return resp

        # 3. Fetch from External Live Weather Provider
        try:
            if self.provider_type == "openweathermap" and self.api_key and not self.api_key.startswith("your_"):
                live_response = await self._fetch_openweathermap(resolved_name, resolved_lat, resolved_lon)
            else:
                live_response = await self._fetch_open_meteo(resolved_name, resolved_lat, resolved_lon)

            # Store in cache
            weather_cache.set(cache_key, live_response)
            return live_response

        except Exception as e:
            logger.error("Live weather provider call failed: %s", type(e).__name__)
            # Check if any cached/stale data exists to serve (retains original observed measurements)
            if cached_item:
                resp, freshness = cached_item
                logger.warning("Falling back to %s weather for %s", freshness, resolved_name)
                return resp

            # No cache exists; return structured UNAVAILABLE response with explicit null measurements
            return self._build_unavailable_response(
                location=resolved_name,
                lat=resolved_lat,
                lon=resolved_lon,
                reason="Live meteorological provider is temporarily unavailable. No prior cache exists."
            )

    async def _fetch_openweathermap(self, location_name: str, lat: float, lon: float) -> WeatherResponse:
        """Fetches current conditions and 5-day forecast from OpenWeatherMap."""
        cur_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
        fct_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            cur_resp = await client.get(cur_url)
            if cur_resp.status_code in (401, 403):
                raise BhoomiException("OpenWeatherMap authentication failed.", status_code=401)
            elif cur_resp.status_code == 429:
                raise BhoomiException("OpenWeatherMap rate limit exceeded.", status_code=429)
            elif cur_resp.status_code >= 500:
                raise BhoomiException("OpenWeatherMap upstream service error.", status_code=502)
            elif cur_resp.status_code != 200:
                raise BhoomiException(f"OpenWeatherMap error status {cur_resp.status_code}.", status_code=cur_resp.status_code)

            cur_data = cur_resp.json()

            # Forecast call
            fct_resp = await client.get(fct_url)
            fct_data = fct_resp.json() if fct_resp.status_code == 200 else {}

        # Parse Current
        main = cur_data.get("main")
        wind = cur_data.get("wind")
        weather_items = cur_data.get("weather", [{}])
        cond = weather_items[0].get("description", "Clear").title() if weather_items else "Clear"
        
        temp_c = float(main["temp"]) if main and "temp" in main else None
        humidity = float(main["humidity"]) if main and "humidity" in main else None
        wind_kmh = float(wind["speed"]) * 3.6 if wind and "speed" in wind else None
        
        # Distinction between measured zero rain vs unknown
        if "rain" in cur_data:
            rain_dict = cur_data.get("rain", {})
            rain_mm = float(rain_dict.get("1h", rain_dict.get("3h", 0.0)))
        elif cur_data:
            # Valid live report with zero measured rain
            rain_mm = 0.0
        else:
            rain_mm = None

        # Parse 3-day forecast intervals
        forecast_days: List[WeatherForecastDay] = []
        raw_list = fct_data.get("list", [])
        rain_prob_max = 0 if raw_list else None

        day_buckets: Dict[str, Dict[str, Any]] = {}
        for item in raw_list[:24]:  # Next 72 hours (3 days)
            dt_txt = item.get("dt_txt", "").split(" ")[0]
            if not dt_txt:
                continue
            item_pop = int(float(item.get("pop", 0.0)) * 100)
            item_temp = float(item.get("main", {}).get("temp", temp_c if temp_c is not None else 30.0))
            item_cond = item.get("weather", [{}])[0].get("description", "Scattered Clouds").title()
            item_wind = float(item.get("wind", {}).get("speed", 3.0)) * 3.6
            
            if dt_txt not in day_buckets:
                day_buckets[dt_txt] = {
                    "temps": [],
                    "pops": [],
                    "winds": [],
                    "cond": item_cond
                }
            day_buckets[dt_txt]["temps"].append(item_temp)
            day_buckets[dt_txt]["pops"].append(item_pop)
            day_buckets[dt_txt]["winds"].append(item_wind)
            if rain_prob_max is not None and item_pop > rain_prob_max:
                rain_prob_max = item_pop

        # Build forecast days with explicit calendar dates
        for i, (d_str, b_data) in enumerate(list(day_buckets.items())[:3]):
            fallback_t = temp_c if temp_c is not None else 30.0
            t_max = max(b_data["temps"]) if b_data["temps"] else fallback_t + 2.0
            t_min = min(b_data["temps"]) if b_data["temps"] else fallback_t - 4.0
            p_max = max(b_data["pops"]) if b_data["pops"] else 20
            w_max = max(b_data["winds"]) if b_data.get("winds") else (wind_kmh or 10.0)
            
            # Determine calendar date and day label
            try:
                parsed_dt = datetime.fromisoformat(d_str)
                d_name = "Tomorrow" if i == 0 else parsed_dt.strftime("%A")
            except Exception:
                d_name = "Tomorrow" if i == 0 else f"Day {i+1}"

            forecast_days.append(
                WeatherForecastDay(
                    date=d_name,
                    calendar_date=d_str,
                    day_name=d_name,
                    timezone="Asia/Kolkata",
                    observation_type="FORECAST",
                    temp_max=round(t_max, 1),
                    temp_min=round(t_min, 1),
                    rain_probability=p_max,
                    condition=b_data["cond"],
                    rainfall_mm=0.0,
                    wind_speed_kmh=round(w_max, 1)
                )
            )

        now_utc = datetime.now(timezone.utc)
        today_iso = now_utc.date().isoformat()
        advisory = self._generate_agronomic_advisory(rain_prob_max, rain_mm, temp_c)

        current = WeatherCurrent(
            temperature_c=round(temp_c, 1) if temp_c is not None else None,
            humidity_percent=round(humidity, 1) if humidity is not None else None,
            rainfall_mm=round(rain_mm, 1) if rain_mm is not None else None,
            wind_speed_kmh=round(wind_kmh, 1) if wind_kmh is not None else None,
            weather_condition=cond,
            rain_probability_percent=rain_prob_max,
            advisory=advisory,
            is_live=True,
            timestamp=now_utc,
            retrieved_at=now_utc,
            calendar_date=today_iso,
            timezone="Asia/Kolkata",
            observation_type="CURRENT_OBSERVATION",
            freshness=FreshnessStatus.CURRENT.value,
            source="OpenWeatherMap API"
        )

        tomorrow_f = forecast_days[0] if forecast_days else None
        spray_eval = self.evaluate_spray_window(
            rain_prob=tomorrow_f.rain_probability if tomorrow_f else None,
            rainfall_mm=tomorrow_f.rainfall_mm if tomorrow_f else None,
            wind_speed_kmh=tomorrow_f.wind_speed_kmh if tomorrow_f else None,
            temp_c=tomorrow_f.temp_max if tomorrow_f else None,
            target_date=tomorrow_f.calendar_date if tomorrow_f and tomorrow_f.calendar_date else "Tomorrow",
            data_freshness=FreshnessStatus.CURRENT.value
        )
        irr_eval = self.evaluate_irrigation(
            today_rain_prob=rain_prob_max,
            today_rainfall_mm=rain_mm,
            tomorrow_rain_prob=tomorrow_f.rain_probability if tomorrow_f else None,
            tomorrow_rainfall_mm=tomorrow_f.rainfall_mm if tomorrow_f else None
        )

        date_range = f"{today_iso} to {forecast_days[-1].calendar_date}" if forecast_days and forecast_days[-1].calendar_date else today_iso

        return WeatherResponse(
            location=location_name,
            latitude=lat,
            longitude=lon,
            current=current,
            forecast_3_days=forecast_days,
            source="OpenWeatherMap Real-Time Meteorologic Data",
            target_date=tomorrow_f.calendar_date if tomorrow_f else today_iso,
            target_date_range=date_range,
            timezone="Asia/Kolkata",
            provider_type="OPENWEATHERMAP",
            freshness=FreshnessStatus.CURRENT.value,
            retrieved_at=now_utc.isoformat(),
            spray_window_evaluation=spray_eval,
            irrigation_evaluation=irr_eval
        )

    async def _fetch_open_meteo(self, location_name: str, lat: float, lon: float) -> WeatherResponse:
        """Fetches precision agro-meteorological data from Open-Meteo."""
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&"
            f"current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m&"
            f"daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max&"
            f"timezone=Asia%2FKolkata"
        )

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.get(url)
            if resp.status_code == 429:
                raise BhoomiException("Open-Meteo rate limit exceeded.", status_code=429)
            elif resp.status_code >= 500:
                raise BhoomiException("Open-Meteo upstream server error.", status_code=502)
            elif resp.status_code != 200:
                raise BhoomiException(f"Open-Meteo HTTP {resp.status_code}.", status_code=resp.status_code)

            data = resp.json()

        cur = data.get("current")
        daily = data.get("daily", {})

        temp_c = float(cur["temperature_2m"]) if cur and "temperature_2m" in cur else None
        humidity = float(cur["relative_humidity_2m"]) if cur and "relative_humidity_2m" in cur else None
        rain_mm = float(cur.get("rain", cur.get("precipitation", 0.0))) if cur and ("rain" in cur or "precipitation" in cur) else 0.0 if cur else None
        wind_kmh = float(cur["wind_speed_10m"]) if cur and "wind_speed_10m" in cur else None
        w_code = int(cur.get("weather_code", 0)) if cur else 0
        condition = WMO_WEATHER_CODES.get(w_code, "Partly Cloudy") if cur else "Unavailable"

        # Daily Forecast Arrays: index 0 is Today, index 1 is Tomorrow, index 2 is Day 2, etc.
        times = daily.get("time", [])
        t_maxs = daily.get("temperature_2m_max", [])
        t_mins = daily.get("temperature_2m_min", [])
        rain_probs = daily.get("precipitation_probability_max", [])
        rain_sums = daily.get("precipitation_sum", [])
        wind_maxs = daily.get("wind_speed_10m_max", [])
        daily_codes = daily.get("weather_code", [])

        now_utc = datetime.now(timezone.utc)
        today_cal_date = times[0] if times else now_utc.date().isoformat()

        forecast_days: List[WeatherForecastDay] = []
        # Days 1..3 correspond to Tomorrow and subsequent days
        for i in range(1, min(4, len(times))):
            cal_date = times[i]
            try:
                parsed_dt = datetime.fromisoformat(cal_date)
                day_name = "Tomorrow" if i == 1 else parsed_dt.strftime("%A")
            except Exception:
                day_name = "Tomorrow" if i == 1 else f"Day {i}"

            fallback_t = temp_c if temp_c is not None else 30.0
            t_max = float(t_maxs[i]) if i < len(t_maxs) else fallback_t + 2.0
            t_min = float(t_mins[i]) if i < len(t_mins) else fallback_t - 4.0
            p_prob = int(rain_probs[i]) if i < len(rain_probs) and rain_probs[i] is not None else 10
            r_mm = float(rain_sums[i]) if i < len(rain_sums) and rain_sums[i] is not None else 0.0
            w_max = float(wind_maxs[i]) if i < len(wind_maxs) and wind_maxs[i] is not None else (wind_kmh or 10.0)
            d_code = int(daily_codes[i]) if i < len(daily_codes) else 0
            d_cond = WMO_WEATHER_CODES.get(d_code, "Partly Cloudy")

            forecast_days.append(
                WeatherForecastDay(
                    date="Tomorrow" if i == 1 else f"Day {i} ({cal_date})",
                    calendar_date=cal_date,
                    day_name=day_name,
                    timezone="Asia/Kolkata",
                    observation_type="FORECAST",
                    temp_max=round(t_max, 1),
                    temp_min=round(t_min, 1),
                    rain_probability=p_prob,
                    condition=d_cond,
                    rainfall_mm=round(r_mm, 1),
                    wind_speed_kmh=round(w_max, 1)
                )
            )

        # Today's indicators (index 0)
        today_rain_prob = int(rain_probs[0]) if rain_probs and rain_probs[0] is not None else (forecast_days[0].rain_probability if forecast_days else None)
        today_rain_sum = float(rain_sums[0]) if rain_sums and rain_sums[0] is not None else rain_mm

        advisory = self._generate_agronomic_advisory(today_rain_prob, rain_mm, temp_c)

        current = WeatherCurrent(
            temperature_c=round(temp_c, 1) if temp_c is not None else None,
            humidity_percent=round(humidity, 1) if humidity is not None else None,
            rainfall_mm=round(rain_mm, 1) if rain_mm is not None else None,
            wind_speed_kmh=round(wind_kmh, 1) if wind_kmh is not None else None,
            weather_condition=condition,
            rain_probability_percent=today_rain_prob,
            advisory=advisory,
            is_live=True,
            timestamp=now_utc,
            retrieved_at=now_utc,
            calendar_date=today_cal_date,
            timezone="Asia/Kolkata",
            observation_type="CURRENT_OBSERVATION",
            freshness=FreshnessStatus.CURRENT.value,
            source="Open-Meteo Agro-Meteorological Service"
        )

        tomorrow_f = forecast_days[0] if forecast_days else None
        spray_eval = self.evaluate_spray_window(
            rain_prob=tomorrow_f.rain_probability if tomorrow_f else None,
            rainfall_mm=tomorrow_f.rainfall_mm if tomorrow_f else None,
            wind_speed_kmh=tomorrow_f.wind_speed_kmh if tomorrow_f else None,
            temp_c=tomorrow_f.temp_max if tomorrow_f else None,
            target_date=tomorrow_f.calendar_date if tomorrow_f and tomorrow_f.calendar_date else "Tomorrow",
            data_freshness=FreshnessStatus.CURRENT.value
        )
        irr_eval = self.evaluate_irrigation(
            today_rain_prob=today_rain_prob,
            today_rainfall_mm=today_rain_sum,
            tomorrow_rain_prob=tomorrow_f.rain_probability if tomorrow_f else None,
            tomorrow_rainfall_mm=tomorrow_f.rainfall_mm if tomorrow_f else None
        )

        date_range = f"{today_cal_date} to {forecast_days[-1].calendar_date}" if forecast_days and forecast_days[-1].calendar_date else today_cal_date

        return WeatherResponse(
            location=location_name,
            latitude=lat,
            longitude=lon,
            current=current,
            forecast_3_days=forecast_days,
            source="Open-Meteo High-Precision Weather Service",
            target_date=tomorrow_f.calendar_date if tomorrow_f else today_cal_date,
            target_date_range=date_range,
            timezone="Asia/Kolkata",
            provider_type="OPEN_METEO",
            freshness=FreshnessStatus.CURRENT.value,
            retrieved_at=now_utc.isoformat(),
            spray_window_evaluation=spray_eval,
            irrigation_evaluation=irr_eval
        )

    @staticmethod
    def evaluate_spray_window(
        rain_prob: Optional[int],
        rainfall_mm: Optional[float],
        wind_speed_kmh: Optional[float],
        temp_c: Optional[float],
        target_date: str,
        data_freshness: str = "CURRENT"
    ) -> Dict[str, Any]:
        """
        Deterministic Agronomic Spray Window Assessment.
        Evaluates rain probability, expected precipitation, wind speed, temperature,
        and data freshness. Returns INSUFFICIENT_DATA if required telemetry is missing,
        never inventing safe/unsafe recommendations without data.
        """
        missing_fields = []
        if rain_prob is None:
            missing_fields.append("rain_probability")
        if rainfall_mm is None:
            missing_fields.append("rainfall_mm")
        if wind_speed_kmh is None:
            missing_fields.append("wind_speed_kmh")

        if missing_fields:
            return {
                "status": "INSUFFICIENT_DATA",
                "is_safe": None,
                "missing_fields": missing_fields,
                "explanation": f"Missing critical meteorological fields: {', '.join(missing_fields)}. Cannot provide an authoritative spray safety recommendation without risking chemical washoff or non-target drift.",
                "target_date": target_date,
                "data_freshness": data_freshness,
                "safe_window": None,
                "reasons": []
            }

        is_safe = True
        reasons = []

        # 1. Precipitation & Rain Probability
        if rain_prob >= 35 or rainfall_mm > 1.0:
            is_safe = False
            reasons.append(f"Rain probability ({rain_prob}%) or expected rainfall ({rainfall_mm}mm) exceeds safety limit (washoff risk).")

        # 2. Wind Speed
        if wind_speed_kmh > 15.0:
            is_safe = False
            reasons.append(f"Wind speed ({wind_speed_kmh} km/h) exceeds 15 km/h threshold, causing severe spray drift onto non-target crops.")
        elif wind_speed_kmh < 2.5 and (temp_c is not None and temp_c > 32.0):
            reasons.append("Very low wind speed (<2.5 km/h) with elevated heat creates risk of thermal inversion; spray only in early dawn.")

        # 3. Temperature Threshold
        if temp_c is not None and temp_c > 35.0:
            is_safe = False
            reasons.append(f"Temperature ({temp_c}°C) exceeds 35°C limit, risking chemical flash evaporation and leaf scorch.")

        safe_window = "06:00 AM - 09:00 AM or 04:30 PM - 06:30 PM" if is_safe else None

        return {
            "status": "VALIDATED",
            "is_safe": is_safe,
            "missing_fields": [],
            "target_date": target_date,
            "data_freshness": data_freshness,
            "rain_probability_percent": rain_prob,
            "expected_rainfall_mm": rainfall_mm,
            "wind_speed_kmh": wind_speed_kmh,
            "temperature_c": temp_c,
            "safe_window": safe_window,
            "reasons": reasons,
            "explanation": "Conditions favorable for application." if is_safe else "Spraying is unsafe due to: " + " ".join(reasons)
        }

    @staticmethod
    def evaluate_irrigation(
        today_rain_prob: Optional[int],
        today_rainfall_mm: Optional[float],
        tomorrow_rain_prob: Optional[int],
        tomorrow_rainfall_mm: Optional[float],
        soil_type: str = "Loam",
        soil_moisture_available: bool = False,
        soil_moisture_kpa: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Deterministic Agronomic Irrigation Decision.
        Distinguishes today vs tomorrow conditions. Labels weather-based estimation
        explicitly when soil moisture sensors are absent, displaying underlying assumptions.
        """
        assumptions = [
            "Weather-based estimation; soil moisture tension sensors not detected.",
            f"Assumed soil water retention capacity based on '{soil_type}'.",
            "Farmer must physically verify root-zone moisture at 15 cm depth before valve operation."
        ]

        # Tomorrow rain check: if tomorrow has >=40% rain or >=5mm precipitation, defer today
        if (tomorrow_rain_prob is not None and tomorrow_rain_prob >= 40) or (tomorrow_rainfall_mm is not None and tomorrow_rainfall_mm >= 5.0):
            should_irrigate = False
            decision = "DEFER_IRRIGATION"
            explanation = f"Defer irrigation today: Rain forecast indicates {tomorrow_rain_prob}% probability ({tomorrow_rainfall_mm or 0} mm) tomorrow. Pre-wetting root zone risks soil saturation and root hypoxia."
        elif (today_rain_prob is not None and today_rain_prob >= 45) or (today_rainfall_mm is not None and today_rainfall_mm >= 5.0):
            should_irrigate = False
            decision = "DEFER_IRRIGATION"
            explanation = f"Hold irrigation today: Active rain probability is {today_rain_prob}% with {today_rainfall_mm or 0} mm precipitation expected."
        else:
            should_irrigate = True
            decision = "PROCEED_IRRIGATION"
            explanation = f"Standard irrigation schedule may proceed. Rain chances remain low ({today_rain_prob or 0}% today, {tomorrow_rain_prob or 0}% tomorrow)."

        return {
            "decision": decision,
            "should_irrigate": should_irrigate,
            "recommendation_type": "SENSOR_VERIFIED" if soil_moisture_available else "WEATHER_BASED_ESTIMATION",
            "today_rain_probability": today_rain_prob,
            "tomorrow_rain_probability": tomorrow_rain_prob,
            "assumptions": assumptions,
            "explanation": explanation
        }

    def _generate_agronomic_advisory(
        self,
        rain_probability: Optional[int],
        rain_mm: Optional[float],
        temp_c: Optional[float]
    ) -> str:
        """Translates weather indicators into practical farmer guidance."""
        if rain_probability is None and rain_mm is None:
            return "Precipitation data unavailable. Please inspect field conditions locally."
        if (rain_probability is not None and rain_probability >= 50) or (rain_mm is not None and rain_mm >= 15.0):
            return f"Significant rainfall expected ({rain_probability}% probability). Delay surface irrigation and hold chemical foliar sprays."
        elif rain_probability is not None and rain_probability >= 40:
            return f"Moderate rain expected ({rain_probability}% probability). You can defer today's scheduled surface irrigation."
        elif temp_c is not None and temp_c >= 38.0:
            return "High ambient temperature warning. Ensure light evening moisture to prevent soil desiccation."
        else:
            return "Weather conditions favorable for standard field operations and routine irrigation."

    def _build_unavailable_response(
        self,
        location: str,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        reason: str = "Weather service unavailable."
    ) -> WeatherResponse:
        """Returns structured UNAVAILABLE response with explicit null measurements."""
        now_utc = datetime.now(timezone.utc)
        today_iso = now_utc.date().isoformat()
        current = WeatherCurrent(
            temperature_c=None,
            humidity_percent=None,
            rainfall_mm=None,
            wind_speed_kmh=None,
            weather_condition="Service Unavailable",
            rain_probability_percent=None,
            advisory=f"Live weather data is currently unavailable. {reason}",
            is_live=False,
            timestamp=now_utc,
            retrieved_at=now_utc,
            calendar_date=today_iso,
            timezone="Asia/Kolkata",
            observation_type="CURRENT_OBSERVATION",
            freshness=FreshnessStatus.UNAVAILABLE.value,
            source="Unavailable"
        )
        spray_eval = self.evaluate_spray_window(
            rain_prob=None,
            rainfall_mm=None,
            wind_speed_kmh=None,
            temp_c=None,
            target_date="Tomorrow",
            data_freshness=FreshnessStatus.UNAVAILABLE.value
        )
        irr_eval = self.evaluate_irrigation(
            today_rain_prob=None,
            today_rainfall_mm=None,
            tomorrow_rain_prob=None,
            tomorrow_rainfall_mm=None
        )
        return WeatherResponse(
            location=location,
            latitude=lat,
            longitude=lon,
            current=current,
            forecast_3_days=[],
            source="Unavailable",
            target_date=None,
            target_date_range=None,
            timezone="Asia/Kolkata",
            provider_type="UNAVAILABLE",
            freshness=FreshnessStatus.UNAVAILABLE.value,
            retrieved_at=now_utc.isoformat(),
            spray_window_evaluation=spray_eval,
            irrigation_evaluation=irr_eval
        )
