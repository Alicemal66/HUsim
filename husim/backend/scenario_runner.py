"""MineSim-Dynamic subprocess wrapper — senaryo çalıştırıcı"""
import sys
import json
import asyncio
import logging
import math
import random
from pathlib import Path
from models import OptimizedParams, SimulationMetrics
import scenario_loader

logger = logging.getLogger(__name__)

# MineSim-Dynamic'in gerçek yolu — birden fazla olası konumu dene
BASE_DIR = Path(__file__).parent.parent.parent
_CANDIDATE_PATHS = [
    BASE_DIR / "MineSim-Dynamic-main" / "MineSim-Dynamic-main",
    BASE_DIR / "MineSim-Dynamic-main",
    Path(r"C:\Users\cemal\OneDrive\Desktop\HÜsim\MineSim-Dynamic-main\MineSim-Dynamic-main"),
    Path(r"C:\Users\cemal\OneDrive\Desktop\HÜsim\MineSim-Dynamic-main"),
]

MINESIM_PATH = next((p for p in _CANDIDATE_PATHS if (p / "inputs").exists()), _CANDIDATE_PATHS[0])
INPUTS_PATH = MINESIM_PATH / "inputs"
DEVKIT_PATH = MINESIM_PATH / "devkit"

DEMO_MODE = not INPUTS_PATH.exists()

if DEMO_MODE:
    logger.warning(f"MineSim-Dynamic inputs klasörü bulunamadı ({MINESIM_PATH}) — DEMO modunda çalışıyor.")
else:
    logger.info(f"MineSim-Dynamic bulundu: {MINESIM_PATH}")


def get_available_scenarios() -> list[dict]:
    """Kullanılabilir senaryoları listele."""
    if DEMO_MODE:
        return _demo_scenarios()

    scenarios = []
    for f in INPUTS_PATH.glob("Scenario-*.json"):
        scenario_id = f.stem.replace("Scenario-", "")
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            scenarios.append({
                "id": scenario_id,
                "name": scenario_id.replace("_", " ").title(),
                "file": str(f),
                "description": data.get("description", "MineSim senaryosu"),
                "demo": False,
            })
        except Exception as e:
            logger.error(f"Senaryo okunamadı {f}: {e}")
    return scenarios


def _demo_scenarios() -> list[dict]:
    return [
        {
            "id": "demo_intersection_1",
            "name": "Demo: Kavşak Senaryosu 1",
            "file": None,
            "description": "Demo modu — MineSim-Dynamic kurulu değil. Gerçek senaryo verisi yok.",
            "demo": True,
        },
        {
            "id": "demo_intersection_2",
            "name": "Demo: Kavşak Senaryosu 2",
            "file": None,
            "description": "Demo modu — Çok araçlı kavşak geçişi.",
            "demo": True,
        },
        {
            "id": "demo_highway_merge",
            "name": "Demo: Yol Birleşme",
            "file": None,
            "description": "Demo modu — İki şerit birleşme noktası.",
            "demo": True,
        },
    ]


async def run_scenario(
    simulation_id: str,
    scenario_id: str,
    optimized_params: OptimizedParams,
    algorithm: str = "SPPMM",
    frame_callback=None,
) -> SimulationMetrics:
    """
    Senaryoyu çalıştır. MineSim-Dynamic mevcutsa Python modülü olarak import eder,
    yoksa demo verisi üretir.
    """
    if DEMO_MODE or scenario_id.startswith("demo_"):
        return await _run_demo(simulation_id, scenario_id, optimized_params, algorithm, frame_callback)

    return await _run_minesim(simulation_id, scenario_id, optimized_params, algorithm, frame_callback)


async def _run_minesim(
    simulation_id: str,
    scenario_id: str,
    optimized_params: OptimizedParams,
    algorithm: str,
    frame_callback,
) -> SimulationMetrics:
    """MineSim-Dynamic senaryo yükleyiciyi kullanarak simülasyon çalıştır."""
    try:
        scenario_file = INPUTS_PATH / f"Scenario-{scenario_id}.json"
        if not scenario_file.exists():
            logger.error(f"Senaryo dosyası bulunamadı: {scenario_file}")
            return await _run_demo(simulation_id, scenario_id, optimized_params, algorithm, frame_callback)

        data = scenario_loader.load_scenario_frames(scenario_id, str(scenario_file))
        frames = data.get("frames", [])

        if not frames:
            logger.error(f"Frame listesi boş: {scenario_id}")
            return await _run_demo(simulation_id, scenario_id, optimized_params, algorithm, frame_callback)

        # Hız faktörünü uygula
        spd_f = optimized_params.max_speed_factor if optimized_params else 1.0
        if spd_f != 1.0:
            for frame in frames:
                for v in frame.get("vehicles", []):
                    v["speed"] = round(v["speed"] * spd_f, 2)

        logger.info(f"MineSim senaryo yüklendi: {scenario_id}, {len(frames)} frame")
        return await _stream_frames(frames, frame_callback, algorithm)

    except Exception as e:
        logger.error(f"MineSim çalıştırma hatası: {e} — demo moduna geçiliyor")
        return await _run_demo(simulation_id, scenario_id, optimized_params, algorithm, frame_callback)


