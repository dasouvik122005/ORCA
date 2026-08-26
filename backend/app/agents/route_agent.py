"""
Safe Route Planning Agent — Generates and evaluates candidate routes
using weather and ocean conditions along each path segment.
"""

from __future__ import annotations

import math
from datetime import datetime

from app.agents.geospatial_agent import haversine_distance
from app.config import ROUTE_WEIGHTS
from app.data.api_clients import fetch_marine_data, fetch_weather_data, get_target_hour_index
from app.models.schemas import (
    AgentStatus,
    AgentTrace,
    RouteCandidate,
    RouteReport,
    RouteWaypoint,
)


def _interpolate_waypoints(
    start_lat: float, start_lng: float,
    end_lat: float, end_lng: float,
    num_points: int = 5,
) -> list[tuple[float, float]]:
    """Generate intermediate waypoints along a great circle path."""
    points = []
    for i in range(num_points + 1):
        frac = i / num_points
        lat = start_lat + frac * (end_lat - start_lat)
        lng = start_lng + frac * (end_lng - start_lng)
        points.append((round(lat, 3), round(lng, 3)))
    return points


def _generate_candidate_routes(
    start_lat: float, start_lng: float,
    end_lat: float, end_lng: float,
) -> list[tuple[str, str, list[tuple[float, float]]]]:
    """
    Generate 3 candidate routes:
    1. Direct route (shortest path)
    2. Coastal route (stays closer to shore)
    3. Offshore route (goes further out then cuts in)
    """
    routes = []

    # Route A: Direct
    direct = _interpolate_waypoints(start_lat, start_lng, end_lat, end_lng, 5)
    routes.append(("route_direct", "Direct Route", direct))

    # Route B: Coastal (shifted toward coast — lower latitude for Bay of Bengal)
    mid_lat = (start_lat + end_lat) / 2
    mid_lng = (start_lng + end_lng) / 2

    # Determine coast direction (for Indian coast, generally west or north)
    coast_offset_lat = 0.15  # Shift toward coast
    coast_offset_lng = -0.1

    coastal_mid_lat = mid_lat + coast_offset_lat
    coastal_mid_lng = mid_lng + coast_offset_lng

    coastal = (
        _interpolate_waypoints(start_lat, start_lng, coastal_mid_lat, coastal_mid_lng, 2)[:-1]
        + _interpolate_waypoints(coastal_mid_lat, coastal_mid_lng, end_lat, end_lng, 3)
    )
    routes.append(("route_coastal", "Coastal Route", coastal))

    # Route C: Offshore (shifted away from coast)
    offshore_mid_lat = mid_lat - coast_offset_lat
    offshore_mid_lng = mid_lng + coast_offset_lng * -1

    offshore = (
        _interpolate_waypoints(start_lat, start_lng, offshore_mid_lat, offshore_mid_lng, 2)[:-1]
        + _interpolate_waypoints(offshore_mid_lat, offshore_mid_lng, end_lat, end_lng, 3)
    )
    routes.append(("route_offshore", "Offshore Route", offshore))

    return routes


async def _evaluate_waypoint(lat: float, lng: float, target_dt: str | None) -> dict:
    """Evaluate conditions at a single waypoint using live data."""
    try:
        # Fetch marine data
        marine = await fetch_marine_data(lat, lng, forecast_days=1)
        hourly = marine.get("hourly", {})
        times = hourly.get("time", [])
        idx = get_target_hour_index(times, target_dt)

        wave_h = hourly.get("wave_height", [])
        wave_height = wave_h[idx] if idx < len(wave_h) else None

        # Fetch weather data
        weather = await fetch_weather_data(lat, lng, forecast_days=1)
        w_hourly = weather.get("hourly", {})
        w_times = w_hourly.get("time", [])
        w_idx = get_target_hour_index(w_times, target_dt)

        wind_speed = w_hourly.get("wind_speed_10m", [])
        wind = wind_speed[w_idx] if w_idx < len(wind_speed) else None

        rain_prob = w_hourly.get("precipitation_probability", [])
        rain = rain_prob[w_idx] if w_idx < len(rain_prob) else None

        # Compute risk scores (0-100)
        wave_risk = 0
        if wave_height is not None:
            if wave_height >= 4.0:
                wave_risk = 100
            elif wave_height >= 2.5:
                wave_risk = 75
            elif wave_height >= 1.5:
                wave_risk = 40
            else:
                wave_risk = 10

        weather_risk = 0
        if wind is not None:
            if wind >= 50:
                weather_risk += 50
            elif wind >= 30:
                weather_risk += 30
            else:
                weather_risk += 10
        if rain is not None:
            if rain >= 70:
                weather_risk += 30
            elif rain >= 40:
                weather_risk += 15

        sea_state_risk = wave_risk  # Simplified: sea state correlates with waves

        return {
            "wave_risk": min(wave_risk, 100),
            "weather_risk": min(weather_risk, 100),
            "sea_state_risk": min(sea_state_risk, 100),
        }

    except Exception:
        return {"wave_risk": 50, "weather_risk": 50, "sea_state_risk": 50}


