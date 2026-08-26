"""
Weather Intelligence Agent — Fetches real-time weather data including wind, rain,
lightning risk, and cyclone alerts from live APIs.
"""

from __future__ import annotations

from datetime import datetime

from app.data.api_clients import (
    fetch_owm_onecall,
    fetch_owm_weather,
    fetch_weather_data,
    get_target_hour_index,
)
from app.models.schemas import AgentStatus, AgentTrace, WeatherReport

# WMO Weather Codes → Lightning risk mapping
# Codes 95-99 indicate thunderstorm activity
THUNDERSTORM_CODES = {95, 96, 99}
RAIN_CODES = {51, 53, 55, 61, 63, 65, 66, 67, 80, 81, 82}
HEAVY_WEATHER_CODES = {71, 73, 75, 77, 85, 86}  # Snow/freezing (unlikely for Indian coast)


def _assess_lightning_risk(weather_code: int | None, rain_prob: float | None) -> str:
    """Deterministic lightning risk from WMO weather code and rain probability."""
    if weather_code in THUNDERSTORM_CODES:
        return "HIGH"
    if rain_prob is not None and rain_prob > 70:
        return "MODERATE"
    if weather_code in RAIN_CODES:
        return "LOW"
    return "LOW"


def _extract_cyclone_alerts(owm_data: dict | None) -> str | None:
    """Extract cyclone/storm alerts from OpenWeatherMap One Call alerts."""
    if not owm_data:
        return None
    alerts = owm_data.get("alerts", [])
    for alert in alerts:
        event = alert.get("event", "").lower()
        if any(kw in event for kw in ["cyclone", "hurricane", "storm", "typhoon", "surge"]):
            return alert.get("description", alert.get("event", "Cyclone Alert Active"))
    return None


async def run_weather_agent(
    lat: float,
    lng: float,
    target_dt: str | None = None,
) -> tuple[WeatherReport, AgentTrace]:
    """
    Execute Weather Intelligence Agent.
    Fetches real data from Open-Meteo + OpenWeatherMap and returns structured report.
    """
    trace = AgentTrace(
        agent_name="Weather Intelligence Agent",
        status=AgentStatus.RUNNING,
        message="Fetching live weather data...",
        started_at=datetime.utcnow().isoformat(),
    )

    try:
        # Fetch from Open-Meteo (primary — no API key needed)
        om_data = await fetch_weather_data(lat, lng)
        hourly = om_data.get("hourly", {})
        times = hourly.get("time", [])
        idx = get_target_hour_index(times, target_dt)

        def _get(key: str) -> float | None:
            vals = hourly.get(key, [])
            return vals[idx] if idx < len(vals) else None

        wind_speed = _get("wind_speed_10m")
        wind_dir = _get("wind_direction_10m")
        wind_gusts = _get("wind_gusts_10m")
        temp = _get("temperature_2m")
        feels_like = _get("apparent_temperature")
        humidity = _get("relative_humidity_2m")
        rain_prob = _get("precipitation_probability")
        rainfall = _get("precipitation")
        visibility = _get("visibility")
        cloud_cover = _get("cloud_cover")
        weather_code = _get("weather_code")

        # Convert visibility from meters to km
        if visibility is not None:
            visibility = round(visibility / 1000, 1)

        # Lightning risk (deterministic)
        wc_int = int(weather_code) if weather_code is not None else None
        lightning = _assess_lightning_risk(wc_int, rain_prob)

        # Try OpenWeatherMap for additional alerts
        owm_data = await fetch_owm_onecall(lat, lng)
        cyclone = _extract_cyclone_alerts(owm_data)

        # Extract OWM weather alerts
        alerts = []
        if owm_data and "alerts" in owm_data:
            for a in owm_data["alerts"]:
                alerts.append(a.get("event", "Alert"))

        # Weather description from OWM current
        owm_current = await fetch_owm_weather(lat, lng)
        description = None
        if owm_current and "weather" in owm_current:
            description = owm_current["weather"][0].get("description", "").title()

        report = WeatherReport(
            wind_speed_kmh=round(wind_speed, 1) if wind_speed else None,
            wind_direction_deg=wind_dir,
            wind_gusts_kmh=round(wind_gusts, 1) if wind_gusts else None,
            temperature_c=round(temp, 1) if temp else None,
            feels_like_c=round(feels_like, 1) if feels_like else None,
            humidity_pct=humidity,
            rain_probability_pct=rain_prob,
            rainfall_mm=round(rainfall, 1) if rainfall else None,
            visibility_km=visibility,
            cloud_cover_pct=cloud_cover,
            lightning_risk=lightning,
            cyclone_alert=cyclone,
            weather_description=description,
            alerts=alerts,
            data_source="Open-Meteo + OpenWeatherMap (live)",
        )

        trace.status = AgentStatus.COMPLETED
        trace.message = (
            f"Weather data retrieved: Wind {report.wind_speed_kmh} km/h, "
            f"Rain {report.rain_probability_pct}%, Lightning: {lightning}"
        )
        trace.data = report.model_dump()
        trace.completed_at = datetime.utcnow().isoformat()

    except Exception as e:
        report = WeatherReport(data_source=f"error: {str(e)}")
        trace.status = AgentStatus.ERROR
        trace.message = f"Weather Agent error: {str(e)}"
        trace.completed_at = datetime.utcnow().isoformat()

    return report, trace
