"""
ORCA API Clients — Live HTTP clients for all external data sources.
No mock data. Every response comes from real API calls.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from app.config import (
    CACHE_TTL,
    OPEN_METEO_MARINE_URL,
    OPEN_METEO_WEATHER_URL,
    OPENWEATHERMAP_API_KEY,
    OPENWEATHERMAP_ONECALL_URL,
    OPENWEATHERMAP_WEATHER_URL,
)


# --- Simple in-memory cache (30-min TTL) ---
_cache: dict[str, tuple[float, Any]] = {}


def _get_cached(key: str) -> Optional[Any]:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
        del _cache[key]
    return None


def _set_cached(key: str, data: Any) -> None:
    _cache[key] = (time.time(), data)


# --- Open-Meteo Marine API (no API key required) ---

async def fetch_marine_data(
    lat: float,
    lng: float,
    forecast_days: int = 3,
) -> dict:
    """Fetch wave, swell, and ocean current data from Open-Meteo Marine API."""
    cache_key = f"marine:{lat:.2f}:{lng:.2f}:{forecast_days}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": ",".join([
            "wave_height",
            "wave_direction",
            "wave_period",
            "wind_wave_height",
            "wind_wave_direction",
            "wind_wave_period",
            "swell_wave_height",
            "swell_wave_direction",
            "swell_wave_period",
            "ocean_current_velocity",
            "ocean_current_direction",
        ]),
        "forecast_days": forecast_days,
        "timezone": "auto",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(OPEN_METEO_MARINE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        _set_cached(cache_key, data)
        return data


# --- Open-Meteo Weather API (no API key required) ---

async def fetch_weather_data(
    lat: float,
    lng: float,
    forecast_days: int = 3,
) -> dict:
    """Fetch weather forecast data from Open-Meteo Weather API."""
    cache_key = f"weather:{lat:.2f}:{lng:.2f}:{forecast_days}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation_probability",
            "precipitation",
            "rain",
            "weather_code",
            "cloud_cover",
            "visibility",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ]),
        "forecast_days": forecast_days,
        "timezone": "auto",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(OPEN_METEO_WEATHER_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        _set_cached(cache_key, data)
        return data


# --- Open-Meteo Weather API — SST grid for PFZ analysis ---

async def fetch_sst_grid(
    center_lat: float,
    center_lng: float,
    radius_deg: float = 0.5,
    grid_step: float = 0.1,
) -> list[dict]:
    """
    Fetch SST (via soil_temperature_0cm with sea cells) for a grid of points.
    Used by PFZ Agent for real-time fishing zone identification.
    """
    points = []
    lat = center_lat - radius_deg
    while lat <= center_lat + radius_deg:
        lng = center_lng - radius_deg
        while lng <= center_lng + radius_deg:
            points.append((round(lat, 2), round(lng, 2)))
            lng += grid_step
        lat += grid_step

    results = []
    async with httpx.AsyncClient(timeout=20.0) as client:
        for plat, plng in points:
            cache_key = f"sst:{plat}:{plng}"
            cached = _get_cached(cache_key)
            if cached:
                results.append(cached)
                continue

            params = {
                "latitude": plat,
                "longitude": plng,
                "hourly": "soil_temperature_0cm",
                "forecast_days": 1,
                "cell_selection": "sea",
            }
            try:
                resp = await client.get(OPEN_METEO_WEATHER_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                hourly = data.get("hourly", {})
                temps = hourly.get("soil_temperature_0cm", [])
                valid = [t for t in temps if t is not None]
                sst = sum(valid) / len(valid) if valid else None
                point = {"lat": plat, "lng": plng, "sst": sst}
                _set_cached(cache_key, point)
                results.append(point)
            except Exception:
                results.append({"lat": plat, "lng": plng, "sst": None})

    return results


# --- OpenWeatherMap API (API key required) ---

async def fetch_owm_weather(lat: float, lng: float) -> Optional[dict]:
    """Fetch current weather from OpenWeatherMap (free tier)."""
    if not OPENWEATHERMAP_API_KEY or OPENWEATHERMAP_API_KEY.startswith("your_"):
        return None

    cache_key = f"owm:{lat:.2f}:{lng:.2f}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    params = {
        "lat": lat,
        "lon": lng,
        "appid": OPENWEATHERMAP_API_KEY,
        "units": "metric",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(OPENWEATHERMAP_WEATHER_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            _set_cached(cache_key, data)
            return data
        except Exception:
            return None


async def fetch_owm_onecall(lat: float, lng: float) -> Optional[dict]:
    """Fetch One Call 3.0 data (alerts, hourly, daily) from OpenWeatherMap."""
    if not OPENWEATHERMAP_API_KEY or OPENWEATHERMAP_API_KEY.startswith("your_"):
        return None

    cache_key = f"owm_onecall:{lat:.2f}:{lng:.2f}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    params = {
        "lat": lat,
        "lon": lng,
        "appid": OPENWEATHERMAP_API_KEY,
        "units": "metric",
        "exclude": "minutely",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(OPENWEATHERMAP_ONECALL_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            _set_cached(cache_key, data)
            return data
        except Exception:
            return None


def get_target_hour_index(hourly_times: list[str], target_dt: Optional[str] = None) -> int:
    """
    Find the index in hourly data arrays that best matches the target datetime.
    If no target, returns the current/next hour.
    """
    if not hourly_times:
        return 0

    now = datetime.utcnow()
    if target_dt:
        try:
            target = datetime.fromisoformat(target_dt.replace("Z", "+00:00").replace("+00:00", ""))
        except ValueError:
            target = now + timedelta(hours=12)  # Default to ~tomorrow morning
    else:
        target = now

    best_idx = 0
    best_diff = float("inf")
    for i, t_str in enumerate(hourly_times):
        try:
            t = datetime.fromisoformat(t_str)
            diff = abs((t - target).total_seconds())
            if diff < best_diff:
                best_diff = diff
                best_idx = i
        except ValueError:
            continue

    return best_idx
