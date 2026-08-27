"""
ORCA Configuration — Central configuration for all agents, thresholds, and API endpoints.
All thresholds are configurable and based on IMD/INCOIS advisory guidelines.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")

# --- API Endpoints (all real, no mocks) ---
OPEN_METEO_MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
OPEN_METEO_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
OPENWEATHERMAP_ONECALL_URL = "https://api.openweathermap.org/data/3.0/onecall"
OPENWEATHERMAP_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

# --- LLM Configuration ---
GEMINI_MODEL = "gemini-1.5-flash"

# --- Risk Engine Thresholds (based on IMD/INCOIS guidelines) ---
RISK_THRESHOLDS = {
    # Wave height (meters) — IMD Sea State warnings
    "wave_height_low": 1.0,
    "wave_height_moderate": 2.0,
    "wave_height_high": 2.5,
    "wave_height_extreme": 4.0,
    # Wind speed (km/h) — Beaufort scale mapping
    "wind_speed_low": 15,
    "wind_speed_moderate": 25,
    "wind_speed_high": 35,
    "wind_speed_extreme": 50,
    # Rain probability (0-1)
    "rain_probability_high": 0.7,
    # Visibility (km)
    "visibility_poor": 2.0,
    # SST optimal range for fishing (°C) — tropical Indian Ocean
    "sst_optimal_min": 24.0,
    "sst_optimal_max": 30.0,
    # Chlorophyll-a (mg/m³) — productivity indicator
    "chlorophyll_productive": 0.5,
    "chlorophyll_high_productive": 2.0,
}

# --- Risk Weights (configurable) ---
RISK_WEIGHTS = {
    "wave": 0.30,
    "wind": 0.25,
    "weather": 0.20,
    "lightning": 0.10,
    "cyclone": 0.10,
    "boundary": 0.05,
}

# --- Route Optimization Weights ---
ROUTE_WEIGHTS = {
    "safety": 0.40,
    "weather": 0.25,
    "sea_state": 0.20,
    "distance": 0.10,
    "fuel_efficiency": 0.05,
}

# --- Risk Level Mapping ---
RISK_LEVELS = {
    "safe": {"min": 0, "max": 30, "label": "Safe", "emoji": "🟢", "color": "#2ecc71"},
    "caution": {"min": 31, "max": 60, "label": "Caution", "emoji": "🟡", "color": "#f1c40f"},
    "high_risk": {"min": 61, "max": 80, "label": "High Risk", "emoji": "🟠", "color": "#e67e22"},
    "extreme_risk": {"min": 81, "max": 100, "label": "Extreme Risk", "emoji": "🔴", "color": "#e74c3c"},
}

# --- Douglas Sea State Scale ---
SEA_STATE_SCALE = {
    0: {"description": "Calm (glassy)", "wave_height_max": 0.0},
    1: {"description": "Calm (rippled)", "wave_height_max": 0.1},
    2: {"description": "Smooth", "wave_height_max": 0.5},
    3: {"description": "Slight", "wave_height_max": 1.25},
    4: {"description": "Moderate", "wave_height_max": 2.5},
    5: {"description": "Rough", "wave_height_max": 4.0},
    6: {"description": "Very Rough", "wave_height_max": 6.0},
    7: {"description": "High", "wave_height_max": 9.0},
    8: {"description": "Very High", "wave_height_max": 14.0},
    9: {"description": "Phenomenal", "wave_height_max": float("inf")},
}

# --- Supported Intents ---
INTENTS = [
    "SAFETY_CHECK",
    "PFZ_DISCOVERY",
    "ROUTE_PLANNING",
    "EXPLANATION",
    "GENERAL",
]

# --- Supported Languages ---
LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
}

# --- Indian Coastal Locations (real coordinates) ---
FISHING_HARBORS = {
    "digha": {"lat": 21.6285, "lng": 87.5095, "state": "West Bengal"},
    "paradip": {"lat": 20.3164, "lng": 86.6085, "state": "Odisha"},
    "visakhapatnam": {"lat": 17.6868, "lng": 83.2185, "state": "Andhra Pradesh"},
    "chennai": {"lat": 13.0827, "lng": 80.2707, "state": "Tamil Nadu"},
    "kochi": {"lat": 9.9312, "lng": 76.2673, "state": "Kerala"},
    "mangalore": {"lat": 12.9141, "lng": 74.8560, "state": "Karnataka"},
    "goa": {"lat": 15.4909, "lng": 73.8278, "state": "Goa"},
    "mumbai": {"lat": 18.9388, "lng": 72.8354, "state": "Maharashtra"},
    "porbandar": {"lat": 21.6417, "lng": 69.6293, "state": "Gujarat"},
    "tuticorin": {"lat": 8.7642, "lng": 78.1348, "state": "Tamil Nadu"},
    "puri": {"lat": 19.7983, "lng": 85.8249, "state": "Odisha"},
    "ratnagiri": {"lat": 16.9902, "lng": 73.3120, "state": "Maharashtra"},
    "kakinada": {"lat": 16.9891, "lng": 82.2475, "state": "Andhra Pradesh"},
    "rameswaram": {"lat": 9.2876, "lng": 79.3129, "state": "Tamil Nadu"},
    "sundarbans": {"lat": 21.9497, "lng": 89.1833, "state": "West Bengal"},
    "haldia": {"lat": 22.0257, "lng": 88.0583, "state": "West Bengal"},
    "dhamra": {"lat": 20.7850, "lng": 86.9536, "state": "Odisha"},
}

# --- Cache TTL (seconds) ---
CACHE_TTL = 1800  # 30 minutes
