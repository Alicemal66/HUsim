"""HÜsim — Senaryo üretici"""
import json
import math
import random
import logging
from pathlib import Path
from scenario_loader import (
    GENERATED_PATH,
    _make_demo_road_geometry,
    _make_ego_route,
    _make_agent_routes,
    _interpolate_route,
)

logger = logging.getLogger(__name__)


class ScenarioGenerator:
    def generate(
        self,
        intersection_type: str,   # "T", "cross", "straight", "complex"
        vehicle_count: int,        # 2-8
        difficulty: str,           # "kolay", "orta", "zor", "kritik"
        special_condition: str,    # "normal", "dar_yol", "egim", "kor_kavsak"
        weather_params: dict,      # hava optimizasyon sonuçları
        name: str = "",
    ) -> dict:
        """
        Tam senaryo üret ve generated_scenarios/ klasörüne kaydet.
        """
        import time
        scenario_id = f"gen_{intersection_type}_{vehicle_count}v_{difficulty}_{int(time.time()) % 100000}"

        dt = 0.1
        total_time = 20.0
        total_frames = int(total_time / dt)

        road_geom = _make_demo_road_geometry(intersection_type)
        ego_route = _make_ego_route(intersection_type)
        agent_routes = _make_agent_routes(intersection_type, vehicle_count - 1)

        # Zorluk faktörleri
        difficulty_params = {
            "kolay":   {"speed_mult": 0.7, "jitter": 0.05, "brake_prob": 0.02},
            "orta":    {"speed_mult": 1.0, "jitter": 0.15, "brake_prob": 0.08},
            "zor":     {"speed_mult": 1.3, "jitter": 0.3,  "brake_prob": 0.15},
            "kritik":  {"speed_mult": 1.6, "jitter": 0.5,  "brake_prob": 0.25},
        }
        dp = difficulty_params.get(difficulty, difficulty_params["orta"])

        # Hava etkisi: max_speed_factor
        speed_factor = weather_params.get("max_speed_factor", 1.0) if weather_params else 1.0

        # Özel koşullar
        special_mods = {
            "normal":     {"road_width_mult": 1.0, "slope": 0.0},
            "dar_yol":    {"road_width_mult": 0.55, "slope": 0.0},
            "egim":       {"road_width_mult": 1.0, "slope": 0.08},
            "kor_kavsak": {"road_width_mult": 1.0, "slope": 0.0},
        }
        sm = special_mods.get(special_condition, special_mods["normal"])

        braking_states: dict[str, bool] = {}

        frames = []
        for fi in range(total_frames):
            t = fi * dt
            vehicles = []

            # EGO
            ex, ey, eh, es = _interpolate_route(ego_route, t, total_time)
            es *= dp["speed_mult"] * speed_factor
            if sm["slope"] > 0:
                # Eğim etkisi: t > 0.5 iken yavaşla
                if t / total_time > 0.5:
                    es *= (1.0 - sm["slope"] * 3)

            vehicles.append({
                "id": "ego",
                "x": round(ex + random.uniform(-dp["jitter"], dp["jitter"]), 3),
                "y": round(ey + random.uniform(-dp["jitter"], dp["jitter"]), 3),
                "heading": round(eh, 4),
                "speed": round(max(0.0, es), 2),
                "length": 8.5,
                "width": 3.5,
            })

            # Ajanlar
            for ai, route in enumerate(agent_routes):
                key = f"a{ai}"
                ax, ay, ah, asp = _interpolate_route(route, t, total_time)
                asp *= dp["speed_mult"] * speed_factor

                # Beklenmedik fren
                if random.random() < dp["brake_prob"] * 0.01:
                    braking_states[key] = True
                if braking_states.get(key):
                    asp *= 0.2
                    if random.random() < 0.05:
                        braking_states[key] = False

                # Çarpışmaya yakın: yavaşla
                dist = math.hypot(ax - ex, ay - ey)
                if dist < 10.0:
                    asp = max(0.0, asp * (dist / 10.0))

                vehicles.append({
                    "id": f"agent_{ai + 1}",
                    "x": round(ax + random.uniform(-dp["jitter"], dp["jitter"]), 3),
                    "y": round(ay + random.uniform(-dp["jitter"], dp["jitter"]), 3),
                    "heading": round(ah, 4),
                    "speed": round(max(0.0, asp), 2),
                    "length": round(random.choice([4.5, 5.0, 5.4, 6.0]), 1),
                    "width": round(random.choice([1.9, 2.0, 2.1, 2.2]), 1),
                })

            frames.append({
                "frame": fi,
                "time": round(t, 2),
                "vehicles": vehicles,
                "completed": fi == total_frames - 1,
            })

        scenario_name = name if name else f"{intersection_type.upper()} — {vehicle_count} Araç ({difficulty.capitalize()})"
        result = {
            "scenario_id": scenario_id,
            "name": scenario_name,
            "source": "generated",
            "total_frames": total_frames,
            "dt": dt,
            "agent_count": vehicle_count,
            "total_time": total_time,
            "scenario_type": intersection_type,
            "difficulty": difficulty,
            "special_condition": special_condition,
            "badge": "Üretilmiş",
            "description": f"Üretilmiş: {intersection_type}, {vehicle_count} araç, {difficulty}, {special_condition}",
            "frames": frames,
            "road_geometry": road_geom,
        }

        out_path = GENERATED_PATH / f"{scenario_id}.json"
        with open(out_path, "w", encoding="utf-8") as fp:
            json.dump(result, fp, ensure_ascii=False)
        logger.info(f"Senaryo üretildi: {out_path}")

        return result
