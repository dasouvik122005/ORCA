"""
Risk Assessment Agent — Deterministic risk scoring engine.
NOT LLM-based. Uses configurable thresholds and weighted scoring.
All risk calculations are transparent and reproducible.
"""

from __future__ import annotations

from datetime import datetime

from app.config import RISK_LEVELS, RISK_THRESHOLDS, RISK_WEIGHTS
from app.models.schemas import (
    AgentStatus,
    AgentTrace,
    OceanReport,
    RiskFactorScore,
    RiskLevel,
    RiskScore,
    WeatherReport,
    GeospatialReport,
)


def _score_wave_risk(wave_height: float | None) -> tuple[float, str]:
    """Deterministic wave risk scoring."""
    if wave_height is None:
        return 30, "No wave data — moderate caution assumed"
    if wave_height >= RISK_THRESHOLDS["wave_height_extreme"]:
        return 100, f"Extreme wave height ({wave_height}m ≥ {RISK_THRESHOLDS['wave_height_extreme']}m)"
    if wave_height >= RISK_THRESHOLDS["wave_height_high"]:
        return 80, f"High wave height ({wave_height}m ≥ {RISK_THRESHOLDS['wave_height_high']}m)"
    if wave_height >= RISK_THRESHOLDS["wave_height_moderate"]:
        return 55, f"Moderate wave height ({wave_height}m)"
    if wave_height >= RISK_THRESHOLDS["wave_height_low"]:
        return 30, f"Low wave height ({wave_height}m)"
    return 10, f"Calm seas ({wave_height}m)"


def _score_wind_risk(wind_speed: float | None) -> tuple[float, str]:
    """Deterministic wind risk scoring."""
    if wind_speed is None:
        return 30, "No wind data — moderate caution assumed"
    if wind_speed >= RISK_THRESHOLDS["wind_speed_extreme"]:
        return 100, f"Extreme wind ({wind_speed} km/h ≥ {RISK_THRESHOLDS['wind_speed_extreme']} km/h)"
    if wind_speed >= RISK_THRESHOLDS["wind_speed_high"]:
        return 80, f"High wind speed ({wind_speed} km/h)"
    if wind_speed >= RISK_THRESHOLDS["wind_speed_moderate"]:
        return 55, f"Moderate wind ({wind_speed} km/h)"
    if wind_speed >= RISK_THRESHOLDS["wind_speed_low"]:
        return 30, f"Light-moderate wind ({wind_speed} km/h)"
    return 10, f"Light winds ({wind_speed} km/h)"


def _score_weather_risk(
    rain_prob: float | None,
    visibility: float | None,
) -> tuple[float, str]:
    """Deterministic weather (rain + visibility) risk scoring."""
    score = 0
    details = []

    if rain_prob is not None:
        if rain_prob >= 80:
            score += 70
            details.append(f"Very high rain probability ({rain_prob}%)")
        elif rain_prob >= 60:
            score += 50
            details.append(f"High rain probability ({rain_prob}%)")
        elif rain_prob >= 40:
            score += 30
            details.append(f"Moderate rain probability ({rain_prob}%)")
        else:
            score += 10
            details.append(f"Low rain probability ({rain_prob}%)")
    else:
        score += 20
        details.append("No precipitation data")

    if visibility is not None and visibility < RISK_THRESHOLDS["visibility_poor"]:
        score += 20
        details.append(f"Poor visibility ({visibility} km)")

    return min(score, 100), "; ".join(details)


def _score_lightning_risk(lightning: str | None) -> tuple[float, str]:
    """Deterministic lightning risk scoring."""
    if lightning == "HIGH":
        return 90, "High lightning risk — thunderstorm activity detected"
    if lightning == "MODERATE":
        return 55, "Moderate lightning risk — thunderstorm possible"
    return 10, "Low lightning risk"


def _score_cyclone_risk(cyclone_alert: str | None) -> tuple[float, str]:
    """Deterministic cyclone risk scoring."""
    if cyclone_alert:
        return 100, f"CYCLONE ALERT ACTIVE: {cyclone_alert}"
    return 0, "No cyclone alert"


def _score_boundary_risk(geospatial: GeospatialReport | None) -> tuple[float, str]:
    """Deterministic boundary/geofencing risk scoring."""
    if geospatial is None:
        return 0, "No geospatial data"

    score = 0
    details = []

    if geospatial.within_eez is False:
        score += 80
        details.append("Outside India's EEZ")

    if geospatial.restricted_zones_nearby:
        score += 60
        details.append(f"Near restricted zone: {geospatial.restricted_zones_nearby[0]}")

    if geospatial.marine_protected_areas:
        score += 40
        details.append(f"Near MPA: {geospatial.marine_protected_areas[0]}")

    if geospatial.boundary_warning:
        score += 30
        details.append(geospatial.boundary_warning)

    return min(score, 100), "; ".join(details) if details else "No boundary concerns"


def _get_risk_level(score: float) -> tuple[RiskLevel, str, str, str]:
    """Map score to risk level, label, emoji, and color."""
    for level_key, info in RISK_LEVELS.items():
        if info["min"] <= score <= info["max"]:
            return RiskLevel(level_key), info["label"], info["emoji"], info["color"]
    return RiskLevel.EXTREME_RISK, "Extreme Risk", "🔴", "#e74c3c"


