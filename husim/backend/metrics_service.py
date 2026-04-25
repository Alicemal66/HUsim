"""Simülasyon metrik hesaplama servisi"""
import math
import logging
from models import SimulationMetrics

logger = logging.getLogger(__name__)


def compute_metrics(frames: list[dict], algorithm_name: str = "") -> SimulationMetrics:
    """
    Frame listesinden tüm metrikleri hesapla.
    Her frame: {"frame": int, "time": float, "vehicles": [...], "completed": bool}
    """
    if not frames:
        return SimulationMetrics(algorithm_name=algorithm_name)

    ego_states = []
    for f in frames:
        vehicles = f.get("vehicles", [])
        ego = next((v for v in vehicles if v.get("id") == "ego"), None)
        if ego:
            ego_states.append(ego)

    collision_count = 0
    near_miss_count = 0
    min_safety_dist = float("inf")
    risk_scores = []

    for f in frames:
        vehicles = f.get("vehicles", [])
        ego = next((v for v in vehicles if v.get("id") == "ego"), None)
        agents = [v for v in vehicles if v.get("id") != "ego"]

        if not ego:
            continue

        for ag in agents:
            dist = math.hypot(ego["x"] - ag["x"], ego["y"] - ag["y"])
            min_safety_dist = min(min_safety_dist, dist)
            if dist < 0.5:
                collision_count += 1
            elif dist < 2.0:
                near_miss_count += 1

    # Hız istatistikleri
    speeds = [s["speed"] for s in ego_states if "speed" in s]
    avg_speed = sum(speeds) / len(speeds) if speeds else 0

    # İvme hesabı (delta_v / delta_t)
    accelerations = []
    for i in range(1, len(ego_states)):
        dv = ego_states[i]["speed"] - ego_states[i - 1]["speed"]
        dt = frames[i]["time"] - frames[i - 1]["time"] if i < len(frames) else 0.1
        if dt > 0:
            accelerations.append(dv / dt)

    max_accel = max((a for a in accelerations if a > 0), default=0.0)
    max_decel = abs(min((a for a in accelerations if a < 0), default=0.0))

    # Direksiyon yumuşaklığı (heading değişim varyansı)
    headings = [s.get("heading", 0) for s in ego_states]
    heading_changes = [abs(headings[i] - headings[i - 1]) for i in range(1, len(headings))]
    if heading_changes:
        mean_hc = sum(heading_changes) / len(heading_changes)
        variance = sum((h - mean_hc) ** 2 for h in heading_changes) / len(heading_changes)
        smoothness = max(0.0, 1.0 - min(1.0, variance * 10))
    else:
        smoothness = 1.0

    # Güzergah verimliliği (doğrusal mesafe / gerçek mesafe)
    if len(ego_states) > 1:
        straight_dist = math.hypot(
            ego_states[-1]["x"] - ego_states[0]["x"],
            ego_states[-1]["y"] - ego_states[0]["y"],
        )
        actual_dist = sum(
            math.hypot(
                ego_states[i]["x"] - ego_states[i - 1]["x"],
                ego_states[i]["y"] - ego_states[i - 1]["y"],
            )
            for i in range(1, len(ego_states))
        )
        path_efficiency = min(1.0, straight_dist / actual_dist) if actual_dist > 0 else 1.0
    else:
        path_efficiency = 1.0

    completion_time = frames[-1]["time"] if frames else 0.0
    task_completed = frames[-1].get("completed", False) if frames else False
    risk_score = min(100.0, near_miss_count * 5.0 + collision_count * 25.0)

    return SimulationMetrics(
        collision_count=collision_count,
        near_miss_count=near_miss_count,
        min_safety_distance=round(min_safety_dist if min_safety_dist != float("inf") else 0, 2),
        risk_score=round(risk_score, 1),
        completion_time=round(completion_time, 2),
        path_efficiency=round(path_efficiency, 3),
        average_speed=round(avg_speed, 2),
        max_acceleration=round(max_accel, 2),
        max_deceleration=round(max_decel, 2),
        steering_smoothness=round(smoothness, 3),
        task_completed=task_completed,
        completion_rate=100.0 if task_completed else round(len(frames) / max(len(frames), 1) * 100, 1),
        algorithm_name=algorithm_name,
    )
