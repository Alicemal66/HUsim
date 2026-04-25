"""Çarpışma tespit servisi — Grid Map tabanlı risk hesaplama"""
import math
import logging
from models import VehicleState, Point, CollisionReport, OptimizedParams

logger = logging.getLogger(__name__)

# Araç boyutları (metre)
VEHICLE_LENGTH = 8.0
VEHICLE_WIDTH = 3.5


def check_collision_probability(
    ego_vehicle: VehicleState,
    agents: list[VehicleState],
    road_boundary: list[Point],
    params: OptimizedParams,
) -> CollisionReport:
    """
    Grid tabanlı çarpışma olasılığı hesapla.
    Vehicle-Collision-Detection-in-Grid-Map prensipleri kullanılır.
    """
    collision_risks = []
    min_ttc = None

    for agent in agents:
        dist = _euclidean_distance(ego_vehicle, agent)

        # Güvenli mesafe (parametre bazlı)
        safe_dist = _safe_distance(ego_vehicle.speed, params)

        # İkincil mesafe — araç uzunluğuna göre çarpışma alanı
        collision_zone = VEHICLE_LENGTH * 1.5 * params.safety_margin_factor

        if dist < collision_zone:
            # Çarpışma zamanı tahmini (TTC)
            rel_speed = abs(ego_vehicle.speed - agent.speed)
            ttc = dist / rel_speed if rel_speed > 0.1 else None

            risk_pct = max(0, min(100, (1 - dist / collision_zone) * 100))

            collision_risks.append({
                "agent_id": agent.vehicle_id,
                "distance": round(dist, 2),
                "safe_distance": round(safe_dist, 2),
                "risk_percentage": round(risk_pct, 1),
                "time_to_collision": round(ttc, 2) if ttc else None,
            })

            if ttc and (min_ttc is None or ttc < min_ttc):
                min_ttc = ttc

    # Yol sınırı çarpışma kontrolü
    boundary_risk = _check_road_boundary(ego_vehicle, road_boundary)

    # Genel risk skoru (0-100)
    if collision_risks:
        max_agent_risk = max(r["risk_percentage"] for r in collision_risks)
    else:
        max_agent_risk = 0

    total_risk = min(100, max(max_agent_risk, boundary_risk))

    return CollisionReport(
        risk_score=round(total_risk, 1),
        collision_risks=collision_risks,
        time_to_collision=round(min_ttc, 2) if min_ttc else None,
    )


def _euclidean_distance(v1: VehicleState, v2: VehicleState) -> float:
    return math.hypot(v1.x - v2.x, v1.y - v2.y)


def _safe_distance(speed_ms: float, params: OptimizedParams) -> float:
    """Hıza ve parametrelere göre güvenli takip mesafesi hesapla."""
    # Temel kural: v²/(2·a) + tepki mesafesi
    reaction_time = 1.5  # saniye
    decel = 4.0 / params.braking_distance_factor
    braking_dist = (speed_ms ** 2) / (2 * max(0.1, decel))
    reaction_dist = speed_ms * reaction_time
    return (braking_dist + reaction_dist) * params.safety_margin_factor


def _check_road_boundary(vehicle: VehicleState, boundary: list[Point]) -> float:
    """Yol sınırına yakınlık risk skoru."""
    if not boundary:
        return 0.0

    min_dist = float("inf")
    for i in range(len(boundary) - 1):
        dist = _point_to_segment(
            vehicle.x, vehicle.y,
            boundary[i].x, boundary[i].y,
            boundary[i + 1].x, boundary[i + 1].y,
        )
        min_dist = min(min_dist, dist)

    # 5 metre içinde risk başlar
    if min_dist > 5.0:
        return 0.0
    return max(0, min(100, (1 - min_dist / 5.0) * 80))


def _point_to_segment(px, py, ax, ay, bx, by) -> float:
    """Nokta ile çizgi segmenti arasındaki mesafe."""
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))
