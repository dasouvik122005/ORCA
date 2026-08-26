"""
PFZ (Potential Fishing Zone) Agent — Identifies fishing zones in real-time
using live SST and oceanographic data with marine biology heuristics.
No mock data — all zone identification is computed from live parameters.
"""

from __future__ import annotations

from datetime import datetime

from app.config import RISK_THRESHOLDS
from app.data.api_clients import fetch_sst_grid
from app.agents.geospatial_agent import haversine_distance
from app.models.schemas import AgentStatus, AgentTrace, PFZReport, PFZZone


def _score_fishing_potential(sst: float | None, sst_gradient: float = 0.0) -> tuple[float, str]:
    """
    Score fishing potential based on oceanographic heuristics.
    
    Key principles (from marine biology):
    - Optimal SST: 24-30°C for tropical Indian Ocean fish species
    - SST gradients (thermal fronts): Higher gradients indicate upwelling = more fish
    - Chlorophyll proxy: SST gradients correlate with nutrient upwelling
    """
    if sst is None:
        return 0.0, "No SST data available"

    score = 0.0
    reasons = []

    # SST optimality (0-50 points)
    opt_min = RISK_THRESHOLDS["sst_optimal_min"]
    opt_max = RISK_THRESHOLDS["sst_optimal_max"]
    if opt_min <= sst <= opt_max:
        # Within optimal range — score based on sweet spot (26-28°C)
        sweet_spot = 27.0
        deviation = abs(sst - sweet_spot)
        sst_score = max(0, 50 - deviation * 10)
        score += sst_score
        reasons.append(f"SST {sst}°C within optimal range ({opt_min}-{opt_max}°C)")
    elif sst < opt_min:
        penalty = (opt_min - sst) * 10
        score += max(0, 20 - penalty)
        reasons.append(f"SST {sst}°C below optimal range")
    else:
        penalty = (sst - opt_max) * 10
        score += max(0, 20 - penalty)
        reasons.append(f"SST {sst}°C above optimal range")

    # SST gradient (thermal front) (0-30 points)
    if sst_gradient > 0.5:
        score += 30
        reasons.append(f"Strong thermal front detected (gradient: {sst_gradient:.1f}°C)")
    elif sst_gradient > 0.2:
        score += 20
        reasons.append(f"Moderate thermal front (gradient: {sst_gradient:.1f}°C)")
    elif sst_gradient > 0.1:
        score += 10
        reasons.append(f"Weak thermal activity (gradient: {sst_gradient:.1f}°C)")

    # Nutrient upwelling indicator (SST 1-3°C below surrounding = upwelling)
    # This is approximated from the gradient
    if sst_gradient > 0.3 and opt_min <= sst <= opt_max:
        score += 20
        reasons.append("Possible nutrient upwelling zone")

    return min(score, 100), "; ".join(reasons)


def _compute_sst_gradient(center_sst: float, neighbor_ssts: list[float]) -> float:
    """Compute SST gradient magnitude at a point relative to its neighbors."""
    if not neighbor_ssts or center_sst is None:
        return 0.0
    valid = [s for s in neighbor_ssts if s is not None]
    if not valid:
        return 0.0
    avg_neighbor = sum(valid) / len(valid)
    return abs(center_sst - avg_neighbor)


async def run_pfz_agent(
    lat: float,
    lng: float,
    search_radius_km: float = 50.0,
) -> tuple[PFZReport, AgentTrace]:
    """
    Execute PFZ Discovery Agent.
    Identifies potential fishing zones using live SST data and
    oceanographic heuristics (thermal fronts, optimal SST ranges).
    """
    trace = AgentTrace(
        agent_name="PFZ Discovery Agent",
        status=AgentStatus.RUNNING,
        message="Scanning ocean for potential fishing zones using live satellite data...",
        started_at=datetime.utcnow().isoformat(),
    )

    try:
        # Convert search radius to degrees (approximate)
        radius_deg = search_radius_km / 111.0  # ~111 km per degree

        # Fetch SST grid from live API
        grid_step = max(0.1, radius_deg / 5)  # Adaptive resolution
        sst_points = await fetch_sst_grid(lat, lng, radius_deg, grid_step)

        # Build SST map for gradient computation
        sst_map: dict[tuple[float, float], float] = {}
        for p in sst_points:
            if p["sst"] is not None:
                sst_map[(p["lat"], p["lng"])] = p["sst"]

        # Evaluate each point for fishing potential
        zones: list[PFZZone] = []
        for p in sst_points:
            if p["sst"] is None:
                continue

            plat, plng = p["lat"], p["lng"]

            # Compute gradient from neighbors
            neighbors = []
            for nlat, nlng in sst_map:
                if (nlat, nlng) != (plat, plng):
                    d = haversine_distance(plat, plng, nlat, nlng)
                    if d < 30:  # Within 30km
                        neighbors.append(sst_map[(nlat, nlng)])
            gradient = _compute_sst_gradient(p["sst"], neighbors)

            # Score the point
            score, reasoning = _score_fishing_potential(p["sst"], gradient)

            # Only include points with meaningful fishing potential
            if score < 30:
                continue

            dist = haversine_distance(lat, lng, plat, plng)
            zone = PFZZone(
                lat=plat,
                lng=plng,
                distance_km=round(dist, 1),
                sst_c=p["sst"],
                sst_gradient=round(gradient, 2),
                score=round(score, 1),
                reasoning=reasoning,
            )
            zones.append(zone)

        # Sort by score (best first), limit to top 5
        zones.sort(key=lambda z: z.score, reverse=True)
        zones = zones[:5]

        report = PFZReport(
            zones=zones,
            search_radius_km=search_radius_km,
            data_source="Open-Meteo SST Grid (live) + Oceanographic Heuristics",
        )

        trace.status = AgentStatus.COMPLETED
        trace.message = (
            f"Found {len(zones)} potential fishing zones within {search_radius_km}km radius"
        )
        trace.data = report.model_dump()
        trace.completed_at = datetime.utcnow().isoformat()

    except Exception as e:
        report = PFZReport(data_source=f"error: {str(e)}")
        trace.status = AgentStatus.ERROR
        trace.message = f"PFZ Agent error: {str(e)}"
        trace.completed_at = datetime.utcnow().isoformat()

    return report, trace