def _vessel_recommendation(score: float, primary_hazard: str) -> str:
    """Generate vessel-type-specific recommendation."""
    if score >= 81:
        return (
            "🚫 ALL VESSELS: Do NOT venture into the sea. "
            f"Primary danger: {primary_hazard}. "
            "Wait for conditions to improve."
        )
    if score >= 61:
        return (
            f"⚠ NOT RECOMMENDED for small fishing vessels (< 15m). "
            f"Large vessels may proceed with extreme caution. "
            f"Primary concern: {primary_hazard}."
        )
    if score >= 31:
        return (
            f"⚡ CAUTION for all vessels. Small boats should stay close to shore. "
            f"Monitor: {primary_hazard}."
        )
    return "✅ Conditions are generally favorable for fishing. Standard safety precautions apply."


async def run_risk_agent(
    weather: WeatherReport | None = None,
    ocean: OceanReport | None = None,
    geospatial: GeospatialReport | None = None,
) -> tuple[RiskScore, AgentTrace]:
    """
    Execute Risk Assessment Agent.
    Combines all hazard data into a weighted risk score using deterministic functions.
    """
    trace = AgentTrace(
        agent_name="Risk Assessment Agent",
        status=AgentStatus.RUNNING,
        message="Calculating composite risk score from all agent data...",
        started_at=datetime.utcnow().isoformat(),
    )

    try:
        factors: list[RiskFactorScore] = []

        # Wave risk
        wave_score, wave_detail = _score_wave_risk(
            ocean.wave_height_m if ocean else None
        )
        factors.append(RiskFactorScore(
            factor="Wave Height",
            score=wave_score,
            weight=RISK_WEIGHTS["wave"],
            weighted_score=round(wave_score * RISK_WEIGHTS["wave"], 1),
            detail=wave_detail,
        ))

        # Wind risk
        wind_score, wind_detail = _score_wind_risk(
            weather.wind_speed_kmh if weather else None
        )
        factors.append(RiskFactorScore(
            factor="Wind Speed",
            score=wind_score,
            weight=RISK_WEIGHTS["wind"],
            weighted_score=round(wind_score * RISK_WEIGHTS["wind"], 1),
            detail=wind_detail,
        ))

        # Weather (rain + visibility) risk
        weather_score, weather_detail = _score_weather_risk(
            weather.rain_probability_pct if weather else None,
            weather.visibility_km if weather else None,
        )
        factors.append(RiskFactorScore(
            factor="Weather Conditions",
            score=weather_score,
            weight=RISK_WEIGHTS["weather"],
            weighted_score=round(weather_score * RISK_WEIGHTS["weather"], 1),
            detail=weather_detail,
        ))

        # Lightning risk
        lightning_score, lightning_detail = _score_lightning_risk(
            weather.lightning_risk if weather else None
        )
        factors.append(RiskFactorScore(
            factor="Lightning",
            score=lightning_score,
            weight=RISK_WEIGHTS["lightning"],
            weighted_score=round(lightning_score * RISK_WEIGHTS["lightning"], 1),
            detail=lightning_detail,
        ))

        # Cyclone risk
        cyclone_score, cyclone_detail = _score_cyclone_risk(
            weather.cyclone_alert if weather else None
        )
        factors.append(RiskFactorScore(
            factor="Cyclone",
            score=cyclone_score,
            weight=RISK_WEIGHTS["cyclone"],
            weighted_score=round(cyclone_score * RISK_WEIGHTS["cyclone"], 1),
            detail=cyclone_detail,
        ))

        # Boundary/geofencing risk
        boundary_score, boundary_detail = _score_boundary_risk(geospatial)
        factors.append(RiskFactorScore(
            factor="Maritime Boundaries",
            score=boundary_score,
            weight=RISK_WEIGHTS["boundary"],
            weighted_score=round(boundary_score * RISK_WEIGHTS["boundary"], 1),
            detail=boundary_detail,
        ))

        # Compute final weighted score
        final_score = sum(f.weighted_score for f in factors)
        final_score = round(min(max(final_score, 0), 100), 1)

        # Find primary hazard
        primary = max(factors, key=lambda f: f.score)

        # Map to risk level
        risk_level, risk_label, risk_emoji, risk_color = _get_risk_level(final_score)

        # Vessel recommendation
        vessel_rec = _vessel_recommendation(final_score, primary.factor)

        result = RiskScore(
            final_score=final_score,
            risk_level=risk_level,
            risk_label=risk_label,
            risk_emoji=risk_emoji,
            risk_color=risk_color,
            primary_hazard=primary.factor,
            primary_hazard_score=primary.score,
            factor_scores=factors,
            vessel_recommendation=vessel_rec,
        )

        trace.status = AgentStatus.COMPLETED
        trace.message = (
            f"Risk Score: {final_score}/100 ({risk_emoji} {risk_label}) | "
            f"Primary Hazard: {primary.factor} ({primary.score}/100)"
        )
        trace.data = result.model_dump()
        trace.completed_at = datetime.utcnow().isoformat()

    except Exception as e:
        result = RiskScore(
            final_score=50,
            risk_level=RiskLevel.CAUTION,
            risk_label="Caution",
            risk_emoji="🟡",
            risk_color="#f1c40f",
            primary_hazard="Unknown",
            primary_hazard_score=50,
            vessel_recommendation="Unable to compute full risk — exercise caution",
        )
        trace.status = AgentStatus.ERROR
        trace.message = f"Risk Agent error: {str(e)}"
        trace.completed_at = datetime.utcnow().isoformat()

    return result, trace
