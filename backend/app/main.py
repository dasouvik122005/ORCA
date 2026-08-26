"""
ORCA Marine Intelligence Platform — FastAPI Backend

Main application entry point with REST API and WebSocket endpoints.
"""

from __future__ import annotations

import json
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.agents.orchestrator import process_query
from app.config import GEMINI_API_KEY, OPENWEATHERMAP_API_KEY
from app.models.schemas import OrcaResponse, UserQuery
from app.websocket import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup/shutdown events."""
    print("ORCA Marine Intelligence Platform starting...")
    print(f"   Gemini API Key: {'Configured' if GEMINI_API_KEY and not GEMINI_API_KEY.startswith('your_') else 'Not set'}")
    print(f"   OpenWeatherMap Key: {'Configured' if OPENWEATHERMAP_API_KEY and not OPENWEATHERMAP_API_KEY.startswith('your_') else 'Not set (limited weather data)'}")
    print("   Open-Meteo Marine: No key needed")
    print("   Open-Meteo Weather: No key needed")
    print("ORCA ready to serve.")
    yield
    print("ORCA shutting down.")


app = FastAPI(
    title="🐋 ORCA Marine Intelligence Platform",
    description=(
        "Agentic AI-powered marine decision intelligence platform that coordinates "
        "specialized AI agents to analyze ocean, weather, satellite, and geospatial data."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ORCA Marine Intelligence Platform",
        "agents": [
            "Orchestrator",
            "Weather Intelligence",
            "Ocean Intelligence",
            "PFZ Discovery",
            "Geospatial Intelligence",
            "Risk Assessment",
            "Explainability & Response",
            "Safe Route Planning",
        ],
        "data_sources": {
            "open_meteo_marine": "active",
            "open_meteo_weather": "active",
            "openweathermap": "active" if OPENWEATHERMAP_API_KEY and not OPENWEATHERMAP_API_KEY.startswith("your_") else "not_configured",
            "gemini_llm": "active" if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("your_") else "not_configured",
        },
    }


@app.post("/api/chat", response_model=OrcaResponse)
async def chat(query: UserQuery):
    """
    Main chat endpoint. Accepts a user query and returns the full ORCA response
    with agent traces, risk scores, map data, and explanation.
    """
    try:
        # Progress callback for WebSocket updates
        async def progress_cb(agent: str, status: str, message: str):
            await manager.send_agent_progress(agent, status, message)

        response = await process_query(query, progress_callback=progress_cb)
        return response

    except Exception as e:
        traceback.print_exc()
        return OrcaResponse(
            intent="GENERAL",
            language="en",
            recommendation="⚠ ORCA encountered an error",
            explanation=f"Error processing your request: {str(e)}",
            agent_traces=[],
            conversation_id=query.conversation_id or "",
        )


@app.get("/api/harbors")
async def get_harbors():
    """Return list of fishing harbors for the frontend location picker."""
    from app.config import FISHING_HARBORS
    return {
        name: {**info, "name": name.title()}
        for name, info in FISHING_HARBORS.items()
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time agent progress streaming."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; listen for pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