async def run_route_agent(
    start_lat: float, start_lng: float,
    end_lat: float, end_lng: float,
    target_dt: str | None = None,
) -> tuple[RouteReport, AgentTrace]:
    """
    Execute Route Planning Agent.
    Generates candidate routes and evaluates each using live marine/weather data.
    """
    trace = AgentTrace(
        agent_name="Safe Route Planning Agent",
        status=AgentStatus.RUNNING,
        message="Generating and evaluating candidate routes...",
        started_at=datetime.utcnow().isoformat(),
    )

    try:
        candidate_routes = _generate_candidate_routes(
            start_lat, start_lng, end_lat, end_lng
        )

        results: list[RouteCandidate] = []

        for route_id, route_name, waypoint_coords in candidate_routes:
            waypoints: list[RouteWaypoint] = []
            total_wave = 0
            total_weather = 0
            total_sea = 0

            # Evaluate conditions at each waypoint
            for wlat, wlng in waypoint_coords:
                scores = await _evaluate_waypoint(wlat, wlng, target_dt)
                wp = RouteWaypoint(
                    lat=wlat,
                    lng=wlng,
                    wave_risk=scores["wave_risk"],
                    weather_risk=scores["weather_risk"],
                    sea_state_risk=scores["sea_state_risk"],
                )
                waypoints.append(wp)
                total_wave += scores["wave_risk"]
                total_weather += scores["weather_risk"]
                total_sea += scores["sea_state_risk"]

            n = len(waypoints) or 1

            # Average risk per waypoint
            avg_wave = total_wave / n
            avg_weather = total_weather / n
            avg_sea = total_sea / n

            # Safety score: 100 - average risk (higher = safer)
            safety_score = 100 - (avg_wave * 0.5 + avg_weather * 0.3 + avg_sea * 0.2)

            # Distance
            total_dist = 0
            for i in range(len(waypoint_coords) - 1):
                total_dist += haversine_distance(
                    waypoint_coords[i][0], waypoint_coords[i][1],
                    waypoint_coords[i + 1][0], waypoint_coords[i + 1][1],
                )

            # Distance score: shorter is better (normalize against direct route)
            direct_dist = haversine_distance(start_lat, start_lng, end_lat, end_lng)
            dist_ratio = total_dist / max(direct_dist, 0.1)
            distance_score = max(0, 100 - (dist_ratio - 1) * 200)

            # Fuel score (proportional to distance + current)
            fuel_score = distance_score * 0.9  # Simplified

            # Overall weighted score
            overall = (
                safety_score * ROUTE_WEIGHTS["safety"]
                + (100 - avg_weather) * ROUTE_WEIGHTS["weather"]
                + (100 - avg_sea) * ROUTE_WEIGHTS["sea_state"]
                + distance_score * ROUTE_WEIGHTS["distance"]
                + fuel_score * ROUTE_WEIGHTS["fuel_efficiency"]
            )

            candidate = RouteCandidate(
                route_id=route_id,
                name=route_name,
                waypoints=waypoints,
                total_distance_km=round(total_dist, 1),
                safety_score=round(safety_score, 1),
                weather_score=round(100 - avg_weather, 1),
                sea_state_score=round(100 - avg_sea, 1),
                distance_score=round(distance_score, 1),
                fuel_score=round(fuel_score, 1),
                overall_score=round(overall, 1),
                reasoning="",
            )
            results.append(candidate)

        # Select best route
        results.sort(key=lambda r: r.overall_score, reverse=True)
        if results:
            results[0].recommended = True
            results[0].reasoning = (
                f"Recommended: Best overall score ({results[0].overall_score}/100) "
                f"balancing safety ({results[0].safety_score}), weather ({results[0].weather_score}), "
                f"and distance ({results[0].total_distance_km} km)"
            )
            for r in results[1:]:
                r.reasoning = f"Alternative: Score {r.overall_score}/100, Distance {r.total_distance_km} km"

        report = RouteReport(
            routes=results,
            recommended_route_id=results[0].route_id if results else None,
        )

        trace.status = AgentStatus.COMPLETED
        trace.message = (
            f"Evaluated {len(results)} routes. "
            f"Recommended: {results[0].name if results else 'None'} "
            f"(score: {results[0].overall_score if results else 0})"
        )
        trace.data = report.model_dump()
        trace.completed_at = datetime.utcnow().isoformat()

    except Exception as e:
        report = RouteReport()
        trace.status = AgentStatus.ERROR
        trace.message = f"Route Agent error: {str(e)}"
        trace.completed_at = datetime.utcnow().isoformat()

    return report, trace
