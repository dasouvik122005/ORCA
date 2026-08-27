"""
ORCA Pydantic Models — All request/response schemas for the API and inter-agent communication.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --- Enums ---

class Intent(str, Enum):
    SAFETY_CHECK = "SAFETY_CHECK"
    PFZ_DISCOVERY = "PFZ_DISCOVERY"
    ROUTE_PLANNING = "ROUTE_PLANNING"
    EXPLANATION = "EXPLANATION"
    GENERAL = "GENERAL"
    HISTORICAL_ANALYSIS = "HISTORICAL_ANALYSIS"


class RiskLevel(str, Enum):
    SAFE = "safe"
    CAUTION = "caution"
    HIGH_RISK = "high_risk"
    EXTREME_RISK = "extreme_risk"


class Language(str, Enum):
    EN = "en"
    HI = "hi"
    BN = "bn"


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


# --- Location ---

class Location(BaseModel):
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")
    name: Optional[str] = Field(None, description="Human-readable location name")


# --- User Request ---

class UserQuery(BaseModel):
    message: str = Field(..., description="User's natural language query")
    location: Optional[Location] = Field(None, description="User's location or selected harbor")
    datetime_target: Optional[str] = Field(None, description="Target date/time (ISO format)")
    conversation_id: Optional[str] = Field(None, description="For multi-turn context")


# --- Agent Trace (for transparency/explainability) ---

class AgentTrace(BaseModel):
    agent_name: str
    status: AgentStatus = AgentStatus.PENDING
    message: str = ""
    data: Optional[dict] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None


# --- Weather Report ---

class WeatherReport(BaseModel):
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    wind_gusts_kmh: Optional[float] = None
    temperature_c: Optional[float] = None
    feels_like_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    rain_probability_pct: Optional[float] = None
    rainfall_mm: Optional[float] = None
    visibility_km: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    lightning_risk: Optional[str] = None  # LOW / MODERATE / HIGH
    cyclone_alert: Optional[str] = None  # None or advisory text
    weather_description: Optional[str] = None
    alerts: list[str] = Field(default_factory=list)
    data_source: str = "live_api"


# --- Ocean Report ---

class OceanReport(BaseModel):
    wave_height_m: Optional[float] = None
    swell_wave_height_m: Optional[float] = None
    wind_wave_height_m: Optional[float] = None
    wave_period_s: Optional[float] = None
    wave_direction_deg: Optional[float] = None
    swell_wave_period_s: Optional[float] = None
    ocean_current_velocity_ms: Optional[float] = None
    ocean_current_direction_deg: Optional[float] = None
    sst_c: Optional[float] = None
    sea_state_code: Optional[int] = None
    sea_state_description: Optional[str] = None
    data_source: str = "live_api"


# --- PFZ Report ---

class PFZZone(BaseModel):
    lat: float
    lng: float
    distance_km: float
    chlorophyll_mgm3: Optional[float] = None
    sst_c: Optional[float] = None
    sst_gradient: Optional[float] = None
    risk_level: Optional[RiskLevel] = None
    score: float = 0.0
    reasoning: str = ""


class PFZReport(BaseModel):
    zones: list[PFZZone] = Field(default_factory=list)
    search_radius_km: float = 50.0
    data_source: str = "live_api"


# --- Geospatial Report ---

class GeospatialReport(BaseModel):
    within_eez: Optional[bool] = None
    eez_distance_km: Optional[float] = None
    nearest_boundary_km: Optional[float] = None
    boundary_warning: Optional[str] = None
    restricted_zones_nearby: list[str] = Field(default_factory=list)
    marine_protected_areas: list[str] = Field(default_factory=list)
    nearest_port: Optional[str] = None
    nearest_port_distance_km: Optional[float] = None
    data_source: str = "geojson"


# --- Risk Score ---

class RiskFactorScore(BaseModel):
    factor: str
    score: float = Field(..., ge=0, le=100)
    weight: float
    weighted_score: float
    detail: str = ""


class RiskScore(BaseModel):
    final_score: float = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    risk_label: str
    risk_emoji: str
    risk_color: str
    primary_hazard: str
    primary_hazard_score: float
    factor_scores: list[RiskFactorScore] = Field(default_factory=list)
    vessel_recommendation: str = ""
    data_source: str = "deterministic_engine"


# --- Route ---

class RouteWaypoint(BaseModel):
    lat: float
    lng: float
    wave_risk: Optional[float] = None
    weather_risk: Optional[float] = None
    sea_state_risk: Optional[float] = None


class RouteCandidate(BaseModel):
    route_id: str
    name: str
    waypoints: list[RouteWaypoint] = Field(default_factory=list)
    total_distance_km: float = 0.0
    safety_score: float = 0.0
    weather_score: float = 0.0
    sea_state_score: float = 0.0
    distance_score: float = 0.0
    fuel_score: float = 0.0
    overall_score: float = 0.0
    recommended: bool = False
    reasoning: str = ""


class RouteReport(BaseModel):
    routes: list[RouteCandidate] = Field(default_factory=list)
    recommended_route_id: Optional[str] = None


# --- Historical Report ---

class HistoricalReport(BaseModel):
    sst_trend_c: Optional[float] = None
    historical_analysis_summary: str = ""
    trend_data: list[dict] = Field(default_factory=list)
    data_source: str = "agentic_analysis"


# --- Full ORCA Response ---

class OrcaResponse(BaseModel):
    intent: Intent
    language: Language
    recommendation: str
    explanation: str
    risk_score: Optional[RiskScore] = None
    weather_report: Optional[WeatherReport] = None
    ocean_report: Optional[OceanReport] = None
    pfz_report: Optional[PFZReport] = None
    geospatial_report: Optional[GeospatialReport] = None
    route_report: Optional[RouteReport] = None
    historical_report: Optional[HistoricalReport] = None
    agent_traces: list[AgentTrace] = Field(default_factory=list)
    map_data: Optional[dict] = None
    conversation_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# --- WebSocket Events ---

class WSEvent(BaseModel):
    type: str  # agent_progress | result | error
    agent: Optional[str] = None
    status: Optional[AgentStatus] = None
    message: str = ""
    data: Optional[dict] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
