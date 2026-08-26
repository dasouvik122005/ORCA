"""
Ocean Intelligence Agent — Fetches real-time marine data including wave height,
swell, ocean currents, SST, and sea state classification.
"""

from __future__ import annotations

from datetime import datetime

from app.config import SEA_STATE_SCALE
from app.data.api_clients import (
    fetch_marine_data,
    fetch_weather_data,
    get_target_hour_index,
)
from app.models.schemas import AgentStatus, AgentTrace, OceanReport


def _classify_sea_state(wave_height: float | None) -> tuple[int | None, str | None]:
    """Classify sea state using the Douglas Sea State Scale."""
    if wave_height is None:
        return None, None
    for code, info in sorted(SEA_STATE_SCALE.items()):
        if wave_height <= info["wave_height_max"]:
            return code, info["description"]
    return 9, "Phenomenal"


async def _fetch_sst(lat: float, lng: float) -> float | None:
    """
    Fetch SST using Open-Meteo weather API with soil_temperature_0cm + sea cell selection.
    This is the recommended workaround since Open-Meteo Marine API doesn't provide SST directly.
    """
    try:
        import httpx
        params = {
            "latitude": lat,
            "longitude": lng,
            "hourly": "soil_temperature_0cm",
            "forecast_days": 1,
            "cell_selection": "sea",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
            resp.raise_for_status()
            data = resp.json()
            temps = data.get("hourly", {}).get("soil_temperature_0cm", [])
            valid = [t for t in temps if t is not None]
            if valid:
                return round(sum(valid) / len(valid), 1)
    except Exception:
        pass
    return None


async def run_ocean_agent(
    lat: float,
    lng: float,
    target_dt: str | None = None,
) -> tuple[OceanReport, AgentTrace]:
    """
    Execute Ocean Intelligence Agent.
    Fetches real marine data from Open-Meteo Marine API and returns structured report.
    """
    trace = AgentTrace(
        agent_name="Ocean Intelligence Agent",
        status=AgentStatus.RUNNING,
        message="Fetching live marine and ocean data...",
        started_at=datetime.utcnow().isoformat(),
    )

    try:
        # Fetch marine data (waves, swell, currents)
        marine_data = await fetch_marine_data(lat, lng)
        hourly = marine_data.get("hourly", {})
        times = hourly.get("time", [])
        idx = get_target_hour_index(times, target_dt)

        def _get(key: str) -> float | None:
            vals = hourly.get(key, [])
            return vals[idx] if idx < len(vals) else None

        wave_height = _get("wave_height")
        swell_height = _get("swell_wave_height")
        wind_wave_height = _get("wind_wave_height")
        wave_period = _get("wave_period")
        wave_dir = _get("wave_direction")
        swell_period = _get("swell_wave_period")
        current_vel = _get("ocean_current_velocity")
        current_dir = _get("ocean_current_direction")

        # Classify sea state (deterministic)
        sea_code, sea_desc = _classify_sea_state(wave_height)

        # Fetch SST
        sst = await _fetch_sst(lat, lng)

        report = OceanReport(
            wave_height_m=round(wave_height, 2) if wave_height else None,
            swell_wave_height_m=round(swell_height, 2) if swell_height else None,
            wind_wave_height_m=round(wind_wave_height, 2) if wind_wave_height else None,
            wave_period_s=round(wave_period, 1) if wave_period else None,
            wave_direction_deg=wave_dir,
            swell_wave_period_s=round(swell_period, 1) if swell_period else None,
            ocean_current_velocity_ms=round(current_vel, 2) if current_vel else None,
            ocean_current_direction_deg=current_dir,
            sst_c=sst,
            sea_state_code=sea_code,
            sea_state_description=sea_desc,
            data_source="Open-Meteo Marine API (live)",
        )

        trace.status = AgentStatus.COMPLETED
        trace.message = (
            f"Ocean data retrieved: Waves {report.wave_height_m}m, "
            f"SST {report.sst_c}°C, Sea State: {sea_desc}"
        )
        trace.data = report.model_dump()
        trace.completed_at = datetime.utcnow().isoformat()

    except Exception as e:
        report = OceanReport(data_source=f"error: {str(e)}")
        trace.status = AgentStatus.ERROR
        trace.message = f"Ocean Agent error: {str(e)}"
        trace.completed_at = datetime.utcnow().isoformat()

    return report, trace
