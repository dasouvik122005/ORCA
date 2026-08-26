"""
ORCA Orchestrator Agent — LangGraph-based state machine that coordinates
all specialized agents to process user queries end-to-end.

This is the brain of ORCA. It:
1. Detects intent and language from user query
2. Plans which agents to invoke
3. Orchestrates parallel and sequential agent execution
4. Collects results and produces the final response
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.explainability_agent import run_explainability_agent
from app.agents.geospatial_agent import run_geospatial_agent
from app.agents.ocean_agent import run_ocean_agent
from app.agents.pfz_agent import run_pfz_agent
from app.agents.risk_agent import run_risk_agent
from app.agents.route_agent import run_route_agent
from app.agents.weather_agent import run_weather_agent
from app.config import FISHING_HARBORS, GEMINI_API_KEY, GEMINI_MODEL
from app.models.schemas import (
    AgentStatus,
    AgentTrace,
    Intent,
    Language,
    Location,
    OrcaResponse,
    UserQuery,
)

# --- Conversation Store (in-memory for multi-turn) ---
_conversations: dict[str, list[dict]] = {}

# Intent detection prompt
INTENT_PROMPT = """You are ORCA's intent detection system. Analyze the user's message and extract:

1. **intent**: One of: SAFETY_CHECK, PFZ_DISCOVERY, ROUTE_PLANNING, EXPLANATION, GENERAL
2. **language**: The language of the message — "en" (English), "hi" (Hindi), or "bn" (Bengali)
3. **location_name**: Any location mentioned (harbor, city, coastal area). Return null if none.
4. **target_time**: Any time reference ("tomorrow morning", "today evening", etc). Return null if none.
5. **destination**: Any destination mentioned for route planning. Return null if none.

IMPORTANT:
- SAFETY_CHECK: User asks if it's safe to go fishing/sailing/to sea
- PFZ_DISCOVERY: User asks where to fish, nearest fishing zone, best fishing spot
- ROUTE_PLANNING: User asks for safest route, how to reach, best path
- EXPLANATION: User asks why something happened (fish decline, conditions change)
- GENERAL: Greetings, about ORCA, or unrelated

