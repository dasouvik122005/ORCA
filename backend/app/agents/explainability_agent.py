"""
Explainability & Response Agent — Uses LLM to generate human-readable,
multilingual explanations of ORCA's recommendations.

The LLM ONLY explains results. All risk calculations are deterministic.
"""

from __future__ import annotations

from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.models.schemas import (
    AgentStatus,
    AgentTrace,
    GeospatialReport,
    HistoricalReport,
    Intent,
    Language,
    OceanReport,
    PFZReport,
    RiskScore,
    WeatherReport,
)

SYSTEM_PROMPT = """You are ORCA's Explainability Agent — a marine safety communication specialist.

Your SOLE job is to explain recommendations that have ALREADY been computed by deterministic risk engines.
You do NOT calculate risk. You do NOT guess safety levels. You EXPLAIN the data.

Rules:
1. ALWAYS respond in the language specified (en/hi/bn).
2. Be concise but thorough — fishermen need clear, actionable advice.
3. Reference specific data points (wave height, wind speed, etc.).
4. Use the risk score and level that were already calculated — do NOT override them.
5. For Bengali (bn), use natural Bengali script (বাংলা).
6. For Hindi (hi), use natural Devanagari script (हिंदी).
7. Structure your response with:
   - A clear safety verdict first
   - Key data points supporting the verdict
   - Specific actionable recommendation
   - Any additional warnings
8. Use emoji sparingly but effectively for quick scanning.
"""


def _build_context(
    intent: Intent,
    weather: WeatherReport | None,
    ocean: OceanReport | None,
    risk: RiskScore | None,
    geospatial: GeospatialReport | None,
    pfz: PFZReport | None,
    historical: HistoricalReport | None = None,
    user_query: str = "",
) -> str:
    """Build a structured context string for the LLM from all agent findings."""
    parts = [f"USER QUERY: {user_query}", f"INTENT: {intent.value}", ""]

    if risk:
        parts.append("=== RISK ASSESSMENT (Deterministic — DO NOT OVERRIDE) ===")
        parts.append(f"Final Risk Score: {risk.final_score}/100")
        parts.append(f"Risk Level: {risk.risk_emoji} {risk.risk_label}")
        parts.append(f"Primary Hazard: {risk.primary_hazard} (score: {risk.primary_hazard_score})")
        parts.append(f"Vessel Recommendation: {risk.vessel_recommendation}")
        for f in risk.factor_scores:
            parts.append(f"  - {f.factor}: {f.score}/100 — {f.detail}")
        parts.append("")

    if weather:
        parts.append("=== WEATHER DATA (Live) ===")
        if weather.wind_speed_kmh is not None:
            parts.append(f"Wind: {weather.wind_speed_kmh} km/h (gusts: {weather.wind_gusts_kmh})")
        if weather.rain_probability_pct is not None:
            parts.append(f"Rain Probability: {weather.rain_probability_pct}%")
        if weather.temperature_c is not None:
            parts.append(f"Temperature: {weather.temperature_c}°C")
        if weather.visibility_km is not None:
            parts.append(f"Visibility: {weather.visibility_km} km")
        if weather.lightning_risk:
            parts.append(f"Lightning Risk: {weather.lightning_risk}")
        if weather.cyclone_alert:
            parts.append(f"⚠ CYCLONE ALERT: {weather.cyclone_alert}")
        if weather.weather_description:
            parts.append(f"Conditions: {weather.weather_description}")
        parts.append("")

    if ocean:
        parts.append("=== OCEAN DATA (Live) ===")
        if ocean.wave_height_m is not None:
            parts.append(f"Wave Height: {ocean.wave_height_m}m")
        if ocean.swell_wave_height_m is not None:
            parts.append(f"Swell: {ocean.swell_wave_height_m}m")
        if ocean.sst_c is not None:
            parts.append(f"Sea Surface Temp: {ocean.sst_c}°C")
        if ocean.sea_state_description:
            parts.append(f"Sea State: {ocean.sea_state_description} (Code {ocean.sea_state_code})")
        if ocean.ocean_current_velocity_ms is not None:
            parts.append(f"Current: {ocean.ocean_current_velocity_ms} m/s")
        parts.append("")

    if geospatial:
        parts.append("=== GEOSPATIAL DATA ===")
        parts.append(f"Within EEZ: {'Yes' if geospatial.within_eez else 'No'}")
        if geospatial.nearest_port:
            parts.append(f"Nearest Port: {geospatial.nearest_port} ({geospatial.nearest_port_distance_km} km)")
        if geospatial.restricted_zones_nearby:
            parts.append(f"⚠ Restricted Zones: {', '.join(geospatial.restricted_zones_nearby)}")
        if geospatial.marine_protected_areas:
            parts.append(f"🌊 MPAs: {', '.join(geospatial.marine_protected_areas)}")
        if geospatial.boundary_warning:
            parts.append(f"⚠ {geospatial.boundary_warning}")
        parts.append("")

    if pfz and pfz.zones:
        parts.append("=== POTENTIAL FISHING ZONES (Live Analysis) ===")
        for i, z in enumerate(pfz.zones, 1):
            parts.append(
                f"Zone {i}: ({z.lat}°N, {z.lng}°E) — {z.distance_km}km away, "
                f"SST: {z.sst_c}°C, Score: {z.score}/100"
            )
            parts.append(f"  Reason: {z.reasoning}")
        parts.append("")

    if historical:
        parts.append("=== HISTORICAL TREND ANALYSIS ===")
        parts.append(f"Analysis: {historical.historical_analysis_summary}")
        parts.append("")

    return "\n".join(parts)