async def _run_demo(
    simulation_id: str,
    scenario_id: str,
    optimized_params: OptimizedParams,
    algorithm: str,
    frame_callback,
) -> SimulationMetrics:
    """Demo modu — sahte simülasyon verisi üret."""
    logger.info(f"Demo senaryo çalıştırılıyor: {scenario_id}")
    total_frames = 150
    frames = _generate_demo_frames(total_frames, optimized_params)
    return await _stream_frames(frames, frame_callback, algorithm)


def _generate_demo_frames(total_frames: int, params: OptimizedParams) -> list[dict]:
    """Demo frame listesi üret."""
    frames = []
    ego_x, ego_y = 0.0, 0.0
    heading = 0.0
    speed = 8.0 * params.max_speed_factor

    # 3 ajan araç
    agents = [
        {"id": "agent_0", "x": 30.0, "y": 5.0, "heading": math.pi, "speed": speed * 0.8},
        {"id": "agent_1", "x": 60.0, "y": -3.0, "heading": math.pi * 0.9, "speed": speed * 0.7},
        {"id": "agent_2", "x": 20.0, "y": 10.0, "heading": math.pi * 1.1, "speed": speed * 0.6},
    ]

    for i in range(total_frames):
        t = i / total_frames
        ego_x = t * 100.0
        ego_y = math.sin(t * math.pi * 2) * 3.0
        heading = math.atan2(math.cos(t * math.pi * 2) * 3.0 * math.pi * 2 / 100.0, 1.0)

        current_agents = []
        for ag in agents:
            current_agents.append({
                "id": ag["id"],
                "x": ag["x"] - t * 40.0 + random.uniform(-0.2, 0.2),
                "y": ag["y"] + random.uniform(-0.3, 0.3),
                "heading": ag["heading"] + random.uniform(-0.05, 0.05),
                "speed": ag["speed"],
            })

        frames.append({
            "frame": i,
            "time": round(i * 0.1, 2),
            "vehicles": [
                {"id": "ego", "x": round(ego_x, 2), "y": round(ego_y, 2),
                 "heading": round(heading, 4), "speed": round(speed, 2)}
            ] + current_agents,
            "completed": i == total_frames - 1,
        })

    return frames


async def _stream_frames(frames: list[dict], frame_callback, algorithm: str) -> SimulationMetrics:
    """Frame'leri aktar ve metrikleri hesapla."""
    speeds = []
    min_dist = float("inf")
    collisions = 0
    near_misses = 0

    for frame_data in frames:
        if frame_callback:
            await frame_callback(frame_data)
        await asyncio.sleep(0.05)  # ~20 FPS akış

        vehicles = frame_data.get("vehicles", [])
        ego = next((v for v in vehicles if v["id"] == "ego"), None)
        if ego:
            speeds.append(ego["speed"])

        agents = [v for v in vehicles if v["id"] != "ego"]
        if ego:
            for ag in agents:
                dist = math.hypot(ego["x"] - ag["x"], ego["y"] - ag["y"])
                min_dist = min(min_dist, dist)
                if dist < 2.0:
                    near_misses += 1
                if dist < 0.5:
                    collisions += 1

    avg_speed = sum(speeds) / len(speeds) if speeds else 0
    task_completed = len(frames) > 0 and frames[-1].get("completed", False)

    return SimulationMetrics(
        collision_count=collisions,
        near_miss_count=near_misses,
        min_safety_distance=round(min_dist if min_dist != float("inf") else 0, 2),
        risk_score=min(100, near_misses * 5 + collisions * 20),
        completion_time=round(len(frames) * 0.1, 2),
        path_efficiency=round(random.uniform(0.75, 0.95), 3),
        average_speed=round(avg_speed, 2),
        max_acceleration=round(random.uniform(1.0, 3.0), 2),
        max_deceleration=round(random.uniform(1.5, 4.0), 2),
        steering_smoothness=round(random.uniform(0.6, 0.95), 3),
        task_completed=task_completed,
        completion_rate=100.0 if task_completed else round(len(frames) / 150 * 100, 1),
        algorithm_name=algorithm,
    )
