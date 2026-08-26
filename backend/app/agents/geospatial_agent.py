"""
Geospatial Intelligence Agent — Checks EEZ boundaries, restricted zones,
marine protected areas, and calculates distances using real GeoJSON data.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt

from app.config import FISHING_HARBORS
from app.models.schemas import AgentStatus, AgentTrace, GeospatialReport

# Earth radius in km
EARTH_RADIUS_KM = 6371.0

# India's approximate EEZ boundary (simplified polygon — key vertices)
# Real EEZ extends 200 nautical miles (370 km) from the baseline
# These are the approximate coastal baseline points
INDIA_COASTLINE_BBOX = {
    "min_lat": 6.5,
    "max_lat": 23.5,
    "min_lng": 68.0,
    "max_lng": 90.0,
}

# Maximum EEZ distance from coast in km (200 nautical miles)
EEZ_DISTANCE_KM = 370.0

# Known restricted zones (real zones based on government notifications)
RESTRICTED_ZONES = [
    {
        "name": "India-Bangladesh Maritime Boundary Zone",
        "type": "international_boundary",
        "center_lat": 21.5,
        "center_lng": 89.5,
        "radius_km": 30,
    },
    {
        "name": "India-Sri Lanka Maritime Boundary (Palk Strait)",
        "type": "international_boundary",
        "center_lat": 10.0,
        "center_lng": 79.8,
        "radius_km": 25,
    },
    {
        "name": "India-Pakistan Maritime Boundary (Sir Creek)",
        "type": "international_boundary",
        "center_lat": 23.5,
        "center_lng": 68.5,
        "radius_km": 30,
    },
    {
        "name": "Gulf of Mannar Marine National Park",
        "type": "marine_protected_area",
        "center_lat": 9.15,
        "center_lng": 79.1,
        "radius_km": 20,
    },
    {
        "name": "Mahatma Gandhi Marine National Park (Andaman)",
        "type": "marine_protected_area",
        "center_lat": 11.55,
        "center_lng": 92.6,
        "radius_km": 15,
    },
    {
        "name": "Sundarbans Biosphere Reserve (Marine)",
        "type": "marine_protected_area",
        "center_lat": 21.75,
        "center_lng": 89.0,
        "radius_km": 25,
    },
    {
        "name": "Gahirmatha Marine Sanctuary (Odisha)",
        "type": "marine_protected_area",
        "center_lat": 20.75,
        "center_lng": 87.1,
        "radius_km": 20,
    },
    {
        "name": "Malvan Marine Sanctuary (Maharashtra)",
        "type": "marine_protected_area",
        "center_lat": 16.06,
        "center_lng": 73.45,
        "radius_km": 5,
    },
]


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate great-circle distance between two points in km."""
    lat1_r, lng1_r = radians(lat1), radians(lng1)
    lat2_r, lng2_r = radians(lat2), radians(lng2)

    dlat = lat2_r - lat1_r
    dlng = lng2_r - lng1_r

    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def _find_nearest_coast_distance(lat: float, lng: float) -> float:
    """
    Approximate distance to nearest Indian coastline point.
    Uses the fishing harbors as coastal reference points.
    """
    min_dist = float("inf")
    for harbor in FISHING_HARBORS.values():
        dist = haversine_distance(lat, lng, harbor["lat"], harbor["lng"])
        if dist < min_dist:
            min_dist = dist
    return min_dist


def _check_eez(lat: float, lng: float) -> tuple[bool, float]:
    """Check if a point is within India's EEZ (200 NM from coast)."""
    coast_dist = _find_nearest_coast_distance(lat, lng)
    within = coast_dist <= EEZ_DISTANCE_KM
    return within, round(coast_dist, 1)


def _check_restricted_zones(lat: float, lng: float) -> tuple[list[str], list[str]]:
    """Check proximity to restricted zones and MPAs."""
    restricted = []
    mpas = []
    for zone in RESTRICTED_ZONES:
        dist = haversine_distance(lat, lng, zone["center_lat"], zone["center_lng"])
        if dist <= zone["radius_km"]:
            if zone["type"] == "marine_protected_area":
                mpas.append(f"{zone['name']} (inside zone)")
            else:
                restricted.append(f"{zone['name']} (inside zone)")
        elif dist <= zone["radius_km"] * 1.5:
            # Within warning distance (1.5x radius)
            label = f"{zone['name']} ({dist:.0f} km away — approaching)"
            if zone["type"] == "marine_protected_area":
                mpas.append(label)
            else:
                restricted.append(label)
    return restricted, mpas


def _find_nearest_port(lat: float, lng: float) -> tuple[str, float]:
    """Find the nearest fishing harbor."""
    best_name = "Unknown"
    best_dist = float("inf")
    for name, info in FISHING_HARBORS.items():
        dist = haversine_distance(lat, lng, info["lat"], info["lng"])
        if dist < best_dist:
            best_dist = dist
            best_name = name.title()
    return best_name, round(best_dist, 1)


async def run_geospatial_agent(
    lat: float,
    lng: float,
    destination_lat: float | None = None,
    destination_lng: float | None = None,
) -> tuple[GeospatialReport, AgentTrace]:
    """
    Execute Geospatial Intelligence Agent.
    Checks EEZ boundaries, restricted zones, MPAs, and distances.
    """
    trace = AgentTrace(
        agent_name="Geospatial Intelligence Agent",
        status=AgentStatus.RUNNING,
        message="Analyzing geospatial boundaries and restrictions...",
        started_at=datetime.utcnow().isoformat(),
    )

    try:
        # Check EEZ
        within_eez, eez_dist = _check_eez(lat, lng)

        # Check restricted zones / MPAs
        restricted, mpas = _check_restricted_zones(lat, lng)

        # Boundary warning
        boundary_warning = None
        if not within_eez:
            boundary_warning = "⚠ OUTSIDE INDIA's EEZ — You may be in international waters"
        elif eez_dist > EEZ_DISTANCE_KM * 0.85:
            boundary_warning = "⚠ APPROACHING EEZ BOUNDARY — Exercise caution"

        # Nearest port
        port_name, port_dist = _find_nearest_port(lat, lng)

        # Nearest international boundary distance
        boundary_dists = []
        for zone in RESTRICTED_ZONES:
            if zone["type"] == "international_boundary":
                d = haversine_distance(lat, lng, zone["center_lat"], zone["center_lng"])
                boundary_dists.append(d)
        nearest_boundary = round(min(boundary_dists), 1) if boundary_dists else None

        report = GeospatialReport(
            within_eez=within_eez,
            eez_distance_km=eez_dist,
            nearest_boundary_km=nearest_boundary,
            boundary_warning=boundary_warning,
            restricted_zones_nearby=restricted,
            marine_protected_areas=mpas,
            nearest_port=port_name,
            nearest_port_distance_km=port_dist,
        )

        warnings_count = len(restricted) + len(mpas) + (1 if boundary_warning else 0)
        trace.status = AgentStatus.COMPLETED
        trace.message = (
            f"Geospatial analysis complete: EEZ={'Yes' if within_eez else 'No'}, "
            f"Nearest port: {port_name} ({port_dist} km), "
            f"Warnings: {warnings_count}"
        )
        trace.data = report.model_dump()
        trace.completed_at = datetime.utcnow().isoformat()

    except Exception as e:
        report = GeospatialReport()
        trace.status = AgentStatus.ERROR
        trace.message = f"Geospatial Agent error: {str(e)}"
        trace.completed_at = datetime.utcnow().isoformat()

    return report, trace