async def run_explainability_agent(
    intent: Intent,
    language: Language,
    user_query: str,
    weather: WeatherReport | None = None,
    ocean: OceanReport | None = None,
    risk: RiskScore | None = None,
    geospatial: GeospatialReport | None = None,
    pfz: PFZReport | None = None,
    historical: HistoricalReport | None = None,
) -> tuple[str, str, AgentTrace]:
    """
    Execute Explainability Agent.
    Returns (recommendation, explanation) in the user's language.
    """
    trace = AgentTrace(
        agent_name="Explainability & Response Agent",
        status=AgentStatus.RUNNING,
        message=f"Generating explanation in {language.value}...",
        started_at=datetime.utcnow().isoformat(),
    )

    try:
        context = _build_context(intent, weather, ocean, risk, geospatial, pfz, historical, user_query)

        lang_map = {"en": "English", "hi": "Hindi (Devanagari script)", "bn": "Bengali (বাংলা script)"}
        lang_name = lang_map.get(language.value, "English")

        prompt = (
            f"Based on the following data from ORCA's specialized agents, "
            f"provide a clear, actionable explanation for the user.\n\n"
            f"Respond ENTIRELY in {lang_name}.\n\n"
            f"Data:\n{context}\n\n"
            f"Format your response as:\n"
            f"1. RECOMMENDATION: A one-line clear verdict\n"
            f"2. EXPLANATION: A detailed but concise explanation with specific data points\n"
            f"3. ACTION: What the user should do\n"
        )

        if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("your_"):
            # Fallback: generate explanation without LLM
            recommendation, explanation = _generate_fallback_explanation(
                intent, language, risk, weather, ocean, geospatial, pfz, historical
            )
        else:
            llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
                temperature=0.3,
            )

            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]

            response = await llm.ainvoke(messages)
            full_text = response.content

            # Parse recommendation and explanation
            lines = full_text.strip().split("\n")
            recommendation = ""
            explanation = full_text

            for i, line in enumerate(lines):
                if "RECOMMENDATION" in line.upper() or i == 0:
                    recommendation = line.replace("RECOMMENDATION:", "").replace("1.", "").strip()
                    recommendation = recommendation.lstrip("*# ")
                    break

            if not recommendation and risk:
                recommendation = f"{risk.risk_emoji} {risk.risk_label} — {risk.vessel_recommendation}"

        trace.status = AgentStatus.COMPLETED
        trace.message = f"Explanation generated in {lang_name}"
        trace.completed_at = datetime.utcnow().isoformat()

        return recommendation, explanation, trace

    except Exception as e:
        recommendation, explanation = _generate_fallback_explanation(
            intent, language, risk, weather, ocean, geospatial, pfz, historical
        )
        trace.status = AgentStatus.COMPLETED
        trace.message = f"Fallback explanation generated (LLM unavailable: {str(e)})"
        trace.completed_at = datetime.utcnow().isoformat()

        return recommendation, explanation, trace


def _generate_fallback_explanation(
    intent: Intent,
    language: Language,
    risk: RiskScore | None,
    weather: WeatherReport | None,
    ocean: OceanReport | None,
    geospatial: GeospatialReport | None,
    pfz: PFZReport | None,
    historical: HistoricalReport | None = None,
) -> tuple[str, str]:
    """Generate structured explanation without LLM (fallback)."""
    if risk:
        rec = f"{risk.risk_emoji} {risk.risk_label} (Score: {risk.final_score}/100)"
        parts = [rec, "", f"Primary Hazard: {risk.primary_hazard}", ""]

        if weather:
            parts.append("Weather Conditions:")
            if weather.wind_speed_kmh is not None:
                parts.append(f"  💨 Wind: {weather.wind_speed_kmh} km/h")
            if weather.rain_probability_pct is not None:
                parts.append(f"  🌧 Rain: {weather.rain_probability_pct}%")
            if weather.lightning_risk:
                parts.append(f"  ⚡ Lightning: {weather.lightning_risk}")

        if ocean:
            parts.append("\nOcean Conditions:")
            if ocean.wave_height_m is not None:
                parts.append(f"  🌊 Waves: {ocean.wave_height_m}m")
            if ocean.sea_state_description:
                parts.append(f"  🌊 Sea State: {ocean.sea_state_description}")
            if ocean.sst_c is not None:
                parts.append(f"  🌡 SST: {ocean.sst_c}°C")

        parts.append(f"\n{risk.vessel_recommendation}")

        return rec, "\n".join(parts)

    if historical:
        return "Historical Analysis", historical.historical_analysis_summary

    return "⚠ Unable to assess", "Insufficient data for assessment."