Respond ONLY with valid JSON, no markdown:
{"intent": "...", "language": "...", "location_name": "...", "target_time": "...", "destination": "..."}
"""


def _resolve_location(name: str | None, provided: Location | None) -> Location | None:
    """Resolve a location name to coordinates using the fishing harbors database."""
    if provided and provided.lat and provided.lng:
        return provided

    if name:
        name_lower = name.lower().strip()
        for harbor_name, info in FISHING_HARBORS.items():
            if harbor_name in name_lower or name_lower in harbor_name:
                return Location(lat=info["lat"], lng=info["lng"], name=harbor_name.title())

        # Try partial matching
        for harbor_name, info in FISHING_HARBORS.items():
            if any(part in name_lower for part in harbor_name.split()):
                return Location(lat=info["lat"], lng=info["lng"], name=harbor_name.title())

    # Default: Digha (common fishing harbor in Bay of Bengal)
    return Location(lat=21.6285, lng=87.5095, name="Digha")


def _resolve_target_time(time_ref: str | None) -> str | None:
    """Convert natural language time reference to ISO datetime."""
    if not time_ref:
        return None

    now = datetime.utcnow()
    time_lower = time_ref.lower()

    if "tomorrow" in time_lower:
        target = now + timedelta(days=1)
        if "morning" in time_lower:
            target = target.replace(hour=6, minute=0)
        elif "afternoon" in time_lower:
            target = target.replace(hour=14, minute=0)
        elif "evening" in time_lower:
            target = target.replace(hour=18, minute=0)
        else:
            target = target.replace(hour=8, minute=0)
        return target.isoformat()

    if "today" in time_lower or "now" in time_lower:
        if "evening" in time_lower:
            target = now.replace(hour=18, minute=0)
        elif "afternoon" in time_lower:
            target = now.replace(hour=14, minute=0)
        else:
            return now.isoformat()
        return target.isoformat()

    # Try to detect specific hours like "11 AM"
    import re
    match = re.search(r"(\d{1,2})\s*(am|pm|AM|PM)", time_ref)
    if match:
        hour = int(match.group(1))
        period = match.group(2).lower()
        if period == "pm" and hour != 12:
            hour += 12
        if period == "am" and hour == 12:
            hour = 0
        target = now + timedelta(days=1)
        target = target.replace(hour=hour, minute=0)
        return target.isoformat()

    return None


async def _detect_intent(
    user_message: str,
    conversation_history: list[dict],
) -> dict:
    """Use LLM to detect intent, language, and extract entities."""

    # Build conversation context for multi-turn
    context = ""
    if conversation_history:
        context = "\nPrevious conversation:\n"
        for turn in conversation_history[-3:]:  # Last 3 turns
            context += f"User: {turn.get('user', '')}\n"
            if turn.get("response"):
                context += f"ORCA: {turn['response'][:200]}...\n"
        context += "\n"

    try:
        if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("your_"):
            llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
                temperature=0,
            )
            messages = [
                SystemMessage(content=INTENT_PROMPT),
                HumanMessage(content=f"{context}User message: {user_message}"),
            ]
            response = await llm.ainvoke(messages)
            text = response.content.strip()
            # Clean markdown code blocks if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                text = text.rsplit("```", 1)[0]
            return json.loads(text)
        else:
            # Fallback: simple rule-based detection
            return _rule_based_intent(user_message)
    except Exception:
        return _rule_based_intent(user_message)


def _rule_based_intent(message: str) -> dict:
    """Fallback intent detection using keyword matching."""
    msg = message.lower()

    # Language detection
    lang = "en"
    # Bengali characters (Unicode range)
    if any("\u0980" <= c <= "\u09FF" for c in message):
        lang = "bn"
    elif any("\u0900" <= c <= "\u097F" for c in message):
        lang = "hi"

    # Intent detection
    intent = "GENERAL"
    safety_keywords = ["safe", "safety", "danger", "risk", "go fishing", "venture", "নিরাপদ", "সমুদ্র", "সুরক্ষিত", "सुरक्षित", "मछली"]
    pfz_keywords = ["fishing zone", "where to fish", "pfz", "fishing spot", "মাছ ধরা", "मछली पकड़"]
    route_keywords = ["route", "path", "reach", "navigate", "safest way", "পথ", "रास्ता"]
    explain_keywords = ["why", "reason", "decline", "কেন", "क्यों", "explain"]

    if any(k in msg for k in safety_keywords):
        intent = "SAFETY_CHECK"
    elif any(k in msg for k in pfz_keywords):
        intent = "PFZ_DISCOVERY"
    elif any(k in msg for k in route_keywords):
        intent = "ROUTE_PLANNING"
    elif any(k in msg for k in explain_keywords):
        intent = "EXPLANATION"

    # Location extraction (simple)
    location = None
    for harbor in FISHING_HARBORS:
        if harbor in msg:
            location = harbor
            break

    return {
        "intent": intent,
        "language": lang,
        "location_name": location,
        "target_time": "tomorrow morning" if "tomorrow" in msg else None,
        "destination": None,
    }


async def process_query(query: UserQuery, progress_callback=None) -> OrcaResponse:
    """
    Main orchestrator entry point.
    Processes user query through the multi-agent pipeline.
    """
    conversation_id = query.conversation_id or str(uuid.uuid4())
    conversation_history = _conversations.get(conversation_id, [])
    agent_traces: list[AgentTrace] = []

    async def _emit(agent: str, status: str, message: str):
        if progress_callback:
            await progress_callback(agent, status, message)

    # Step 1: Intent Detection
    await _emit("Orchestrator", "running", "Analyzing your query...")
    intent_data = await _detect_intent(query.message, conversation_history)

    intent_str = intent_data.get("intent", "GENERAL")
    try:
        intent = Intent(intent_str)
    except ValueError:
        intent = Intent.GENERAL

    lang_str = intent_data.get("language", "en")
    try:
        language = Language(lang_str)
    except ValueError:
        language = Language.EN

    location_name = intent_data.get("location_name")
    target_time = _resolve_target_time(intent_data.get("target_time"))
    location = _resolve_location(location_name, query.location)

    # If datetime provided in query, use it
    if query.datetime_target:
        target_time = query.datetime_target

    orchestrator_trace = AgentTrace(
        agent_name="Orchestrator Agent",
        status=AgentStatus.COMPLETED,
        message=(
            f"Intent: {intent.value} | Language: {language.value} | "
            f"Location: {location.name if location else 'Unknown'} | "
            f"Time: {target_time or 'Current'}"
        ),
        data={
            "intent": intent.value,
            "language": language.value,
            "location": location.model_dump() if location else None,
            "target_time": target_time,
        },
        started_at=datetime.utcnow().isoformat(),
        completed_at=datetime.utcnow().isoformat(),
    )
    agent_traces.append(orchestrator_trace)

    lat = location.lat if location else 21.6285
    lng = location.lng if location else 87.5095

    # Step 2: Execute agents based on intent
    weather_report = None
    ocean_report = None
    pfz_report = None
    geospatial_report = None
    risk_result = None
    route_report = None

    if intent in (Intent.SAFETY_CHECK, Intent.GENERAL, Intent.EXPLANATION):
        # Safety check: Weather + Ocean + Geospatial → Risk → Explain
        await _emit("Weather Agent", "running", "Fetching live weather data...")
        await _emit("Ocean Agent", "running", "Fetching live marine data...")
        await _emit("Geospatial Agent", "running", "Analyzing boundaries...")

        # Run Weather, Ocean, Geospatial in parallel
        weather_task = run_weather_agent(lat, lng, target_time)
        ocean_task = run_ocean_agent(lat, lng, target_time)
        geo_task = run_geospatial_agent(lat, lng)

        (weather_report, weather_trace), (ocean_report, ocean_trace), (geospatial_report, geo_trace) = (
            await asyncio.gather(weather_task, ocean_task, geo_task)
        )
        agent_traces.extend([weather_trace, ocean_trace, geo_trace])

        await _emit("Weather Agent", "completed", weather_trace.message)
        await _emit("Ocean Agent", "completed", ocean_trace.message)
        await _emit("Geospatial Agent", "completed", geo_trace.message)

        # Risk Assessment
        await _emit("Risk Agent", "running", "Calculating composite risk score...")
        risk_result, risk_trace = await run_risk_agent(weather_report, ocean_report, geospatial_report)
        agent_traces.append(risk_trace)
        await _emit("Risk Agent", "completed", risk_trace.message)

    elif intent == Intent.PFZ_DISCOVERY:
        # PFZ: Weather + Ocean + PFZ + Geospatial → Risk per zone
        await _emit("PFZ Agent", "running", "Scanning ocean for fishing zones...")
        await _emit("Ocean Agent", "running", "Fetching marine conditions...")
        await _emit("Geospatial Agent", "running", "Checking boundaries...")

        pfz_task = run_pfz_agent(lat, lng)
        ocean_task = run_ocean_agent(lat, lng, target_time)
        geo_task = run_geospatial_agent(lat, lng)
        weather_task = run_weather_agent(lat, lng, target_time)

        (pfz_report, pfz_trace), (ocean_report, ocean_trace), (geospatial_report, geo_trace), (weather_report, weather_trace) = (
            await asyncio.gather(pfz_task, ocean_task, geo_task, weather_task)
        )
        agent_traces.extend([pfz_trace, ocean_trace, geo_trace, weather_trace])

        await _emit("PFZ Agent", "completed", pfz_trace.message)
        await _emit("Ocean Agent", "completed", ocean_trace.message)
        await _emit("Geospatial Agent", "completed", geo_trace.message)
        await _emit("Weather Agent", "completed", weather_trace.message)

        # Risk for overall area
        await _emit("Risk Agent", "running", "Assessing risk for fishing zones...")
        risk_result, risk_trace = await run_risk_agent(weather_report, ocean_report, geospatial_report)
        agent_traces.append(risk_trace)
        await _emit("Risk Agent", "completed", risk_trace.message)

    elif intent == Intent.ROUTE_PLANNING:
        # Route: Determine destination from context or query
        dest_name = intent_data.get("destination")
        dest_location = _resolve_location(dest_name, None)

        # If no destination, check conversation history for PFZ results
        if dest_location and dest_location.name == "Digha" and conversation_history:
            for prev in reversed(conversation_history):
                if prev.get("pfz_zones"):
                    zones = prev["pfz_zones"]
                    if zones:
                        dest_location = Location(
                            lat=zones[0]["lat"], lng=zones[0]["lng"],
                            name="Recommended PFZ"
                        )
                    break

        dest_lat = dest_location.lat if dest_location else lat + 0.3
        dest_lng = dest_location.lng if dest_location else lng + 0.3

        await _emit("Route Agent", "running", "Generating candidate routes...")
        await _emit("Weather Agent", "running", "Fetching weather along routes...")

        weather_task = run_weather_agent(lat, lng, target_time)
        ocean_task = run_ocean_agent(lat, lng, target_time)
        route_task = run_route_agent(lat, lng, dest_lat, dest_lng, target_time)
        geo_task = run_geospatial_agent(lat, lng, dest_lat, dest_lng)

        (weather_report, weather_trace), (ocean_report, ocean_trace), (route_report, route_trace), (geospatial_report, geo_trace) = (
            await asyncio.gather(weather_task, ocean_task, route_task, geo_task)
        )
        agent_traces.extend([weather_trace, ocean_trace, route_trace, geo_trace])

        await _emit("Weather Agent", "completed", weather_trace.message)
        await _emit("Ocean Agent", "completed", ocean_trace.message)
        await _emit("Route Agent", "completed", route_trace.message)
        await _emit("Geospatial Agent", "completed", geo_trace.message)

        # Risk for departure area
        await _emit("Risk Agent", "running", "Assessing departure area risk...")
        risk_result, risk_trace = await run_risk_agent(weather_report, ocean_report, geospatial_report)
        agent_traces.append(risk_trace)
        await _emit("Risk Agent", "completed", risk_trace.message)

    # Step 3: Explainability Agent
    await _emit("Explainability Agent", "running", f"Generating explanation in {language.value}...")
    recommendation, explanation, explain_trace = await run_explainability_agent(
        intent=intent,
        language=language,
        user_query=query.message,
        weather=weather_report,
        ocean=ocean_report,
        risk=risk_result,
        geospatial=geospatial_report,
        pfz=pfz_report,
    )
    agent_traces.append(explain_trace)
    await _emit("Explainability Agent", "completed", explain_trace.message)

    # Step 4: Build map data
    map_data = _build_map_data(location, weather_report, ocean_report, pfz_report, geospatial_report, route_report, risk_result)

    # Step 5: Store conversation for multi-turn
    turn = {
        "user": query.message,
        "response": recommendation,
        "intent": intent.value,
        "location": location.model_dump() if location else None,
        "target_time": target_time,
        "pfz_zones": [z.model_dump() for z in pfz_report.zones] if pfz_report else None,
    }
    if conversation_id not in _conversations:
        _conversations[conversation_id] = []
    _conversations[conversation_id].append(turn)

    # Build response
    response = OrcaResponse(
        intent=intent,
        language=language,
        recommendation=recommendation,
        explanation=explanation,
        risk_score=risk_result,
        weather_report=weather_report,
        ocean_report=ocean_report,
        pfz_report=pfz_report,
        geospatial_report=geospatial_report,
        route_report=route_report,
        agent_traces=agent_traces,
        map_data=map_data,
        conversation_id=conversation_id,
    )

    return response


def _build_map_data(
    location, weather, ocean, pfz, geospatial, route, risk
) -> dict:
    """Build GeoJSON-like map data for the frontend."""
    data: dict[str, Any] = {
        "center": {"lat": location.lat, "lng": location.lng} if location else {"lat": 20, "lng": 85},
        "zoom": 8,
        "markers": [],
        "zones": [],
        "routes": [],
    }

    # User location marker
    if location:
        data["markers"].append({
            "type": "user_location",
            "lat": location.lat,
            "lng": location.lng,
            "label": location.name or "Your Location",
            "icon": "📍",
        })

    # PFZ zones
    if pfz and pfz.zones:
        for i, z in enumerate(pfz.zones):
            data["markers"].append({
                "type": "pfz",
                "lat": z.lat,
                "lng": z.lng,
                "label": f"PFZ Zone {i + 1}",
                "icon": "🐟",
                "score": z.score,
                "distance": z.distance_km,
                "sst": z.sst_c,
            })

    # Risk zone around user
    if risk:
        data["zones"].append({
            "type": "risk_zone",
            "center_lat": location.lat if location else 20,
            "center_lng": location.lng if location else 85,
            "radius_km": 20,
            "risk_level": risk.risk_level.value,
            "risk_color": risk.risk_color,
            "risk_score": risk.final_score,
        })

    # Routes
    if route and route.routes:
        for r in route.routes:
            data["routes"].append({
                "route_id": r.route_id,
                "name": r.name,
                "recommended": r.recommended,
                "waypoints": [{"lat": wp.lat, "lng": wp.lng} for wp in r.waypoints],
                "overall_score": r.overall_score,
                "color": "#2ecc71" if r.recommended else "#95a5a6",
            })

    return data
