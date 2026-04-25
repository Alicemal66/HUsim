"""HÜsim — Senaryo yükleyici ve MineSim-Dynamic entegrasyonu"""
import json
import math
import random
import logging
from pathlib import Path
from typing import Optional

from engine_model import EngineModel
from orca_solver import ORCASolver

logger = logging.getLogger(__name__)

_POSSIBLE_MINESIM_PATHS = [
    Path(r"C:\Users\cemal\OneDrive\Desktop\HÜsim\MineSim-Dynamic-main\MineSim-Dynamic-main"),
    Path(r"C:\Users\cemal\OneDrive\Desktop\HÜsim\MineSim-Dynamic-main"),
    Path(__file__).parent.parent.parent / "MineSim-Dynamic-main" / "MineSim-Dynamic-main",
    Path(__file__).parent.parent.parent / "MineSim-Dynamic-main",
]

def _find_minesim_path() -> Path:
    for p in _POSSIBLE_MINESIM_PATHS:
        if (p / "inputs").exists():
            logger.info(f"MineSim-Dynamic bulundu: {p}")
            return p
    logger.warning("MineSim-Dynamic bulunamadı — demo modu aktif")
    return _POSSIBLE_MINESIM_PATHS[1]  # Fallback (boş da olsa)

MINESIM_PATH = _find_minesim_path()
INPUTS_PATH = MINESIM_PATH / "inputs"
GENERATED_PATH = Path(__file__).parent / "generated_scenarios"
GENERATED_PATH.mkdir(exist_ok=True)
DEMO_SCENARIOS_PATH = Path(__file__).parent / "demo_scenarios"

HAZIR_SENARYOLAR = [
    {"id": "dapai_intersection_1_3_4",     "name": "Dapai Kavşak 1-3-4",        "agents": 3, "type": "T"},
    {"id": "jiangtong_intersection_9_3_2", "name": "Jiangtong Kavşak 9-3-2",    "agents": 3, "type": "T"},
    {"id": "demo_t_3vehicles",             "name": "T Kavşak — 3 Araç",          "agents": 3, "type": "T",        "legacy": True},
    {"id": "demo_cross_5vehicles",         "name": "Çapraz Kavşak — 5 Araç",    "agents": 5, "type": "cross",    "legacy": True},
    {"id": "demo_narrow_collision",        "name": "Dar Yol Çarpışma",           "agents": 2, "type": "straight", "legacy": True},
    {"id": "demo_foggy_4vehicles",         "name": "Sisli Kavşak — 4 Araç",     "agents": 4, "type": "cross",    "legacy": True},
    {"id": "demo_emergency_brake",         "name": "Acil Fren Senaryosu",        "agents": 1, "type": "straight", "legacy": True},
    {"id": "demo_complex_8vehicles",       "name": "Karmaşık Kavşak — 8 Araç",  "agents": 8, "type": "complex",  "legacy": True},
    {"id": "demo_t_night",                 "name": "Gece Kavşak — 3 Araç",      "agents": 3, "type": "T",        "legacy": True},
    {"id": "demo_cross_rain",              "name": "Yağmurlu Çapraz Kavşak",     "agents": 4, "type": "cross",    "legacy": True},
    # Filo yönetim senaryoları
    {"id": "fleet_intersection",           "name": "Filo: Kavşak Koordinasyonu", "agents": 4, "type": "T",        "legacy": True},
    {"id": "fleet_narrow_pass",            "name": "Filo: Karşılıklı Geçiş",     "agents": 2, "type": "straight", "legacy": True},
    {"id": "fleet_convoy",                 "name": "Filo: Konvoy",               "agents": 3, "type": "straight", "legacy": True},
    {"id": "fleet_obstacle",               "name": "Filo: Acil Engel",           "agents": 1, "type": "straight", "legacy": True},
    {"id": "fleet_heavy_traffic",          "name": "Filo: Yoğun Trafik",         "agents": 5, "type": "cross",    "legacy": True},
    # Stabil senaryolar — geometrik olarak çarpışma imkansız
    {"id": "stable_parallel",    "name": "Paralel Yollar (Stabil)",      "agents": 2, "type": "straight", "stable": True},
    {"id": "stable_sequential",  "name": "Sıralı Geçiş (Stabil)",        "agents": 2, "type": "T",        "stable": True},
    {"id": "stable_convoy",      "name": "Konvoy (Stabil)",               "agents": 2, "type": "straight", "stable": True},
    {"id": "stable_opposite",    "name": "Karşılıklı Geçiş (Stabil)",    "agents": 1, "type": "straight", "stable": True},
    {"id": "stable_fleet",       "name": "Filo Koordinasyonu (Stabil)",   "agents": 4, "type": "cross",    "stable": True},
]


EXTENDED_SCENARIOS = [
    {"id": "ext_dapai_multi",      "name": "Dapai Çok Kamyonlu",        "agents": 5, "type": "intersection", "grade": 0},
    {"id": "ext_uphill_loaded",    "name": "Yokuş Yukarı Tam Yüklü",    "agents": 2, "type": "straight",     "grade": 8},
    {"id": "ext_downhill_brake",   "name": "Yokuş Aşağı Fren Testi",    "agents": 1, "type": "straight",     "grade": -10},
    {"id": "ext_jiangtong_multi",  "name": "Jiangtong Çok Kamyonlu",    "agents": 6, "type": "intersection", "grade": 0},
    {"id": "ext_loading_ramp",     "name": "Rampalı Yükleme İstasyonu", "agents": 2, "type": "straight",     "grade": 5},
    {"id": "ext_narrow_pass",      "name": "Dar Geçit Koordinasyonu",   "agents": 2, "type": "straight",     "grade": -3},
    {"id": "ext_emergency_stop",   "name": "Acil Duraksama",            "agents": 0, "type": "straight",     "grade": 0},
    {"id": "ext_morning_shift",    "name": "Sabah Vardiyası Filo",      "agents": 4, "type": "complex",      "grade": 0},
    {"id": "ext_fog_intersection", "name": "Sis Kavşağı",               "agents": 3, "type": "intersection", "grade": 0},
    {"id": "ext_full_fleet",       "name": "Tam Filo Operasyonu",       "agents": 7, "type": "complex",      "grade": 0},
]


def find_all_scenarios() -> list[dict]:
    """
    MineSim klasöründeki tüm gerçek senaryoları bul.
    Demo senaryolarla ve üretilmiş senaryolarla birleştir.
    """
    scenarios = []
    seen_ids = set()

    # 1) Gerçek MineSim dosyaları
    if INPUTS_PATH.exists():
        for f in sorted(INPUTS_PATH.glob("Scenario-*.json")):
            scenario_id = f.stem.replace("Scenario-", "")
            try:
                with open(f, encoding="utf-8") as fp:
                    data = json.load(fp)
                traj = data.get("TrajSegmentInfo", [])
                cnt = data.get("CntVehicle", len(traj))
                dt = data.get("dt", 0.1)
                max_t = data.get("max_t", 40.0)
                # En uzun araç süresi = frame sayısı
                max_end = max(
                    (t.get("EndTimeInScene", 0) for t in traj),
                    default=max_t
                )
                frame_count = int(max(max_end, max_t) / dt)
                scenarios.append({
                    "id": scenario_id,
                    "name": _pretty_name(scenario_id),
                    "path": str(f),
                    "source": "minesim_real",
                    "frame_count": frame_count,
                    "agent_count": cnt,
                    "total_time": max_t,
                    "scenario_type": data.get("SceneType", "intersection"),
                    "badge": "Gercek Veri",
                    "description": f"MineSim gerçek veri — {cnt} araç, {max_t:.1f}s",
                    "demo": False,
                })
                seen_ids.add(scenario_id)
            except Exception as e:
                logger.error(f"Senaryo okunamadı {f}: {e}")

    # 2) Hazır demo + real senaryolar (gerçek dosya bulunamayanlar için demo üret)
    for s in HAZIR_SENARYOLAR:
        if s["id"] not in seen_ids:
            demo_agents = s["agents"]
            is_stable = s.get("stable", False)
            if is_stable:
                demo_time = 50.0 if s["id"] == "stable_fleet" else 40.0
            else:
                demo_time = max(20.0, demo_agents * 6.0)
            demo_frames = max(200, demo_agents * 60, int(demo_time / 0.1))
            is_legacy = s.get("legacy", False)
            badge = "Stabil" if is_stable else ("Eski" if is_legacy else "Beta")
            scenarios.append({
                "id": s["id"],
                "name": s["name"],
                "path": None,
                "source": "demo",
                "frame_count": demo_frames,
                "agent_count": demo_agents,
                "total_time": demo_time,
                "scenario_type": s["type"],
                "badge": badge,
                "stable": is_stable,
                "description": (
                    f"Stabil senaryo — çarpışma imkansız, {demo_agents} araç"
                    if is_stable
                    else f"Demo senaryo — {demo_agents} araç, {s['type']} kavşak"
                ),
                "demo": True,
            })
            seen_ids.add(s["id"])

    # 3) Genişletilmiş senaryolar (Faza E)
    for s in EXTENDED_SCENARIOS:
        if s["id"] not in seen_ids:
            grade = s.get("grade", 0)
            agent_cnt = s["agents"]
            ext_time = max(30.0, agent_cnt * 7.0)
            if s["id"] == "ext_full_fleet":
                ext_time = 60.0
            ext_frames = max(300, agent_cnt * 70, int(ext_time / 0.1))
            grade_label = f"↗ +{grade}% eğim" if grade > 0 else (f"↘ {grade}% eğim" if grade < 0 else "→ düz")
            scenarios.append({
                "id": s["id"],
                "name": s["name"],
                "path": None,
                "source": "extended",
                "frame_count": ext_frames,
                "agent_count": agent_cnt,
                "total_time": ext_time,
                "scenario_type": s["type"],
                "badge": "Faza-E",
                "grade": grade,
                "grade_label": grade_label,
                "description": f"Faza E — {agent_cnt} araç, {grade_label}",
                "demo": False,
            })
            seen_ids.add(s["id"])

    # 4) Statik demo senaryolar (demo_scenarios/ klasörü — çarpışma imkansız)
    if DEMO_SCENARIOS_PATH.exists():
        for f in sorted(DEMO_SCENARIOS_PATH.glob("demo_*.json")):
            sid = f.stem
            if sid not in seen_ids:
                try:
                    with open(f, encoding="utf-8") as fp:
                        ddata = json.load(fp)
                    traj = ddata.get("TrajSegmentInfo", [])
                    cnt = ddata.get("CntVehicle", len(traj)) + 1  # +1 for ego
                    dt = ddata.get("dt", 0.1)
                    max_t = float(ddata.get("max_t", 20.0))
                    max_end = max((t.get("EndTimeInScene", 0) for t in traj), default=max_t)
                    frame_count = int(max(max_end, max_t) / dt)
                    name_map = {
                        "demo_01_parallel_roads":     "Paralel Yollar",
                        "demo_02_sequential_cross":   "Sıralı Geçiş",
                        "demo_03_convoy":             "Konvoy",
                        "demo_04_opposite_lanes":     "Karşılıklı Şeritler",
                        "demo_05_fleet_coordination": "Filo Koordinasyonu",
                    }
                    scenarios.append({
                        "id": sid,
                        "name": name_map.get(sid, sid),
                        "path": str(f),
                        "source": "demo_static",
                        "frame_count": frame_count,
                        "agent_count": cnt,
                        "total_time": max_t,
                        "scenario_type": ddata.get("SceneType", "straight"),
                        "badge": "Demo",
                        "stable": True,
                        "description": f"Statik demo — çarpışma imkansız, {cnt} araç",
                        "demo": True,
                    })
                    seen_ids.add(sid)
                except Exception as e:
                    logger.error(f"Statik demo okunamadı {f}: {e}")

    # 5) Üretilmiş senaryolar
    if GENERATED_PATH.exists():
        for f in sorted(GENERATED_PATH.glob("*.json")):
            gid = f.stem
            if gid not in seen_ids:
                try:
                    with open(f, encoding="utf-8") as fp:
                        gdata = json.load(fp)
                    scenarios.append({
                        "id": gid,
                        "name": gdata.get("name", gid),
                        "path": str(f),
                        "source": "generated",
                        "frame_count": gdata.get("frame_count", 200),
                        "agent_count": gdata.get("agent_count", 2),
                        "total_time": gdata.get("total_time", 20.0),
                        "scenario_type": gdata.get("scenario_type", "T"),
                        "badge": "Üretilmiş",
                        "description": gdata.get("description", "Üretilmiş senaryo"),
                        "demo": False,
                    })
                    seen_ids.add(gid)
                except Exception as e:
                    logger.error(f"Üretilmiş senaryo okunamadı {f}: {e}")

    return scenarios


def _add_engine_temps(data: dict, grade_percent: float = 0.0, ambient_temp: float = 20.0) -> dict:
    """Frame listesindeki her araç için motor sıcaklığı verisini ekle."""
    engines: dict[str, EngineModel] = {}
    for frame in data.get("frames", []):
        for v in frame.get("vehicles", []):
            vid = v["id"]
            if vid not in engines:
                engines[vid] = EngineModel()
            status = engines[vid].update(
                load_percent=v.get("load_percent", 50.0),
                grade_percent=grade_percent,
                ambient_temp=ambient_temp,
                current_speed=v.get("speed", 0.0),
            )
            v["engine_temp"] = status["temperature"]
            v["engine_status"] = status["status"]
            v["speed_limit_factor"] = status["speed_limit_factor"]
    return data


def load_scenario_frames(scenario_id: str, path: Optional[str], grade_percent: float = 0.0, ambient_temp: float = 20.0) -> dict:
    """
    MineSim log dosyasını yükle ve parse et. Yoksa demo üret.
    Standart HÜsim frame formatına normalize et.
    """
    data = _raw_load_scenario_frames(scenario_id, path)
    rg_grade = data.get("road_geometry", {}).get("grade", grade_percent)
    return _add_engine_temps(data, float(rg_grade or grade_percent), ambient_temp)


def _raw_load_scenario_frames(scenario_id: str, path: Optional[str]) -> dict:
    # Statik demo senaryo?
    demo_file = DEMO_SCENARIOS_PATH / f"{scenario_id}.json"
    if demo_file.exists():
        try:
            return _parse_minesim_file(scenario_id, str(demo_file))
        except Exception as e:
            logger.error(f"Statik demo parse hatası {demo_file}: {e}")

    # Üretilmiş senaryo?
    gen_file = GENERATED_PATH / f"{scenario_id}.json"
    if gen_file.exists():
        try:
            with open(gen_file, encoding="utf-8") as fp:
                gdata = json.load(fp)
            if "frames" in gdata:
                return gdata
        except Exception:
            pass

    # Stabil senaryo?
    if scenario_id.startswith("stable_"):
        return _generate_stable_scenario(scenario_id)

    # Filo senaryo?
    if scenario_id.startswith("fleet_"):
        return _generate_fleet_scenario(scenario_id)

    # Genişletilmiş senaryo?
    if scenario_id.startswith("ext_"):
        return _generate_extended_scenario(scenario_id)

    if path and Path(path).exists():
        try:
            return _parse_minesim_file(scenario_id, path)
        except Exception as e:
            logger.error(f"MineSim parse hatası {path}: {e}")

    # Hazır listeden agent sayısı bul
    meta = next((s for s in HAZIR_SENARYOLAR if s["id"] == scenario_id), None)
    agent_count = meta["agents"] if meta else 3
    scenario_type = meta["type"] if meta else _guess_type(scenario_id)
    return generate_rich_demo_frames(scenario_id, agent_count, scenario_type)


def _parse_minesim_file(scenario_id: str, path: str) -> dict:
    """
    MineSim JSON'unu okuyarak standart frame formatına dönüştür.

    JSON yapısı:
      - ego_info.start_states: EGO'nun başlangıç durumu (x, y, yaw_rad, v_mps)
      - ego_info.VehicleShapeInfo: EGO boyutları
      - goal: EGO'nun hedef poligonu {x:[...], y:[...]}
      - TrajSegmentInfo: NPC araçları (tümü); her biri states.x, y, yaw_rad, v_mps içerir
      - dt, max_t: zaman adımı ve toplam süre
    """
    with open(path, encoding="utf-8") as fp:
        data = json.load(fp)

    dt = data.get("dt", 0.1)
    max_t = float(data.get("max_t", 40.0))
    traj_list = data.get("TrajSegmentInfo", [])
    ego_info = data.get("ego_info", {})
    goal_data = data.get("goal", {})

    if not traj_list and not ego_info:
        raise ValueError("TrajSegmentInfo ve ego_info boş")

    # ── EGO başlangıç bilgileri ───────────────────────────────────────────────
    ego_start = ego_info.get("start_states", {})
    ego_shape = ego_info.get("VehicleShapeInfo", {})

    ego_x0 = float(ego_start.get("x", 0.0))
    ego_y0 = float(ego_start.get("y", 0.0))
    ego_yaw0 = float(ego_start.get("yaw_rad", 0.0))
    ego_v0 = float(ego_start.get("v_mps", 4.5))

    # ── Hedef merkezi (goal poligon ortalaması) ───────────────────────────────
    goal_xs = goal_data.get("x", [])
    goal_ys = goal_data.get("y", [])
    if goal_xs and goal_ys:
        goal_cx = sum(goal_xs) / len(goal_xs)
        goal_cy = sum(goal_ys) / len(goal_ys)
    else:
        # Yoksa başlangıç yönünde 100m ilerle
        goal_cx = ego_x0 + math.cos(ego_yaw0) * 100.0
        goal_cy = ego_y0 + math.sin(ego_yaw0) * 100.0

    # ── EGO trayektorisi: başlangıçtan hedefe bezier eğrisi ──────────────────
    ego_xs, ego_ys, ego_yaws, ego_speeds = _generate_ego_trajectory(
        ego_x0, ego_y0, ego_yaw0, ego_v0, goal_cx, goal_cy, dt, max_t
    )
    ego_n_frames = len(ego_xs)

    # ── NPC araçları ──────────────────────────────────────────────────────────
    npc_data_list = []
    npc_max_end = 0.0
    for i, traj in enumerate(traj_list):
        states = traj.get("states", {})
        xs_raw = states.get("x", [])
        ys_raw = states.get("y", [])
        # Gerçek anahtar isimleri: yaw_rad ve v_mps (heading/v değil)
        yaws_raw = states.get("yaw_rad", [])
        speeds_raw = states.get("v_mps", [])

        shape = traj.get("VehicleShapeInfo", {})
        start_time = float(traj.get("StartTimeInScene", 0.0))
        end_time = float(traj.get("EndTimeInScene", max_t))
        npc_max_end = max(npc_max_end, end_time)

        start_frame = int(round(start_time / dt))
        end_frame = int(round(end_time / dt))

        pos_x = [_extract_val(v) for v in xs_raw]
        pos_y = [_extract_val(v) for v in ys_raw]

        if yaws_raw:
            heads = [_extract_val(v) for v in yaws_raw]
        else:
            heads = _compute_headings(pos_x, pos_y)

        if speeds_raw:
            spds = [abs(_extract_val(v)) for v in speeds_raw]
        else:
            spds = _compute_speeds(pos_x, pos_y, dt)

        npc_data_list.append({
            "idx": i + 1,
            "is_ego": False,
            "length": float(shape.get("length", 5.0)),
            "width": float(shape.get("width", 2.0)),
            "vehicle_type": shape.get("vehicle_type", ""),
            "start_frame": start_frame,
            "end_frame": end_frame,
            "pos_x": pos_x,
            "pos_y": pos_y,
            "headings": heads,
            "speeds": spds,
        })

    # ── Toplam frame sayısı ───────────────────────────────────────────────────
    total_frames = max(ego_n_frames, int(max(npc_max_end, max_t) / dt) + 1)

    # ── Referans: EGO başlangıç pozisyonu ────────────────────────────────────
    ref_x = ego_x0
    ref_y = ego_y0

    # ── ORCA tabanlı EGO navigasyonu ─────────────────────────────────────────
    # NPC'ler sabit yörüngede (reciprocal=False); EGO ORCA ile kaçınır.

    ego_len_val = float(ego_shape.get("length", 9.0))
    ego_wid_val = float(ego_shape.get("width", 4.0))
    ego_radius = (ego_len_val + ego_wid_val) / 4.0
    ego_max_speed = max(ego_v0 * 1.5, 6.0)

    orca_minesim = ORCASolver(time_horizon=5.0, time_step=dt)

    # EGO dinamik durum (mutlak koordinat)
    ex_dyn = ego_x0
    ey_dyn = ego_y0
    evx_dyn = math.cos(ego_yaw0) * ego_v0
    evy_dyn = math.sin(ego_yaw0) * ego_v0

    # EGO için bezier trayektori — sadece yol geometrisi çizimi için kullanılır
    ego_xs_n = [x - ref_x for x in ego_xs]
    ego_ys_n = [y - ref_y for y in ego_ys]

    frames = []
    ego_actual_xs: list[float] = []
    ego_actual_ys: list[float] = []

    for frame_idx in range(total_frames):
        # EGO tercih edilen hız: hedefe doğru
        dx_g = goal_cx - ex_dyn
        dy_g = goal_cy - ey_dyn
        dist_g = math.hypot(dx_g, dy_g)

        if dist_g > 1.0:
            spd_pref = ego_max_speed * min(1.0, dist_g / 15.0)
            pvx = (dx_g / dist_g) * spd_pref
            pvy = (dy_g / dist_g) * spd_pref
        else:
            pvx, pvy = 0.0, 0.0

        # ORCA girdi listesi: EGO (reciprocal) + NPC'ler (non-reciprocal)
        agents_orca: list[dict] = [{
            "id": "ego",
            "x": ex_dyn, "y": ey_dyn,
            "vx": evx_dyn, "vy": evy_dyn,
            "pref_vx": pvx, "pref_vy": pvy,
            "radius": ego_radius,
            "max_speed": ego_max_speed,
            "reciprocal": True,
        }]

        for nd in npc_data_list:
            local_idx = frame_idx - nd["start_frame"]
            if 0 <= local_idx < len(nd["pos_x"]):
                nx_abs = nd["pos_x"][local_idx]
                ny_abs = nd["pos_y"][local_idx]
                if local_idx + 1 < len(nd["pos_x"]):
                    nvx_abs = (nd["pos_x"][local_idx + 1] - nx_abs) / dt
                    nvy_abs = (nd["pos_y"][local_idx + 1] - ny_abs) / dt
                elif local_idx > 0:
                    nvx_abs = (nx_abs - nd["pos_x"][local_idx - 1]) / dt
                    nvy_abs = (ny_abs - nd["pos_y"][local_idx - 1]) / dt
                else:
                    nvx_abs, nvy_abs = 0.0, 0.0
                npc_r = (float(nd["length"]) + float(nd["width"])) / 4.0
                npc_spd = nd["speeds"][local_idx] if local_idx < len(nd["speeds"]) else 4.0
                agents_orca.append({
                    "id": f"agent_{nd['idx']}",
                    "x": nx_abs, "y": ny_abs,
                    "vx": nvx_abs, "vy": nvy_abs,
                    "pref_vx": nvx_abs, "pref_vy": nvy_abs,
                    "radius": npc_r,
                    "max_speed": max(npc_spd * 1.5, 6.0),
                    "reciprocal": False,
                })

        new_vels_m = orca_minesim.compute_new_velocities(agents_orca)
        ego_vel_m = next(v for v in new_vels_m if v["id"] == "ego")

        evx_dyn = ego_vel_m["new_vx"]
        evy_dyn = ego_vel_m["new_vy"]
        ex_dyn += evx_dyn * dt
        ey_dyn += evy_dyn * dt

        ego_actual_xs.append(ex_dyn - ref_x)
        ego_actual_ys.append(ey_dyn - ref_y)

        # Frame oluştur
        vehicles = [{
            "id": "ego",
            "x": round(ex_dyn - ref_x, 3),
            "y": round(ey_dyn - ref_y, 3),
            "heading": round(ego_vel_m["new_heading"], 4),
            "speed": round(max(0.0, ego_vel_m["new_speed"]), 2),
            "length": ego_len_val,
            "width": ego_wid_val,
        }]

        for nd in npc_data_list:
            local_idx = frame_idx - nd["start_frame"]
            if local_idx < 0 or local_idx >= len(nd["pos_x"]):
                continue
            vx_n = nd["pos_x"][local_idx] - ref_x
            vy_n = nd["pos_y"][local_idx] - ref_y
            vh = nd["headings"][local_idx] if local_idx < len(nd["headings"]) else 0.0
            vs = nd["speeds"][local_idx] if local_idx < len(nd["speeds"]) else 0.0
            vehicles.append({
                "id": f"agent_{nd['idx']}",
                "x": round(vx_n, 3),
                "y": round(vy_n, 3),
                "heading": round(vh, 4),
                "speed": round(max(0.0, vs), 2),
                "length": nd["length"],
                "width": nd["width"],
            })

        if vehicles:
            frames.append({
                "frame": frame_idx,
                "time": round(frame_idx * dt, 2),
                "vehicles": vehicles,
                "completed": frame_idx == total_frames - 1,
            })

    # Yol geometrisi için EGO gerçek trayektorisini kullan
    ego_xs_n = ego_actual_xs
    ego_ys_n = ego_actual_ys

    # ── Yol geometrisi ────────────────────────────────────────────────────────
    all_vd_normalized = [
        {
            **nd,
            "pos_x": [x - ref_x for x in nd["pos_x"]],
            "pos_y": [y - ref_y for y in nd["pos_y"]],
        }
        for nd in npc_data_list
    ]
    # EGO trayektorisini de ekle
    all_vd_normalized.insert(0, {
        "pos_x": ego_xs_n,
        "pos_y": ego_ys_n,
        "is_ego": True,
    })
    road_geometry = _extract_road_geometry(all_vd_normalized, 0.0, 0.0)

    # Normalize edilmiş hedef poligon — frontend'de yeşil alan olarak çizilir
    goal_xs_n = [x - ref_x for x in goal_xs]
    goal_ys_n = [y - ref_y for y in goal_ys]
    if goal_xs_n and goal_ys_n:
        road_geometry["goal_polygon"] = [
            {"x": round(x, 2), "y": round(y, 2)}
            for x, y in zip(goal_xs_n, goal_ys_n)
        ]

    # Viewport sınırları: JSON sınırları + tüm trayektori noktaları
    # EGO başlangıcı (0,0) ve tüm NPC yolları kapsansın
    pad = 15.0
    all_traj_x = list(ego_xs_n)
    all_traj_y = list(ego_ys_n)
    for nd in all_vd_normalized[1:]:   # EGO hariç NPC'ler
        all_traj_x.extend(nd["pos_x"])
        all_traj_y.extend(nd["pos_y"])
    if goal_xs_n:
        all_traj_x.extend(goal_xs_n)
        all_traj_y.extend(goal_ys_n)

    traj_xmin = min(all_traj_x) - pad if all_traj_x else -pad
    traj_xmax = max(all_traj_x) + pad if all_traj_x else pad
    traj_ymin = min(all_traj_y) - pad if all_traj_y else -pad
    traj_ymax = max(all_traj_y) + pad if all_traj_y else pad

    json_xmin = data.get("x_min")
    json_xmax = data.get("x_max")
    json_ymin = data.get("y_min")
    json_ymax = data.get("y_max")

    x_min_n = min(json_xmin - ref_x if json_xmin is not None else traj_xmin, traj_xmin)
    x_max_n = max(json_xmax - ref_x if json_xmax is not None else traj_xmax, traj_xmax)
    y_min_n = min(json_ymin - ref_y if json_ymin is not None else traj_ymin, traj_ymin)
    y_max_n = max(json_ymax - ref_y if json_ymax is not None else traj_ymax, traj_ymax)

    road_geometry["viewport_bounds"] = {
        "x_min": round(x_min_n, 2),
        "x_max": round(x_max_n, 2),
        "y_min": round(y_min_n, 2),
        "y_max": round(y_max_n, 2),
    }

    return {
        "scenario_id": scenario_id,
        "source": "minesim_real",
        "total_frames": total_frames,
        "dt": dt,
        "agent_count": len(traj_list) + 1,  # NPC'ler + EGO
        "total_time": max_t,
        "frames": frames,
        "road_geometry": road_geometry,
    }


def _generate_ego_trajectory(
    x0: float, y0: float, yaw0: float, v0: float,
    goal_x: float, goal_y: float, dt: float, max_t: float
) -> tuple:
    """
    EGO için başlangıçtan hedefe kübik bezier eğrisi üret.
    Başlangıç yönünü, hedef yönünü dikkate alarak yumuşak geçiş sağlar.
    Döndürür: (xs, ys, yaws, speeds)
    """
    n_frames = int(max_t / dt) + 1
    dist = math.hypot(goal_x - x0, goal_y - y0)

    if dist < 0.1:
        # Başlangıç = hedef, yerinde dur
        xs = [x0] * n_frames
        ys = [y0] * n_frames
        yaws = [yaw0] * n_frames
        speeds = [0.0] * n_frames
        return xs, ys, yaws, speeds

    # Kontrol noktaları: başlangıç yönünden uzat, hedef yönüne yaklaş
    approach_angle = math.atan2(goal_y - y0, goal_x - x0)
    ctrl_dist = dist / 3.0

    p1x = x0 + math.cos(yaw0) * ctrl_dist
    p1y = y0 + math.sin(yaw0) * ctrl_dist
    p2x = goal_x - math.cos(approach_angle) * ctrl_dist
    p2y = goal_y - math.sin(approach_angle) * ctrl_dist

    xs = []
    ys = []
    for i in range(n_frames):
        t = i / (n_frames - 1) if n_frames > 1 else 0.0
        u = 1.0 - t
        bx = u**3 * x0 + 3*u**2*t * p1x + 3*u*t**2 * p2x + t**3 * goal_x
        by = u**3 * y0 + 3*u**2*t * p1y + 3*u*t**2 * p2y + t**3 * goal_y
        xs.append(bx)
        ys.append(by)

    yaws = _compute_headings(xs, ys)

    # Hız: başlangıç hızından kalkış, orta cruise, sonda yavaşla
    avg_speed = dist / max_t
    speeds = []
    for i in range(n_frames):
        frac = i / (n_frames - 1) if n_frames > 1 else 0.0
        # Trapezoid hız profili: %20 ivme, %60 cruise, %20 fren
        if frac < 0.2:
            s = v0 + (avg_speed * 1.1 - v0) * (frac / 0.2)
        elif frac > 0.8:
            s = avg_speed * 1.1 * (1.0 - (frac - 0.8) / 0.2) + 0.5
        else:
            s = avg_speed * 1.1
        speeds.append(max(0.0, s))

    return xs, ys, yaws, speeds


def generate_rich_demo_frames(scenario_id: str, agent_count: int, scenario_type: str = "T") -> dict:
    """
    ORCA tabanlı demo frame üretici.
    Tüm araçlar (EGO + ajanlar) her frame'de ORCA ile çarpışmasız hız hesaplar.
    EGO ve tüm ajanlar waypoint rotalarını takip eder.
    """
    dt = 0.1
    MAX_FRAMES = 900
    WAYPOINT_REACH_DIST = 5.0

    road_geom = _make_demo_road_geometry(scenario_type)
    ego_route = _make_ego_route(scenario_type)
    agent_routes = _make_agent_routes(scenario_type, agent_count)

    ego_len, ego_wid = 8.5, 3.5
    agent_sizes = [
        (random.choice([4.5, 5.4, 6.0]), random.choice([1.9, 2.0, 2.1]))
        for _ in range(len(agent_routes))
    ]

    orca = ORCASolver(time_horizon=4.0, time_step=dt)

    def _pref_vel(x: float, y: float, route: list, wp_idx: int, max_speed: float):
        """Rota üzerindeki sonraki waypoint'e tercih edilen hız vektörü hesapla."""
        # Mevcut waypoint'e yaklaşıldıysa sonrakine geç
        while wp_idx < len(route) - 1:
            gx, gy = float(route[wp_idx][0]), float(route[wp_idx][1])
            if math.hypot(gx - x, gy - y) < WAYPOINT_REACH_DIST:
                wp_idx += 1
            else:
                break

        if wp_idx >= len(route):
            return 0.0, 0.0, wp_idx

        gx, gy = float(route[wp_idx][0]), float(route[wp_idx][1])
        gspd = float(route[wp_idx][2]) if len(route[wp_idx]) > 2 else max_speed
        dist = math.hypot(gx - x, gy - y)

        if dist < 0.5:
            return 0.0, 0.0, wp_idx

        speed = gspd if gspd > 0.1 else max_speed
        speed = min(speed, max_speed)
        # Son waypoint'e yaklaşınca yavaşla
        if wp_idx == len(route) - 1 and dist < 12.0:
            speed = speed * max(0.1, dist / 12.0)

        nx_d = (gx - x) / dist
        ny_d = (gy - y) / dist
        return nx_d * speed, ny_d * speed, wp_idx

    # EGO başlangıç durumu
    ex = float(ego_route[0][0])
    ey = float(ego_route[0][1])
    evx, evy = 0.0, 0.0
    ego_wp = 1 if len(ego_route) > 1 else 0

    # Ajan başlangıç durumları
    agent_states = []
    for ai, route in enumerate(agent_routes):
        vlen, vwid = agent_sizes[ai]
        agent_states.append({
            "x": float(route[0][0]),
            "y": float(route[0][1]),
            "vx": 0.0, "vy": 0.0,
            "wp": 1 if len(route) > 1 else 0,
            "len": vlen, "wid": vwid,
            "route": route,
            "max_speed": 8.5,
        })

    frames = []
    ego_goal_frame: int | None = None

    for fi in range(MAX_FRAMES):
        # EGO tercih edilen hız
        pvx_e, pvy_e, ego_wp = _pref_vel(ex, ey, ego_route, ego_wp, 7.5)

        # Tüm araçları ORCA'ya gönder
        agents_input = [{
            "id": "ego",
            "x": ex, "y": ey,
            "vx": evx, "vy": evy,
            "pref_vx": pvx_e, "pref_vy": pvy_e,
            "radius": (ego_len + ego_wid) / 4.0,
            "max_speed": 9.0,
        }]

        for ai, st in enumerate(agent_states):
            pvx_a, pvy_a, st["wp"] = _pref_vel(
                st["x"], st["y"], st["route"], st["wp"], st["max_speed"]
            )
            agents_input.append({
                "id": f"agent_{ai + 1}",
                "x": st["x"], "y": st["y"],
                "vx": st["vx"], "vy": st["vy"],
                "pref_vx": pvx_a, "pref_vy": pvy_a,
                "radius": (st["len"] + st["wid"]) / 4.0,
                "max_speed": st["max_speed"],
            })

        new_vels = orca.compute_new_velocities(agents_input)
        vel_map = {v["id"]: v for v in new_vels}

        # EGO güncelle
        nv_e = vel_map["ego"]
        evx, evy = nv_e["new_vx"], nv_e["new_vy"]
        ex += evx * dt
        ey += evy * dt

        # Ajanları güncelle
        for ai, st in enumerate(agent_states):
            nv_a = vel_map[f"agent_{ai + 1}"]
            st["vx"] = nv_a["new_vx"]
            st["vy"] = nv_a["new_vy"]
            st["x"] += st["vx"] * dt
            st["y"] += st["vy"] * dt

        # EGO hedefe ulaştı mı?
        last_wp = ego_route[-1]
        if ego_goal_frame is None and math.hypot(ex - last_wp[0], ey - last_wp[1]) < 5.0:
            ego_goal_frame = fi

        is_completed = ego_goal_frame is not None and fi >= ego_goal_frame + 20

        # Frame oluştur
        eh = nv_e["new_heading"]
        es = nv_e["new_speed"]
        vehicles: list[dict] = [{
            "id": "ego",
            "x": round(ex, 3),
            "y": round(ey, 3),
            "heading": round(eh, 4),
            "speed": round(es, 2),
            "length": ego_len,
            "width": ego_wid,
        }]

        for ai, st in enumerate(agent_states):
            nv_a = vel_map[f"agent_{ai + 1}"]
            vehicles.append({
                "id": f"agent_{ai + 1}",
                "x": round(st["x"], 3),
                "y": round(st["y"], 3),
                "heading": round(nv_a["new_heading"], 4),
                "speed": round(nv_a["new_speed"], 2),
                "length": st["len"],
                "width": st["wid"],
            })

        frames.append({
            "frame": fi,
            "time": round(fi * dt, 2),
            "vehicles": vehicles,
            "completed": is_completed,
        })

        if is_completed:
            break

    total_frames = len(frames)
    return {
        "scenario_id": scenario_id,
        "source": "demo",
        "total_frames": total_frames,
        "dt": dt,
        "agent_count": agent_count,
        "total_time": round(total_frames * dt, 1),
        "frames": frames,
        "road_geometry": road_geom,
    }


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────

def _extract_val(v) -> float:
    """[[x]] veya [x] veya x → float"""
    if isinstance(v, list):
        return _extract_val(v[0]) if v else 0.0
    return float(v)


def _compute_headings(xs: list, ys: list) -> list:
    heads = []
    for i in range(len(xs)):
        if i < len(xs) - 1:
            dx = xs[i + 1] - xs[i]
            dy = ys[i + 1] - ys[i]
            heads.append(math.atan2(dy, dx))
        elif heads:
            heads.append(heads[-1])
        else:
            heads.append(0.0)
    return heads


def _compute_speeds(xs: list, ys: list, dt: float) -> list:
    spds = []
    for i in range(len(xs)):
        if i < len(xs) - 1:
            dx = xs[i + 1] - xs[i]
            dy = ys[i + 1] - ys[i]
            spds.append(math.hypot(dx, dy) / dt)
        elif spds:
            spds.append(spds[-1])
        else:
            spds.append(0.0)
    return spds


def _extract_road_geometry(vehicles_data: list, ref_x: float, ref_y: float) -> dict:
    """Araç yollarından MineSim tarzı yol geometrisi çıkar (drivable_polygons + centerlines)."""
    all_pts = []
    for vd in vehicles_data:
        for x, y in zip(vd["pos_x"], vd["pos_y"]):
            all_pts.append((x - ref_x, y - ref_y))

    if not all_pts:
        return _make_demo_road_geometry("T")

    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    road_width = 8.0
    lane_hw = 5.0  # yarı genişlik: 1 şerit ~5m

    # Araçları yatay/dikey gruba ayır; her araç için Y/X centroid kullan
    horiz_y_cents: list[float] = []   # her yatay aracın Y merkezi
    vert_x_cents: list[float] = []    # her dikey aracın X merkezi
    ego_start: tuple | None = None

    for vd in vehicles_data:
        pxs = vd["pos_x"]
        pys = vd["pos_y"]
        if len(pxs) < 2:
            continue
        dx = abs(max(pxs) - min(pxs))
        dy = abs(max(pys) - min(pys))
        if vd.get("is_ego"):
            ego_start = (pxs[0], pys[0])
        if dx >= dy:
            horiz_y_cents.append(sum(pys) / len(pys))
        else:
            vert_x_cents.append(sum(pxs) / len(pxs))

    drivable_polygons = []
    centerlines = []

    if horiz_y_cents:
        hy_c = sum(horiz_y_cents) / len(horiz_y_cents)
        # Şeritler arası aralık + şerit genişliği
        y_spread = (max(horiz_y_cents) - min(horiz_y_cents)) if len(horiz_y_cents) > 1 else 0
        hy_hw = max(y_spread / 2 + lane_hw, road_width / 2)
        hx_lo, hx_hi = min(xs) - 5, max(xs) + 5
        drivable_polygons.append({
            "points": [
                {"x": round(hx_lo, 1), "y": round(hy_c - hy_hw, 1)},
                {"x": round(hx_hi, 1), "y": round(hy_c - hy_hw, 1)},
                {"x": round(hx_hi, 1), "y": round(hy_c + hy_hw, 1)},
                {"x": round(hx_lo, 1), "y": round(hy_c + hy_hw, 1)},
            ],
            "type": "road",
        })
        centerlines.append({
            "points": [{"x": round(hx_lo, 1), "y": round(hy_c, 1)},
                       {"x": round(hx_hi, 1), "y": round(hy_c, 1)}],
            "type": "base",
        })
        # EGO dikey koldan geliyorsa: EGO başlangıcı ana yolun dışındaysa dikey kol ekle
        if ego_start and not vert_x_cents:
            ey0 = ego_start[1]
            if ey0 > hy_c + hy_hw + 2 or ey0 < hy_c - hy_hw - 2:
                # EGO ana yolun dışından geliyor — dikey kol çıkar
                vx_c = ego_start[0]
                if ey0 > hy_c + hy_hw:
                    vy_lo, vy_hi = hy_c + hy_hw, ey0 + 5
                else:
                    vy_lo, vy_hi = ey0 - 5, hy_c - hy_hw
                drivable_polygons.append({
                    "points": [
                        {"x": round(vx_c - lane_hw, 1), "y": round(vy_lo, 1)},
                        {"x": round(vx_c + lane_hw, 1), "y": round(vy_lo, 1)},
                        {"x": round(vx_c + lane_hw, 1), "y": round(vy_hi, 1)},
                        {"x": round(vx_c - lane_hw, 1), "y": round(vy_hi, 1)},
                    ],
                    "type": "road",
                })
                centerlines.append({
                    "points": [{"x": round(vx_c, 1), "y": round(vy_lo, 1)},
                               {"x": round(vx_c, 1), "y": round(vy_hi, 1)}],
                    "type": "connector",
                })
                # Kavşak: yalnızca kol girişi etrafında küçük alan
                jx_hw = lane_hw
                jy = vy_lo if ey0 > hy_c + hy_hw else vy_hi
                jy_lo = min(jy, hy_c) - jx_hw
                jy_hi = max(jy, hy_c) + jx_hw
                drivable_polygons.append({
                    "points": [
                        {"x": round(vx_c - jx_hw, 1), "y": round(jy_lo, 1)},
                        {"x": round(vx_c + jx_hw, 1), "y": round(jy_lo, 1)},
                        {"x": round(vx_c + jx_hw, 1), "y": round(jy_hi, 1)},
                        {"x": round(vx_c - jx_hw, 1), "y": round(jy_hi, 1)},
                    ],
                    "type": "intersection",
                })
    else:
        hy_c, hy_hw = cy, road_width / 2

    if vert_x_cents:
        vx_c = sum(vert_x_cents) / len(vert_x_cents)
        x_spread = (max(vert_x_cents) - min(vert_x_cents)) if len(vert_x_cents) > 1 else 0
        vx_hw = max(x_spread / 2 + lane_hw, road_width / 2)
        vy_lo, vy_hi = min(ys) - 5, hy_c
        drivable_polygons.append({
            "points": [
                {"x": round(vx_c - vx_hw, 1), "y": round(vy_lo, 1)},
                {"x": round(vx_c + vx_hw, 1), "y": round(vy_lo, 1)},
                {"x": round(vx_c + vx_hw, 1), "y": round(vy_hi, 1)},
                {"x": round(vx_c - vx_hw, 1), "y": round(vy_hi, 1)},
            ],
            "type": "road",
        })
        centerlines.append({
            "points": [{"x": round(vx_c, 1), "y": round(vy_lo, 1)},
                       {"x": round(vx_c, 1), "y": round(vy_hi, 1)}],
            "type": "connector",
        })
        drivable_polygons.append({
            "points": [
                {"x": round(vx_c - vx_hw, 1), "y": round(hy_c - hy_hw, 1)},
                {"x": round(vx_c + vx_hw, 1), "y": round(hy_c - hy_hw, 1)},
                {"x": round(vx_c + vx_hw, 1), "y": round(hy_c + hy_hw, 1)},
                {"x": round(vx_c - vx_hw, 1), "y": round(hy_c + hy_hw, 1)},
            ],
            "type": "intersection",
        })

    return {
        "type": "intersection",
        "center": {"x": round(cx, 1), "y": round(cy, 1)},
        "road_width": road_width,
        "drivable_polygons": drivable_polygons,
        "centerlines": centerlines,
        "segments": [
            {"from": {"x": round(min(xs), 1), "y": round(hy_c, 1)},
             "to": {"x": round(max(xs), 1), "y": round(hy_c, 1)}, "width": road_width},
            {"from": {"x": round(cx, 1), "y": round(min(ys), 1)},
             "to": {"x": round(cx, 1), "y": round(max(ys), 1)}, "width": road_width},
        ],
        "drivable_bounds": [
            {"x": round(min(xs) - road_width, 1), "y": round(cy - road_width / 2, 1)},
            {"x": round(max(xs) + road_width, 1), "y": round(cy + road_width / 2, 1)},
        ],
        "conflict_zones": [{"x": round(cx, 1), "y": round(cy, 1), "r": 12}],
    }


def _make_demo_road_geometry(scenario_type: str, road_half_w: float = 8.0) -> dict:
    """Demo yol geometrisi üret (MineSim tarzı drivable_polygons + centerlines dahil)."""
    rw = road_half_w  # half-width of each road arm
    base: dict = {"road_width": rw * 2, "center": {"x": 0, "y": 0}}

    if scenario_type == "T":
        base["type"] = "T"
        base["segments"] = [
            {"from": {"x": -60, "y": 0}, "to": {"x": 60, "y": 0}, "width": rw * 2},
            {"from": {"x": 20, "y": 0}, "to": {"x": 20, "y": -50}, "width": rw * 2},
        ]
        base["drivable_polygons"] = [
            {"type": "road", "points": [
                {"x": -65, "y": -rw}, {"x": 65, "y": -rw},
                {"x": 65, "y": rw}, {"x": -65, "y": rw}]},
            {"type": "road", "points": [
                {"x": 20 - rw, "y": -55}, {"x": 20 + rw, "y": -55},
                {"x": 20 + rw, "y": -rw}, {"x": 20 - rw, "y": -rw}]},
            {"type": "intersection", "points": [
                {"x": 20 - rw, "y": -rw}, {"x": 20 + rw, "y": -rw},
                {"x": 20 + rw, "y": rw}, {"x": 20 - rw, "y": rw}]},
        ]
        base["centerlines"] = [
            {"type": "base", "points": [{"x": -65, "y": 0}, {"x": 65, "y": 0}]},
            {"type": "connector", "points": [{"x": 20, "y": -55}, {"x": 20, "y": 0}]},
        ]
        base["conflict_zones"] = [{"x": 20, "y": 0, "r": 12}]
        base["viewport_bounds"] = {"x_min": -75, "x_max": 95, "y_min": -60, "y_max": 20}

    elif scenario_type == "cross":
        base["type"] = "cross"
        base["segments"] = [
            {"from": {"x": -60, "y": 0}, "to": {"x": 60, "y": 0}, "width": rw * 2},
            {"from": {"x": 0, "y": -60}, "to": {"x": 0, "y": 60}, "width": rw * 2},
        ]
        base["drivable_polygons"] = [
            {"type": "road", "points": [
                {"x": -65, "y": -rw}, {"x": 65, "y": -rw},
                {"x": 65, "y": rw}, {"x": -65, "y": rw}]},
            {"type": "road", "points": [
                {"x": -rw, "y": -65}, {"x": rw, "y": -65},
                {"x": rw, "y": 65}, {"x": -rw, "y": 65}]},
            {"type": "intersection", "points": [
                {"x": -rw, "y": -rw}, {"x": rw, "y": -rw},
                {"x": rw, "y": rw}, {"x": -rw, "y": rw}]},
        ]
        base["centerlines"] = [
            {"type": "base", "points": [{"x": -65, "y": 0}, {"x": 65, "y": 0}]},
            {"type": "connector", "points": [{"x": 0, "y": -65}, {"x": 0, "y": 65}]},
        ]
        base["conflict_zones"] = [{"x": 0, "y": 0, "r": 12}]
        base["viewport_bounds"] = {"x_min": -80, "x_max": 80, "y_min": -75, "y_max": 75}

    elif scenario_type == "straight":
        base["type"] = "straight"
        base["segments"] = [
            {"from": {"x": -80, "y": 0}, "to": {"x": 80, "y": 0}, "width": rw * 2},
        ]
        base["drivable_polygons"] = [
            {"type": "road", "points": [
                {"x": -85, "y": -rw}, {"x": 85, "y": -rw},
                {"x": 85, "y": rw}, {"x": -85, "y": rw}]},
        ]
        base["centerlines"] = [
            {"type": "base", "points": [{"x": -85, "y": 0}, {"x": 85, "y": 0}]},
        ]
        base["conflict_zones"] = [{"x": 0, "y": 0, "r": 8}]
        base["viewport_bounds"] = {"x_min": -95, "x_max": 115, "y_min": -20, "y_max": 20}

    else:  # complex
        base["type"] = "complex"
        base["segments"] = [
            {"from": {"x": -60, "y": 0}, "to": {"x": 60, "y": 0}, "width": rw * 2},
            {"from": {"x": 0, "y": -60}, "to": {"x": 0, "y": 60}, "width": rw * 2},
            {"from": {"x": -40, "y": -40}, "to": {"x": 0, "y": 0}, "width": rw * 1.6},
            {"from": {"x": 40, "y": -40}, "to": {"x": 0, "y": 0}, "width": rw * 1.6},
        ]
        base["drivable_polygons"] = [
            {"type": "road", "points": [
                {"x": -65, "y": -rw}, {"x": 65, "y": -rw},
                {"x": 65, "y": rw}, {"x": -65, "y": rw}]},
            {"type": "road", "points": [
                {"x": -rw, "y": -65}, {"x": rw, "y": -65},
                {"x": rw, "y": 65}, {"x": -rw, "y": 65}]},
            {"type": "intersection", "points": [
                {"x": -rw, "y": -rw}, {"x": rw, "y": -rw},
                {"x": rw, "y": rw}, {"x": -rw, "y": rw}]},
        ]
        base["centerlines"] = [
            {"type": "base", "points": [{"x": -65, "y": 0}, {"x": 65, "y": 0}]},
            {"type": "connector", "points": [{"x": 0, "y": -65}, {"x": 0, "y": 65}]},
        ]
        base["conflict_zones"] = [
            {"x": 0, "y": 0, "r": 15},
            {"x": -20, "y": -20, "r": 8},
        ]
        base["viewport_bounds"] = {"x_min": -80, "x_max": 80, "y_min": -80, "y_max": 75}

    return base


def _make_ego_route(scenario_type: str) -> list:
    """EGO aracı rotası: (x, y, speed) waypoint listesi. Şerit ayrımlı."""
    if scenario_type == "T":
        # EGO sağ şerit (y=-3): soldan gelip kavşakta aşağı döner
        return [
            (-55, -3, 0.0), (-30, -3, 8.0), (-5, -3, 6.0),
            (18, -3, 4.0), (18, -22, 5.0), (18, -46, 6.0),
        ]
    elif scenario_type == "cross":
        # EGO alt şerit (y=-3): soldan sağa
        return [
            (-55, -3, 0.0), (-15, -3, 8.5), (0, -3, 4.5),
            (15, -3, 7.0), (55, -3, 8.5),
        ]
    elif scenario_type == "straight":
        return [
            (-75, -3, 0.0), (-30, -3, 8.5), (0, -3, 3.0),
            (30, -3, 7.0), (75, -3, 8.5),
        ]
    else:  # complex
        return [
            (-55, -3, 0.0), (-20, -3, 7.0), (0, -3, 3.5),
            (0, -20, 5.0), (0, -55, 7.0),
        ]


def _make_agent_routes(scenario_type: str, count: int) -> list:
    """
    Ajan araç rotaları.
    Tüm başlangıç pozisyonları birbirinden ve EGO'dan en az 20 birim uzakta.
    Aynı rota üzerindeki ajanlar farklı başlangıç noktalarına yerleştirilmiş.
    """
    all_routes: dict[str, list] = {
        # T kavşak şerit düzeni:
        #   EGO: y=-3, soldan sağa sonra aşağı (x=18 kolundan)
        #   Karşı trafik: y=+3, sağdan sola
        #   Dal trafiği: x=22, aşağıdan yukarı
        "T": [
            # Ajan 0: sağdan sola, üst şerit (y=+3)
            [(65, 3, 0.0), (30, 3, 7.5), (5, 3, 5.0), (-10, 3, 4.5), (-35, 3, 7.0), (-65, 3, 7.5)],
            # Ajan 1: daldan yukarı (x=22) — kavşakta EGO ile çakışabilir → EGO bekler
            [(22, -52, 0.0), (22, -28, 6.0), (22, -8, 4.5), (22, 8, 5.0), (22, 28, 6.5)],
            # Ajan 2: sağdan sola, üst şerit (FARKLI başlangıç: 85 → aralık bırakır)
            [(85, 3, 0.0), (55, 3, 8.0), (25, 3, 5.0), (-5, 3, 4.5), (-30, 3, 7.5), (-60, 3, 8.5)],
            # Ajan 3: daldan aşağı (x=18)
            [(18, 28, 0.0), (18, 8, 6.5), (18, -18, 5.0), (18, -46, 6.0)],
            # Ajan 4: soldan sağa, alt şerit (arkadan gelir)
            [(-65, -3, 0.0), (-35, -3, 7.5), (0, -3, 5.5), (22, -3, 4.5), (22, -30, 6.0), (22, -52, 7.0)],
        ],
        # Çapraz kavşak:
        #   EGO: y=-3, soldan sağa
        #   Karşı: y=+3, sağdan sola
        #   Dikey: x=+3 aşağıdan yukarı, x=-3 yukarıdan aşağı
        "cross": [
            # Ajan 0: sağdan sola, üst şerit (y=+3)
            [(65, 3, 0.0), (25, 3, 8.0), (0, 3, 4.0), (-25, 3, 7.5), (-65, 3, 8.5)],
            # Ajan 1: aşağıdan yukarı, sağ kolon (x=+3) — EGO yoluyla kesişir
            [(3, -62, 0.0), (3, -22, 7.5), (3, 0, 4.0), (3, 22, 7.0), (3, 62, 8.0)],
            # Ajan 2: yukarıdan aşağı, sol kolon (x=-3) — EGO yoluyla kesişir
            [(-3, 62, 0.0), (-3, 22, 7.5), (-3, 0, 4.5), (-3, -22, 6.5), (-3, -58, 8.0)],
            # Ajan 3: sağdan sola, dış üst şerit (y=+9, yeterince uzak) — EGO ile çakışmaz
            [(78, 9, 0.0), (35, 9, 8.0), (0, 9, 4.5), (-28, 9, 6.5), (-65, 9, 8.0)],
            # Ajan 4: sağdan sola, dış alt şerit (y=-10) — EGO y=-3'ten lateral ayrımlı
            [(72, -10, 0.0), (30, -10, 7.5), (0, -10, 4.5), (-30, -10, 6.5), (-72, -10, 8.0)],
        ],
        "straight": [
            # Karşı yönde üst şerit (y=+3) — EGO'ya paralel, karşı yön
            [(78, 3, 0.0), (35, 3, 8.5), (0, 3, 4.0), (-35, 3, 7.5), (-78, 3, 8.5)],
            # Aynı yönde alt şerit, sağ tarafa çıkar (EGO'nun önünde durmaz)
            [(-65, -3, 0.0), (-15, -3, 8.0), (30, -3, 7.5), (65, -3, 8.5), (100, -3, 8.5)],
        ],
        # Karmaşık kavşak: EGO yolu (-55,-3)→(0,-3)→(0,-55); ajanlar EGO güzergahında yürümez
        "complex": [
            # Ajan 0: sağdan sola, yatay geçiş (y=-10 şeridinde, EGO y=-3'ten lateral ayrımlı)
            [(65, -10, 0.0), (25, -10, 7.5), (-5, -10, 4.0), (-35, -10, 6.5), (-65, -10, 8.0)],
            # Ajan 1: yukarıdan aşağı, x=+8 kolonu (EGO'nun x=0 kolunundan ayrı)
            [(8, 65, 0.0), (8, 25, 7.0), (8, 0, 3.5), (8, -28, 6.0), (8, -58, 8.0)],
            # Ajan 2: köşegen sol-üst'ten sağ-alt'a
            [(-48, 48, 0.0), (-22, 22, 6.5), (3, 3, 4.5), (22, -8, 6.5), (50, -30, 8.0)],
            # Ajan 3: yukarıdan aşağı, x=+15 kolonu (EGO'dan tamamen ayrı)
            [(15, 65, 0.0), (15, 25, 7.0), (15, 0, 4.0), (15, -25, 6.0), (15, -60, 8.0)],
            # Ajan 4: sağdan sola, üst şerit (y=+9)
            [(75, 9, 0.0), (32, 9, 7.5), (0, 9, 4.0), (-25, 9, 6.5), (-60, 9, 8.0)],
            # Ajan 5: soldan sağa, üst şerit (y=+14)
            [(-60, 14, 0.0), (-25, 14, 7.0), (0, 14, 4.5), (25, 14, 6.5), (60, 14, 8.0)],
            # Ajan 6: aşağıdan yukarı (x=+20, tamamen farklı kolon)
            [(20, -65, 0.0), (20, -25, 7.5), (20, 0, 4.0), (20, 25, 6.5), (20, 58, 8.0)],
            # Ajan 7: sağdan sola, alt şerit (y=-14)
            [(62, -14, 0.0), (28, -14, 7.5), (0, -14, 4.5), (-32, -14, 6.0), (-60, -14, 8.0)],
        ],
    }
    routes = all_routes.get(scenario_type, all_routes["T"])
    return [routes[i % len(routes)] for i in range(count)]


def _interpolate_route(waypoints: list, t: float, total_time: float) -> tuple:
    """Waypoints listesinden t anında (x, y, heading, speed) döndür."""
    if not waypoints:
        return 0.0, 0.0, 0.0, 0.0

    n = len(waypoints)
    if n == 1:
        w = waypoints[0]
        return w[0], w[1], 0.0, w[2]

    progress = min(1.0, t / total_time)
    segment_len = 1.0 / (n - 1)
    seg_idx = min(n - 2, int(progress / segment_len))
    local_t = (progress - seg_idx * segment_len) / segment_len
    local_t = max(0.0, min(1.0, local_t))

    # Cubic ease-in-out
    local_t = local_t * local_t * (3 - 2 * local_t)

    w0 = waypoints[seg_idx]
    w1 = waypoints[seg_idx + 1]
    x = w0[0] + (w1[0] - w0[0]) * local_t
    y = w0[1] + (w1[1] - w0[1]) * local_t
    spd = w0[2] + (w1[2] - w0[2]) * local_t

    dx = w1[0] - w0[0]
    dy = w1[1] - w0[1]
    heading = math.atan2(dy, dx) if (abs(dx) + abs(dy)) > 0.01 else 0.0

    return x, y, heading, spd


def _pretty_name(scenario_id: str) -> str:
    """ID'den güzel isim üret."""
    name_map = {
        "dapai_intersection_1_3_4": "Dapai Kavşak 1-3-4",
        "jiangtong_intersection_9_3_2": "Jiangtong Kavşak 9-3-2",
    }
    if scenario_id in name_map:
        return name_map[scenario_id]
    return scenario_id.replace("_", " ").title()


def _guess_type(scenario_id: str) -> str:
    if "cross" in scenario_id:
        return "cross"
    if "straight" in scenario_id or "narrow" in scenario_id or "highway" in scenario_id:
        return "straight"
    if "complex" in scenario_id:
        return "complex"
    return "T"


# ── Filo Senaryo Yardımcıları ─────────────────────────────────────────────────

def _rlen(route: list) -> float:
    """Rota toplam uzunluğu."""
    total = 0.0
    for i in range(len(route) - 1):
        dx = route[i + 1][0] - route[i][0]
        dy = route[i + 1][1] - route[i][1]
        total += math.hypot(dx, dy)
    return total


def _rpos(route: list, dist: float) -> tuple:
    """Rota üzerinde belirli mesafedeki (x, y, heading) değerini döndür."""
    remaining = max(0.0, dist)
    for i in range(len(route) - 1):
        dx = route[i + 1][0] - route[i][0]
        dy = route[i + 1][1] - route[i][1]
        seg = math.hypot(dx, dy)
        if seg < 1e-4:
            continue
        if remaining <= seg + 1e-9:
            t_seg = remaining / seg
            x = route[i][0] + dx * t_seg
            y = route[i][1] + dy * t_seg
            return x, y, math.atan2(dy, dx)
        remaining -= seg
    last = route[-1]
    if len(route) >= 2:
        h = math.atan2(route[-1][1] - route[-2][1], route[-1][0] - route[-2][0])
    else:
        h = 0.0
    return last[0], last[1], h


def _fleet_sim_frames(vehicles_cfg: list, dt: float, total_time: float) -> list:
    """
    Öncelik tabanlı filo simülatörü.
    Yüksek öncelikli araçlar önce konumlanır; düşük öncelikliler çakışma varsa bekler.
    vehicles_cfg her eleman: {id, route, speed, length, width, priority, vehicle_type, start_delay}
    """
    total_frames = int(total_time / dt)

    # Durum nesneleri
    states = []
    for vc in vehicles_cfg:
        states.append({
            "cfg": vc,
            "dist": max(0.0, vc.get("start_dist", 0.0)),
            "total_dist": _rlen(vc["route"]),
            "status": "waiting" if vc.get("start_delay", 0) > 0 else "moving",
            "wait_timer": float(vc.get("start_delay", 0.0)),
            "speed": 0.0,
            "x": vc["route"][0][0],
            "y": vc["route"][0][1],
            "heading": 0.0,
        })

    frames = []

    for fi in range(total_frames):
        # Öncelik sırasına göre sırala (en yüksek önce = en düşük sayı)
        sorted_idx = sorted(range(len(states)), key=lambda k: states[k]["cfg"]["priority"])

        committed: list[dict] = []

        for idx in sorted_idx:
            st = states[idx]
            vc = st["cfg"]

            # Bekleme süresi
            if st["wait_timer"] > 0:
                st["wait_timer"] = max(0.0, st["wait_timer"] - dt)
                if st["wait_timer"] > 0:
                    x, y, h = _rpos(vc["route"], st["dist"])
                    st["x"], st["y"], st["heading"] = x, y, h
                    st["speed"] = 0.0
                    st["status"] = "waiting"
                    committed.append({**st, "len": vc["length"]})
                    continue

            # Rota sonu
            if st["dist"] >= st["total_dist"] - 0.05:
                x, y, h = _rpos(vc["route"], st["total_dist"])
                st["x"], st["y"], st["heading"] = x, y, h
                st["speed"] = 0.0
                st["status"] = "completed"
                committed.append({**st, "len": vc["length"]})
                continue

            # Bir sonraki pozisyon
            next_dist = min(st["total_dist"], st["dist"] + vc["speed"] * dt)
            nx, ny, nh = _rpos(vc["route"], next_dist)

            # Çakışma kontrolü
            blocked = False
            committed_set = {cs.get("id") for cs in committed}

            # 1) Commit edilmiş (yüksek öncelikli) araçlar — tam güvenli mesafe
            for cs in committed:
                d = math.hypot(nx - cs["x"], ny - cs["y"])
                heading_diff = abs(((nh - cs["heading"]) + math.pi) % (2 * math.pi) - math.pi)
                if heading_diff < 1.0:
                    min_safe = max((vc["length"] + cs["len"]) * 0.55 + 3.0, 9.0)
                else:
                    min_safe = max((vc["length"] + cs["len"]) * 0.5 + 5.0, 14.0)
                if d < min_safe:
                    blocked = True
                    break

            # 2) Henüz işlenmemiş araçların mevcut pozisyonları — sadece fiziksel çakışma eşiği
            if not blocked:
                for other_st in states:
                    other_vc = other_st["cfg"]
                    if other_vc["id"] == vc["id"] or other_vc["id"] in committed_set:
                        continue
                    d = math.hypot(nx - other_st["x"], ny - other_st["y"])
                    heading_diff = abs(((nh - other_st["heading"]) + math.pi) % (2 * math.pi) - math.pi)
                    # Yalnızca karşıdan gelen aynı şerit senaryosunda (heading_diff > 2.5 → karşı yön)
                    # fiziksel boyut tabanlı dar eşik kullan
                    if heading_diff > 2.5:
                        phys_safe = (vc["length"] + other_vc["length"]) * 0.5 + 2.0
                        if d < phys_safe:
                            blocked = True
                            break

            # Sarı bölge: min_safe'nin 1.8 katı mesafede yavaşla
            slowing = False
            if not blocked:
                for cs in committed:
                    d = math.hypot(nx - cs["x"], ny - cs["y"])
                    heading_diff = abs(((nh - cs["heading"]) + math.pi) % (2 * math.pi) - math.pi)
                    if heading_diff < 1.0:
                        warn_safe = max((vc["length"] + cs["len"]) * 0.55 + 3.0, 9.0) * 1.8
                    else:
                        warn_safe = max((vc["length"] + cs["len"]) * 0.5 + 5.0, 14.0) * 1.8
                    if d < warn_safe:
                        slowing = True
                        break

            if blocked:
                x, y, h = _rpos(vc["route"], st["dist"])
                st["x"], st["y"], st["heading"] = x, y, h
                st["speed"] = 0.0
                st["status"] = "waiting"
            elif slowing:
                st["dist"] = next_dist
                x, y, h = _rpos(vc["route"], next_dist)
                st["x"], st["y"], st["heading"] = x, y, h
                st["speed"] = vc["speed"] * 0.5
                st["status"] = "slowing"
            else:
                st["dist"] = next_dist
                x, y, h = _rpos(vc["route"], next_dist)
                st["x"], st["y"], st["heading"] = x, y, h
                st["speed"] = vc["speed"]
                st["status"] = "moving"

            committed.append({**st, "len": vc["length"]})

        # Frame oluştur
        vehicles = []
        for st in states:
            vc = st["cfg"]
            vehicles.append({
                "id": vc["id"],
                "x": round(st["x"], 3),
                "y": round(st["y"], 3),
                "heading": round(st["heading"], 4),
                "speed": round(max(0.0, st["speed"]), 2),
                "length": vc["length"],
                "width": vc["width"],
                "priority": vc["priority"],
                "status": st["status"],
                "vehicle_type": vc.get("vehicle_type", ""),
            })

        frames.append({
            "frame": fi,
            "time": round(fi * dt, 2),
            "vehicles": vehicles,
            "completed": fi == total_frames - 1,
        })

    return frames


def _generate_fleet_scenario(scenario_id: str) -> dict:
    """Filo senaryo yönlendirici."""
    generators = {
        "fleet_intersection": _gen_fleet_intersection,
        "fleet_narrow_pass": _gen_fleet_narrow_pass,
        "fleet_convoy": _gen_fleet_convoy,
        "fleet_obstacle": _gen_fleet_obstacle,
        "fleet_heavy_traffic": _gen_fleet_heavy_traffic,
    }
    gen = generators.get(scenario_id)
    if gen:
        return gen()
    return generate_rich_demo_frames(scenario_id, 3, "T")


def _gen_fleet_intersection() -> dict:
    """Senaryo 1 — Kavşak Koordinasyonu: EGO en yüksek öncelik, ajanlar bekler."""
    dt = 0.1
    total_time = 28.0

    vehicles = [
        {
            "id": "ego",
            "route": [(-65, -4), (-30, -4), (17, -4), (17, -30), (17, -58)],
            "speed": 7.0,
            "length": 9.0, "width": 4.0,
            "priority": 1,
            "vehicle_type": "MineTruck",
            "start_delay": 0.0,
        },
        {
            "id": "agent_1",
            "route": [(22, -58), (22, -22), (22, 0), (22, 30)],
            "speed": 6.0,
            "length": 4.49, "width": 1.877,
            "priority": 3,
            "vehicle_type": "PickupSuv",
            "start_delay": 0.0,
        },
        {
            "id": "agent_2",
            "route": [(72, 4), (30, 4), (5, 4), (-20, 4), (-68, 4)],
            "speed": 7.0,
            "length": 4.49, "width": 1.877,
            "priority": 3,
            "vehicle_type": "PickupSuv",
            "start_delay": 0.0,
        },
        {
            "id": "agent_3",
            "route": [(-72, 4), (-28, 4), (22, 4), (68, 4)],
            "speed": 7.5,
            "length": 4.49, "width": 1.877,
            "priority": 2,
            "vehicle_type": "PickupSuv",
            "start_delay": 2.0,
        },
    ]

    frames = _fleet_sim_frames(vehicles, dt, total_time)

    road_geom = _make_demo_road_geometry("T")
    road_geom["center"] = {"x": 17, "y": 0}
    road_geom["conflict_zones"] = [{"x": 17, "y": 0, "r": 14}]
    road_geom["viewport_bounds"] = {"x_min": -76, "x_max": 78, "y_min": -65, "y_max": 36}

    return {
        "scenario_id": "fleet_intersection",
        "source": "demo",
        "total_frames": len(frames),
        "dt": dt,
        "agent_count": 4,
        "total_time": total_time,
        "frames": frames,
        "road_geometry": road_geom,
    }


def _gen_fleet_narrow_pass() -> dict:
    """Senaryo 2 — Karşılıklı Geçiş: dar yolda karşıdan gelen araçlar."""
    dt = 0.1
    total_time = 22.0

    # EGO soldan sağa, en yüksek öncelik
    # Agent 1 sağdan sola, ortada bekleme noktasına çekilerek EGO'yu geçirir
    # Geçiş noktası: x=30 (burada durur)
    vehicles = [
        {
            "id": "ego",
            "route": [(-85, 0), (-40, 0), (0, 0), (40, 0), (85, 0)],
            "speed": 7.5,
            "length": 9.0, "width": 4.0,
            "priority": 1,
            "vehicle_type": "MineTruck",
            "start_delay": 0.0,
        },
        {
            "id": "agent_1",
            "route": [(85, 0), (35, 0), (35, 0), (-85, 0)],
            "speed": 6.0,
            "length": 4.49, "width": 1.877,
            "priority": 2,
            "vehicle_type": "PickupSuv",
            "start_delay": 0.0,
        },
        {
            "id": "agent_2",
            "route": [(105, 0), (50, 0), (50, 0), (-85, 0)],
            "speed": 6.0,
            "length": 4.49, "width": 1.877,
            "priority": 3,
            "vehicle_type": "PickupSuv",
            "start_delay": 0.0,
        },
    ]

    frames = _fleet_sim_frames(vehicles, dt, total_time)

    road_geom = _make_demo_road_geometry("straight")
    road_geom["road_width"] = 6.0
    road_geom["conflict_zones"] = [{"x": 0, "y": 0, "r": 10}]
    road_geom["viewport_bounds"] = {"x_min": -92, "x_max": 112, "y_min": -20, "y_max": 20}

    return {
        "scenario_id": "fleet_narrow_pass",
        "source": "demo",
        "total_frames": len(frames),
        "dt": dt,
        "agent_count": 3,
        "total_time": total_time,
        "frames": frames,
        "road_geometry": road_geom,
    }


def _gen_fleet_convoy() -> dict:
    """Senaryo 3 — Konvoy: 4 araç aynı rotada, sabit aralıklı."""
    dt = 0.1
    total_time = 20.0
    total_frames = int(total_time / dt)

    # Araçların gerisinde başlaması için rota uzatıldı
    gap = 18.0   # hedef araç mesafesi (m)
    route = [(-85 - 3 * gap, -2), (-85, -2), (-40, -2), (0, -2), (40, -2), (85, -2)]
    route_len = _rlen(route)
    min_gap = 7.0
    max_speed = 8.5

    # Başlangıç mesafeleri: ego 3*gap ileriden, ajanlar sıralı
    ego_dist = 3 * gap
    agent_dists = [2 * gap, 1 * gap, 0.0]
    ego_speed = max_speed
    agent_speeds = [0.0, 0.0, 0.0]

    frames = []

    for fi in range(total_frames):
        t = fi * dt

        # EGO hız profili: t=7-12 arasında yavaşla (simüle edilmiş trafik yoğunluğu)
        if 7.0 < t < 12.0:
            target_ego = 2.0
        else:
            target_ego = max_speed
        # Yumuşak hız geçişi
        ego_speed = 0.88 * ego_speed + 0.12 * target_ego
        ego_dist += ego_speed * dt

        # Ajanlar: önceki aracı takip et, mesafeyi koru
        leader_dists = [ego_dist] + agent_dists
        leader_lens = [9.0, 4.5, 4.5]
        for i in range(3):
            ld = leader_dists[i]
            current_gap = ld - agent_dists[i] - leader_lens[i] - 1.0
            if current_gap <= min_gap:
                target_a = 0.0
            elif current_gap < gap:
                target_a = max_speed * (current_gap - min_gap) / (gap - min_gap)
            else:
                target_a = max_speed
            agent_speeds[i] = 0.85 * agent_speeds[i] + 0.15 * target_a
            agent_speeds[i] = max(0.0, agent_speeds[i])
            agent_dists[i] += agent_speeds[i] * dt

        # EGO pozisyonu
        ex, ey, eh = _rpos(route, max(0.0, ego_dist))
        vehicles = [{
            "id": "ego",
            "x": round(ex, 3),
            "y": round(ey, 3),
            "heading": round(eh, 4),
            "speed": round(max(0.0, ego_speed), 2),
            "length": 9.0,
            "width": 4.0,
            "priority": 1,
            "status": "slowing" if target_ego < max_speed else "moving",
            "vehicle_type": "MineTruck",
        }]

        for i in range(3):
            ax, ay, ah = _rpos(route, max(0.0, agent_dists[i]))
            spd = agent_speeds[i]
            status = "moving" if spd > 0.5 else "waiting"
            if 0 < spd < 3.0:
                status = "slowing"
            vehicles.append({
                "id": f"agent_{i + 1}",
                "x": round(ax, 3),
                "y": round(ay, 3),
                "heading": round(ah, 4),
                "speed": round(spd, 2),
                "length": 4.5,
                "width": 1.9,
                "priority": 2 + i,
                "status": status,
                "vehicle_type": "PickupSuv",
            })

        frames.append({
            "frame": fi,
            "time": round(t, 2),
            "vehicles": vehicles,
            "completed": fi == total_frames - 1,
        })

    road_geom = _make_demo_road_geometry("straight", road_half_w=12.0)
    road_geom["center"] = {"x": 0, "y": -2}
    road_geom["conflict_zones"] = []
    road_geom["viewport_bounds"] = {"x_min": -100, "x_max": 100, "y_min": -25, "y_max": 22}

    return {
        "scenario_id": "fleet_convoy",
        "source": "demo",
        "total_frames": total_frames,
        "dt": dt,
        "agent_count": 4,
        "total_time": total_time,
        "frames": frames,
        "road_geometry": road_geom,
    }


def _gen_fleet_obstacle() -> dict:
    """Senaryo 4 — Acil Engel: EGO rotasında statik engel çıkar, durur/geçer."""
    dt = 0.1
    total_time = 22.0
    total_frames = int(total_time / dt)

    # EGO: soldan sağa, x=-5'te engel var, t=10 sonra geçiş yolu açılır
    # Rotayı 25m uzatarak agent_1'in geride başlamasını sağla
    ego_route_phase1 = [(-110, 0), (-85, 0), (-10, 0)]
    ego_route_bypass = [(-10, 0), (-5, 5), (10, 5), (20, 0), (85, 0)]
    OBSTACLE_CLEAR_T = 10.0  # engel bu t'den sonra yok

    ego_speed = 7.5
    ego_state = "approaching"  # approaching → waiting → bypassing → moving
    ego_dist_p1 = 25.0  # ego rotanın 25m ilerisinden başlar (agent_1'in başlangıç noktasının önünde)
    ego_dist_bp = 0.0
    ego_phase = 1
    ego_rlen_p1 = _rlen(ego_route_phase1)

    # Agent 1: EGO'nun 25m gerisinde başlar (rota başlangıcından)
    a1_dist = 0.0  # rotanın başından başlar, ego 25m ileride
    a1_speed = 0.0
    max_speed = 7.5
    min_gap = 8.0
    gap = 20.0

    # Sabit engel: x=0, y=0 (t < OBSTACLE_CLEAR_T arasında görünür)
    OBSTACLE_X, OBSTACLE_Y = 0.0, 0.0

    frames = []

    for fi in range(total_frames):
        t = fi * dt
        obstacle_active = t < OBSTACLE_CLEAR_T

        # ── EGO hareketi ──────────────────────────────────────────────────────
        if ego_phase == 1:
            # Faz 1: engele yaklaşıyor
            dist_to_obs = math.hypot(
                ego_route_phase1[-1][0] - OBSTACLE_X,
                ego_route_phase1[-1][1] - OBSTACLE_Y
            )
            remaining_route = ego_rlen_p1 - ego_dist_p1

            if obstacle_active and remaining_route < 12.0:
                ego_state = "waiting"
                ego_speed = max(0.0, ego_speed - 0.5 * dt * 10)
            elif not obstacle_active and ego_state == "waiting":
                ego_state = "bypassing"
                ego_phase = 2
                ego_dist_bp = 0.0
            elif ego_state == "approaching":
                ego_dist_p1 = min(ego_rlen_p1, ego_dist_p1 + ego_speed * dt)
                if ego_dist_p1 >= ego_rlen_p1 - 12.0 and obstacle_active:
                    ego_state = "waiting"

            ex, ey, eh = _rpos(ego_route_phase1, min(ego_dist_p1, ego_rlen_p1))

        else:
            # Faz 2: bypass yoluyla geçiyor
            bp_len = _rlen(ego_route_bypass)
            ego_speed = min(max_speed, ego_speed + 0.5)
            ego_dist_bp = min(bp_len, ego_dist_bp + ego_speed * dt)
            ex, ey, eh = _rpos(ego_route_bypass, ego_dist_bp)
            ego_state = "moving" if ego_dist_bp > 1.0 else "bypassing"

        actual_ego_speed = ego_speed if ego_state in ("moving", "bypassing", "approaching") else 0.0

        # ── Agent 1 ────────────────────────────────────────────────────────────
        ego_effective_dist = ego_dist_p1 if ego_phase == 1 else (ego_rlen_p1 + ego_dist_bp)
        current_gap = ego_effective_dist - a1_dist - 9.0 - 1.0
        if current_gap <= min_gap:
            a1_target = 0.0
        elif current_gap < gap:
            a1_target = max_speed * (current_gap - min_gap) / (gap - min_gap)
        else:
            a1_target = max_speed
        a1_speed = 0.85 * a1_speed + 0.15 * a1_target
        a1_speed = max(0.0, a1_speed)
        a1_dist += a1_speed * dt

        a1x, a1y, a1h = _rpos(ego_route_phase1, max(0.0, min(a1_dist, ego_rlen_p1)))

        # ── Engel aracı (görünür veya gizli) ──────────────────────────────────
        vehicles = [{
            "id": "ego",
            "x": round(ex, 3),
            "y": round(ey, 3),
            "heading": round(eh, 4),
            "speed": round(max(0.0, actual_ego_speed), 2),
            "length": 9.0,
            "width": 4.0,
            "priority": 1,
            "status": ego_state,
            "vehicle_type": "MineTruck",
        }, {
            "id": "agent_1",
            "x": round(a1x, 3),
            "y": round(a1y, 3),
            "heading": round(a1h, 4),
            "speed": round(a1_speed, 2),
            "length": 4.5,
            "width": 1.9,
            "priority": 2,
            "status": "moving" if a1_speed > 0.5 else "waiting",
            "vehicle_type": "PickupSuv",
        }]

        if obstacle_active:
            vehicles.append({
                "id": "obstacle",
                "x": OBSTACLE_X,
                "y": OBSTACLE_Y,
                "heading": 0.0,
                "speed": 0.0,
                "length": 5.0,
                "width": 3.0,
                "priority": 99,
                "status": "waiting",
                "vehicle_type": "StaticObstacle",
            })

        frames.append({
            "frame": fi,
            "time": round(t, 2),
            "vehicles": vehicles,
            "completed": fi == total_frames - 1,
        })

    road_geom = _make_demo_road_geometry("straight")
    road_geom["conflict_zones"] = [{"x": 0, "y": 0, "r": 12}]
    road_geom["viewport_bounds"] = {"x_min": -92, "x_max": 92, "y_min": -20, "y_max": 20}

    return {
        "scenario_id": "fleet_obstacle",
        "source": "demo",
        "total_frames": total_frames,
        "dt": dt,
        "agent_count": 2,
        "total_time": total_time,
        "frames": frames,
        "road_geometry": road_geom,
    }


def _gen_fleet_heavy_traffic() -> dict:
    """Senaryo 5 — Yoğun Trafik: 5 ajan + EGO, çapraz kavşak, koordinatör yönetir."""
    dt = 0.1
    total_time = 25.0

    # Çapraz kavşak — farklı önceliklerde 5 ajan
    vehicles = [
        {
            "id": "ego",
            "route": [(-75, -4), (-25, -4), (0, -4), (25, -4), (75, -4)],
            "speed": 7.5, "length": 9.0, "width": 4.0,
            "priority": 1, "vehicle_type": "MineTruck", "start_delay": 0.0,
        },
        {
            "id": "agent_1",
            "route": [(4, -72), (4, -22), (4, 0), (4, 22), (4, 72)],
            "speed": 6.5, "length": 4.49, "width": 1.877,
            "priority": 3, "vehicle_type": "PickupSuv", "start_delay": 0.0,
        },
        {
            "id": "agent_2",
            "route": [(-4, 72), (-4, 22), (-4, 0), (-4, -22), (-4, -72)],
            "speed": 6.0, "length": 4.49, "width": 1.877,
            "priority": 3, "vehicle_type": "PickupSuv", "start_delay": 0.5,
        },
        {
            "id": "agent_3",
            "route": [(75, 4), (25, 4), (0, 4), (-25, 4), (-75, 4)],
            "speed": 7.0, "length": 4.49, "width": 1.877,
            "priority": 2, "vehicle_type": "PickupSuv", "start_delay": 1.0,
        },
        {
            "id": "agent_4",
            "route": [(10, -78), (10, -30), (10, 0), (10, 30), (10, 78)],
            "speed": 5.5, "length": 5.0, "width": 2.0,
            "priority": 4, "vehicle_type": "PickupSuv", "start_delay": 2.0,
        },
        {
            "id": "agent_5",
            "route": [(-78, -10), (-30, -10), (0, -10), (30, -10), (78, -10)],
            "speed": 6.0, "length": 4.5, "width": 1.9,
            "priority": 4, "vehicle_type": "PickupSuv", "start_delay": 3.0,
        },
    ]

    frames = _fleet_sim_frames(vehicles, dt, total_time)

    road_geom = _make_demo_road_geometry("cross")
    road_geom["conflict_zones"] = [{"x": 0, "y": 0, "r": 15}]
    road_geom["viewport_bounds"] = {"x_min": -82, "x_max": 82, "y_min": -82, "y_max": 82}

    return {
        "scenario_id": "fleet_heavy_traffic",
        "source": "demo",
        "total_frames": len(frames),
        "dt": dt,
        "agent_count": 6,
        "total_time": total_time,
        "frames": frames,
        "road_geometry": road_geom,
    }


# ── Stabil Senaryo Yardımcıları ───────────────────────────────────────────────

def _generate_stable_scenario(scenario_id: str) -> dict:
    """Stabil senaryo yönlendirici."""
    generators = {
        "stable_parallel":   _gen_stable_parallel,
        "stable_sequential": _gen_stable_sequential,
        "stable_convoy":     _gen_stable_convoy,
        "stable_opposite":   _gen_stable_opposite,
        "stable_fleet":      _gen_stable_fleet,
    }
    gen = generators.get(scenario_id)
    if gen:
        return gen()
    return generate_rich_demo_frames(scenario_id, 2, "straight")


def _stable_frame_seq(vehicles_cfg: list, dt: float, total_time: float) -> list:
    """Stabil senaryo frame üretici — her araç sabit rota üzerinde ilerler, çarpışma kontrolü yok."""
    total_frames = int(total_time / dt)
    frames = []
    for fi in range(total_frames):
        t = fi * dt
        vehicles = []
        for vc in vehicles_cfg:
            route = vc["route"]
            speed = vc["speed"]
            rlen = _rlen(route) or 1.0
            dist = min(speed * t, rlen)
            x, y, h = _rpos(route, dist)
            vehicles.append({
                "id": vc["id"],
                "x": round(x, 3),
                "y": round(y, 3),
                "heading": round(h, 4),
                "speed": round(speed if dist < rlen else 0.0, 2),
                "length": vc["length"],
                "width": vc["width"],
            })
        frames.append({
            "frame": fi,
            "time": round(t, 2),
            "vehicles": vehicles,
            "completed": fi == total_frames - 1,
        })
    return frames


def _gen_stable_parallel() -> dict:
    """Senaryo A — Paralel Yollar: 3 paralel şerit, çarpışma geometrik olarak imkansız."""
    dt = 0.1
    total_time = 20.0
    road_hw = 12.0  # her iki yönde geniş şerit

    vehicles_cfg = [
        {"id": "ego",     "route": [(-70, 0), (70, 0)],   "speed": 7.0, "length": 9.0, "width": 4.0},
        {"id": "agent_1", "route": [(70, -20), (-70, -20)], "speed": 6.5, "length": 4.5, "width": 2.0},
        {"id": "agent_2", "route": [(70, 20), (-70, 20)],   "speed": 6.0, "length": 4.5, "width": 2.0},
    ]
    frames = _stable_frame_seq(vehicles_cfg, dt, total_time)
    road_geom = {
        "type": "straight",
        "center": {"x": 0, "y": 0},
        "road_width": road_hw * 2,
        "drivable_polygons": [
            {"type": "road", "points": [
                {"x": -75, "y": -road_hw}, {"x": 75, "y": -road_hw},
                {"x": 75, "y": road_hw}, {"x": -75, "y": road_hw}]},
        ],
        "centerlines": [
            {"type": "base", "points": [{"x": -75, "y": 0}, {"x": 75, "y": 0}]},
            {"type": "base", "points": [{"x": -75, "y": -20}, {"x": 75, "y": -20}]},
            {"type": "base", "points": [{"x": -75, "y": 20}, {"x": 75, "y": 20}]},
        ],
        "segments": [{"from": {"x": -75, "y": 0}, "to": {"x": 75, "y": 0}, "width": road_hw * 2}],
        "conflict_zones": [],
        "viewport_bounds": {"x_min": -80, "x_max": 80, "y_min": -35, "y_max": 35},
        "goal_polygon": [{"x": 60, "y": -10}, {"x": 75, "y": -10}, {"x": 75, "y": 10}, {"x": 60, "y": 10}],
    }
    return {
        "scenario_id": "stable_parallel",
        "source": "demo",
        "total_frames": len(frames),
        "dt": dt,
        "agent_count": 3,
        "total_time": total_time,
        "frames": frames,
        "road_geometry": road_geom,
    }


def _gen_stable_sequential() -> dict:
    """Senaryo B — Sıralı Geçiş: her araç kavşakta yalnız, çarpışma geometrik olarak imkansız."""
    dt = 0.1
    total_time = 40.0
    rw = 8.0

    # EGO: tamamen yatay, kavşak merkezinden (x=0) geçip y=-4 şeridinde ilerler
    ego_route = [(-70, -4), (70, -4)]
    ego_speed = 7.0
    ego_rlen = _rlen(ego_route)
    # EGO x=0'ı geçme zamanı: (70/140)*140/7 ≈ 5s, tamamen çıkma: 140/7 ≈ 20s

    # Agent1: t=22s'de başlar (EGO çıktıktan 2s sonra), yatay karşı yön
    a1_route = [(70, 4), (-70, 4)]
    a1_speed = 6.0
    a1_delay = 22.0
    a1_rlen = _rlen(a1_route)

    # Agent2: t=32s'de başlar (Agent1 kavşak bölgesini 32s'de terk eder), dikey
    # Agent1 x=0'ı terk etme zamanı: 22 + 70/6 ≈ 33.7s → 34s'den sonra güvenli
    a2_route = [(0, -60), (0, 60)]
    a2_speed = 5.5
    a2_delay = 36.0
    a2_rlen = _rlen(a2_route)

    total_frames = int(total_time / dt)
    frames = []

    for fi in range(total_frames):
        t = fi * dt
        ego_dist = min(ego_speed * t, ego_rlen)
        ex, ey, eh = _rpos(ego_route, ego_dist)

        a1_t = max(0.0, t - a1_delay)
        a1_dist = min(a1_speed * a1_t, a1_rlen)
        a1x, a1y, a1h = _rpos(a1_route, a1_dist)

        a2_t = max(0.0, t - a2_delay)
        a2_dist = min(a2_speed * a2_t, a2_rlen)
        a2x, a2y, a2h = _rpos(a2_route, a2_dist)

        frames.append({
            "frame": fi,
            "time": round(t, 2),
            "vehicles": [
                {"id": "ego", "x": round(ex, 3), "y": round(ey, 3), "heading": round(eh, 4),
                 "speed": round(ego_speed if ego_dist < ego_rlen else 0.0, 2), "length": 9.0, "width": 4.0},
                {"id": "agent_1", "x": round(a1x, 3), "y": round(a1y, 3), "heading": round(a1h, 4),
                 "speed": round(a1_speed if a1_t > 0 and a1_dist < a1_rlen else 0.0, 2), "length": 4.5, "width": 2.0},
                {"id": "agent_2", "x": round(a2x, 3), "y": round(a2y, 3), "heading": round(a2h, 4),
                 "speed": round(a2_speed if a2_t > 0 and a2_dist < a2_rlen else 0.0, 2), "length": 4.5, "width": 2.0},
            ],
            "completed": fi == total_frames - 1,
        })

    road_geom = _make_demo_road_geometry("cross", rw / 2)
    road_geom["viewport_bounds"] = {"x_min": -80, "x_max": 80, "y_min": -68, "y_max": 68}
    road_geom["goal_polygon"] = [{"x": 58, "y": -10}, {"x": 75, "y": -10}, {"x": 75, "y": 2}, {"x": 58, "y": 2}]

    return {
        "scenario_id": "stable_sequential",
        "source": "demo",
        "total_frames": len(frames),
        "dt": dt,
        "agent_count": 3,
        "total_time": total_time,
        "frames": frames,
        "road_geometry": road_geom,
    }


def _gen_stable_convoy() -> dict:
    """Senaryo C — Konvoy: EGO önde, ajanlar sabit 25m mesafede takip eder."""
    dt = 0.1
    total_time = 20.0
    # Yeterince uzun rota — her araç farklı başlangıç noktasında
    route = [(-120, 0), (70, 0)]
    route_len = _rlen(route)  # 190m
    speed = 7.0
    gap = 25.0  # araçlar arası mesafe (merkez-merkez)

    # Başlangıç mesafeleri: EGO rota üzerinde 50m ileriden başlar
    ego_s0 = 50.0   # x = -120+50 = -70
    a1_s0 = 25.0    # x = -120+25 = -95
    a2_s0 = 0.0     # x = -120

    total_frames = int(total_time / dt)
    frames = []

    for fi in range(total_frames):
        t = fi * dt
        ego_dist = min(ego_s0 + speed * t, route_len)
        a1_dist = min(a1_s0 + speed * t, route_len)
        a2_dist = min(a2_s0 + speed * t, route_len)

        ex, ey, eh = _rpos(route, ego_dist)
        a1x, a1y, a1h = _rpos(route, a1_dist)
        a2x, a2y, a2h = _rpos(route, a2_dist)

        frames.append({
            "frame": fi,
            "time": round(t, 2),
            "vehicles": [
                {"id": "ego", "x": round(ex, 3), "y": round(ey, 3), "heading": round(eh, 4),
                 "speed": round(speed if ego_dist < route_len else 0.0, 2), "length": 9.0, "width": 4.0},
                {"id": "agent_1", "x": round(a1x, 3), "y": round(a1y, 3), "heading": round(a1h, 4),
                 "speed": round(speed if a1_dist < route_len else 0.0, 2), "length": 4.5, "width": 2.0},
                {"id": "agent_2", "x": round(a2x, 3), "y": round(a2y, 3), "heading": round(a2h, 4),
                 "speed": round(speed if a2_dist < route_len else 0.0, 2), "length": 4.5, "width": 2.0},
            ],
            "completed": fi == total_frames - 1,
        })

    road_geom = _make_demo_road_geometry("straight")
    road_geom["goal_polygon"] = [{"x": 60, "y": -6}, {"x": 75, "y": -6}, {"x": 75, "y": 6}, {"x": 60, "y": 6}]

    return {
        "scenario_id": "stable_convoy",
        "source": "demo",
        "total_frames": len(frames),
        "dt": dt,
        "agent_count": 3,
        "total_time": total_time,
        "frames": frames,
        "road_geometry": road_geom,
    }


def _gen_stable_opposite() -> dict:
    """Senaryo D — Karşılıklı Güvenli Geçiş: geniş yol, 16m şerit ayrımı."""
    dt = 0.1
    total_time = 20.0
    road_hw = 14.0  # 28m toplam genişlik

    vehicles_cfg = [
        {"id": "ego",     "route": [(-75, 8), (75, 8)],  "speed": 7.0, "length": 9.0, "width": 4.0},
        {"id": "agent_1", "route": [(75, -8), (-75, -8)], "speed": 6.5, "length": 4.5, "width": 2.0},
    ]
    frames = _stable_frame_seq(vehicles_cfg, dt, total_time)

    road_geom = {
        "type": "straight",
        "center": {"x": 0, "y": 0},
        "road_width": road_hw * 2,
        "drivable_polygons": [
            {"type": "road", "points": [
                {"x": -80, "y": -road_hw}, {"x": 80, "y": -road_hw},
                {"x": 80, "y": road_hw}, {"x": -80, "y": road_hw}]},
        ],
        "centerlines": [
            {"type": "base", "points": [{"x": -80, "y": 8}, {"x": 80, "y": 8}]},
            {"type": "base", "points": [{"x": -80, "y": -8}, {"x": 80, "y": -8}]},
        ],
        "segments": [{"from": {"x": -80, "y": 0}, "to": {"x": 80, "y": 0}, "width": road_hw * 2}],
        "conflict_zones": [],
        "viewport_bounds": {"x_min": -88, "x_max": 88, "y_min": -22, "y_max": 22},
        "goal_polygon": [{"x": 62, "y": 2}, {"x": 75, "y": 2}, {"x": 75, "y": 14}, {"x": 62, "y": 14}],
    }

    return {
        "scenario_id": "stable_opposite",
        "source": "demo",
        "total_frames": len(frames),
        "dt": dt,
        "agent_count": 2,
        "total_time": total_time,
        "frames": frames,
        "road_geometry": road_geom,
    }


def _gen_stable_fleet() -> dict:
    """Senaryo E — Filo Koordinasyonu: 5 araç, her biri kavşakta yalnız."""
    dt = 0.1
    total_time = 50.0
    rw = 8.0

    # EGO önce geçer (öncelik 1)
    # Her araç bir önceki kavşak geçiş süresi + 6s sonra başlar
    delays = [0.0, 8.0, 14.0, 20.0, 26.0]
    routes = [
        [(-70, -4), (70, -4)],       # EGO: soldan sağa
        [(4, -70), (4, 70)],          # Agent 1: aşağıdan yukarı
        [(70, 4), (-70, 4)],          # Agent 2: sağdan sola
        [(-4, 70), (-4, -70)],        # Agent 3: yukarıdan aşağı
        [(-70, -12), (70, -12)],      # Agent 4: soldan sağa, farklı şerit
    ]
    ids = ["ego", "agent_1", "agent_2", "agent_3", "agent_4"]
    speeds = [7.0, 6.0, 6.5, 6.0, 5.5]
    lengths = [9.0, 4.5, 4.5, 4.5, 4.5]
    widths = [4.0, 2.0, 2.0, 2.0, 2.0]

    rlens = [_rlen(r) for r in routes]
    total_frames = int(total_time / dt)
    frames = []

    for fi in range(total_frames):
        t = fi * dt
        vehicles = []
        for i in range(5):
            et = max(0.0, t - delays[i])
            dist = min(speeds[i] * et, rlens[i])
            x, y, h = _rpos(routes[i], dist)
            vehicles.append({
                "id": ids[i],
                "x": round(x, 3), "y": round(y, 3), "heading": round(h, 4),
                "speed": round(speeds[i] if et > 0 and dist < rlens[i] else 0.0, 2),
                "length": lengths[i], "width": widths[i],
            })
        frames.append({
            "frame": fi, "time": round(t, 2),
            "vehicles": vehicles, "completed": fi == total_frames - 1,
        })

    road_geom = _make_demo_road_geometry("cross", rw / 2)
    road_geom["viewport_bounds"] = {"x_min": -82, "x_max": 82, "y_min": -82, "y_max": 82}
    road_geom["goal_polygon"] = [{"x": 58, "y": -10}, {"x": 75, "y": -10}, {"x": 75, "y": 2}, {"x": 58, "y": 2}]

    return {
        "scenario_id": "stable_fleet",
        "source": "demo",
        "total_frames": total_frames,
        "dt": dt,
        "agent_count": 5,
        "total_time": total_time,
        "frames": frames,
        "road_geometry": road_geom,
    }


# ── Faza E — Genişletilmiş Senaryo Üreticisi ─────────────────────────────────

def _generate_extended_scenario(scenario_id: str) -> dict:
    """Faza E genişletilmiş senaryo yönlendirici."""
    meta = next((s for s in EXTENDED_SCENARIOS if s["id"] == scenario_id), None)
    if meta is None:
        return generate_rich_demo_frames(scenario_id, 3, "T")

    grade = meta.get("grade", 0)
    scenario_type = meta["type"]
    agent_count = meta["agents"]
    total_time = 60.0 if scenario_id == "ext_full_fleet" else max(30.0, agent_count * 7.0)
    dt = 0.1

    # Yük ve eğim bazlı hız hesapla
    # Eğim etkisi: yokuş yukarı hız azalır, yokuş aşağı fren uzar
    grade_speed_factor = max(0.3, 1.0 - max(grade, 0) * 0.03)
    ego_base_speed = 8.9 * grade_speed_factor  # Tam yüklü kamyon hızı (m/s)
    agent_base_speed = 7.5 * max(0.4, 1.0 - abs(grade) * 0.02)

    # Dar geçit senaryosu için özel yol geometrisi
    if scenario_id == "ext_narrow_pass":
        return _gen_ext_narrow_pass(dt, total_time, grade)

    # Acil duraksama
    if scenario_id == "ext_emergency_stop":
        return _gen_ext_emergency_stop(dt, grade)

    # Rampalı yükleme
    if scenario_id == "ext_loading_ramp":
        return _gen_ext_loading_ramp(dt, total_time, grade)

    # Sis kavşağı
    if scenario_id == "ext_fog_intersection":
        return _gen_ext_fog_intersection(dt, total_time)

    # Genel senaryo için mevcut generate_rich_demo_frames kullan
    # Hız seçimi: yük ve eğime göre
    speed_type = scenario_type
    if scenario_type == "intersection":
        speed_type = "T"

    result = generate_rich_demo_frames(scenario_id, agent_count, speed_type)

    # Grade bilgisini road_geometry'ye ekle
    if "road_geometry" in result:
        result["road_geometry"]["grade"] = grade
        result["road_geometry"]["grade_label"] = (
            f"↗ +{grade}%" if grade > 0 else (f"↘ {grade}%" if grade < 0 else "→ 0%")
        )

    result["grade"] = grade
    result["source"] = "extended"

    # Yokuş yukarı: EGO ve ajanların hızını düşür
    if grade != 0 and "frames" in result:
        spd_factor = grade_speed_factor if grade > 0 else min(1.0 + abs(grade) * 0.015, 1.2)
        for frame in result["frames"]:
            for v in frame.get("vehicles", []):
                v["speed"] = round(v["speed"] * spd_factor, 2)

    return result


def _gen_ext_narrow_pass(dt: float, total_time: float, grade: int) -> dict:
    """Dar Geçit Koordinasyonu — tek şeritli yol, bekleme cebi."""
    total_frames = int(total_time / dt)

    # EGO: soldan sağa, bekleme cebine girip karşıdan geleni geçirir
    ego_route = [
        (-75, -2, 7.0), (-40, -2, 6.0), (-20, -2, 3.0),
        (-20, -8, 2.0),  # Bekleme cebine gir
        (-20, -8, 0.0),  # Bekle
        (-20, -8, 0.0),
        (-20, -2, 2.0),  # Geri rota
        (0, -2, 5.0), (35, -2, 7.0), (75, -2, 7.5),
    ]
    agent1_route = [
        (75, 2, 6.5), (35, 2, 5.5), (0, 2, 4.0), (-20, 2, 5.5), (-55, 2, 7.0), (-75, 2, 7.5),
    ]
    agent2_route = [
        (75, 2, 0.0), (75, 2, 0.0), (65, 2, 5.0), (35, 2, 6.5), (0, 2, 5.0), (-40, 2, 7.0), (-75, 2, 7.5),
    ]

    grade_factor = max(0.4, 1.0 - abs(grade) * 0.03)
    frames = []
    ego_prog = 0.0
    a1_prog = 0.0
    a2_prog = 0.0
    step = 1.0 / (total_frames - 1) if total_frames > 1 else 1.0

    for fi in range(total_frames):
        ego_prog = min(1.0, ego_prog + step)
        a1_prog = min(1.0, a1_prog + step)
        a2_prog = min(1.0, a2_prog + step * 0.8)

        ex, ey, eh, es = _interpolate_route(ego_route, ego_prog * total_time, total_time)
        a1x, a1y, a1h, a1s = _interpolate_route(agent1_route, a1_prog * total_time, total_time)
        a2x, a2y, a2h, a2s = _interpolate_route(agent2_route, a2_prog * total_time, total_time)

        vehicles = [
            {"id": "ego", "x": round(ex, 3), "y": round(ey, 3), "heading": round(eh, 4),
             "speed": round(es * grade_factor, 2), "length": 9.0, "width": 4.0},
            {"id": "agent_1", "x": round(a1x, 3), "y": round(a1y, 3), "heading": round(a1h, 4),
             "speed": round(a1s * grade_factor, 2), "length": 8.5, "width": 3.5},
            {"id": "agent_2", "x": round(a2x, 3), "y": round(a2y, 3), "heading": round(a2h, 4),
             "speed": round(a2s * grade_factor, 2), "length": 9.0, "width": 4.0},
        ]
        frames.append({"frame": fi, "time": round(fi * dt, 2), "vehicles": vehicles, "completed": fi == total_frames - 1})

    road_geom = _make_demo_road_geometry("straight", 5.0)
    road_geom["grade"] = grade
    road_geom["grade_label"] = f"↘ {grade}%" if grade < 0 else "→ 0%"
    # Bekleme cebi polygon
    road_geom["drivable_polygons"].append({
        "type": "road",
        "points": [{"x": -28, "y": -14}, {"x": -12, "y": -14}, {"x": -12, "y": -5}, {"x": -28, "y": -5}],
    })
    road_geom["viewport_bounds"] = {"x_min": -90, "x_max": 90, "y_min": -20, "y_max": 15}

    return {
        "scenario_id": "ext_narrow_pass", "source": "extended",
        "total_frames": total_frames, "dt": dt, "agent_count": 3,
        "total_time": total_time, "grade": grade, "frames": frames, "road_geometry": road_geom,
    }


def _gen_ext_emergency_stop(dt: float, grade: int) -> dict:
    """Acil Duraksama — t=5s'de kaya düşer, EGO frenler."""
    total_time = 25.0
    total_frames = int(total_time / dt)
    obstacle_appear_frame = 50  # t=5s

    grade_brake_factor = 1.0 + abs(grade) * 0.08 if grade < 0 else 1.0
    brake_dist = 45.0 * grade_brake_factor  # ~45m frenleme mesafesi

    ego_route = [
        (-75, -2, 0.0), (-30, -2, 12.0), (-10, -2, 12.0),
        (5, -2, 8.0), (10, -2, 3.0), (12, -2, 0.0),  # Fren
        (12, -2, 0.0), (12, -2, 0.0),  # Bekle
    ]

    frames = []
    ego_prog = 0.0
    step = 1.0 / (total_frames - 1) if total_frames > 1 else 1.0
    braking = False

    for fi in range(total_frames):
        ego_prog = min(1.0, ego_prog + step * (0.3 if braking else 1.0))
        ex, ey, eh, es = _interpolate_route(ego_route, ego_prog * total_time, total_time)

        vehicles: list[dict] = [
            {"id": "ego", "x": round(ex, 3), "y": round(ey, 3), "heading": round(eh, 4),
             "speed": round(max(0.0, es), 2), "length": 9.0, "width": 4.0},
        ]

        # Kaya t=5s'den sonra belirir
        if fi >= obstacle_appear_frame:
            braking = True
            vehicles.append({
                "id": "obstacle_1",
                "x": 15.0, "y": -2.0, "heading": 0.0, "speed": 0.0,
                "length": 3.0, "width": 3.0,
                "vehicle_type": "StaticObstacle",
            })

        frames.append({"frame": fi, "time": round(fi * dt, 2), "vehicles": vehicles, "completed": fi == total_frames - 1})

    road_geom = _make_demo_road_geometry("straight", 7.0)
    road_geom["grade"] = grade
    road_geom["grade_label"] = "→ 0%"
    road_geom["viewport_bounds"] = {"x_min": -90, "x_max": 50, "y_min": -20, "y_max": 20}

    return {
        "scenario_id": "ext_emergency_stop", "source": "extended",
        "total_frames": total_frames, "dt": dt, "agent_count": 1,
        "total_time": total_time, "grade": grade, "frames": frames, "road_geometry": road_geom,
    }


def _gen_ext_loading_ramp(dt: float, total_time: float, grade: int) -> dict:
    """Rampalı Yükleme — EGO boş gidip platformda yükleniyor."""
    total_frames = int(total_time / dt)
    load_start_frame = int(total_frames * 0.35)
    load_end_frame = int(total_frames * 0.55)

    ego_route = [
        (-75, -2, 0.0), (-30, -2, 8.0),
        (0, 0, 4.0), (20, 5, 3.0),  # Rampa
        (40, 5, 0.0),  # Platform — yükleniyor
        (40, 5, 0.0),
        (20, 5, 3.0), (0, 0, 4.0),  # İniş
        (-30, -2, 7.0), (-75, -2, 8.0),  # Dönüş
    ]
    a1_route = [
        (75, 2, 7.5), (40, 2, 6.0), (20, 5, 3.0), (0, 0, 4.0), (-30, -2, 7.0), (-75, -2, 7.5),
    ]
    a2_route = [
        (75, 2, 0.0), (75, 2, 0.0), (65, 2, 6.0), (40, 2, 5.5), (20, 5, 3.0),
        (0, 0, 4.0), (-30, -2, 6.5), (-75, -2, 7.0),
    ]

    frames = []
    ego_prog = 0.0
    a1_prog = 0.0
    a2_prog = 0.0
    step = 1.0 / (total_frames - 1) if total_frames > 1 else 1.0

    for fi in range(total_frames):
        # EGO platform'da bekliyor
        if load_start_frame <= fi <= load_end_frame:
            ego_prog_step = 0.0
        else:
            ego_prog_step = step * 0.7
        ego_prog = min(1.0, ego_prog + ego_prog_step)
        a1_prog = min(1.0, a1_prog + step * 0.85)
        a2_prog = min(1.0, a2_prog + step * 0.7)

        ex, ey, eh, es = _interpolate_route(ego_route, ego_prog * total_time, total_time)
        a1x, a1y, a1h, a1s = _interpolate_route(a1_route, a1_prog * total_time, total_time)
        a2x, a2y, a2h, a2s = _interpolate_route(a2_route, a2_prog * total_time, total_time)

        is_loading = load_start_frame <= fi <= load_end_frame
        vehicles = [
            {"id": "ego", "x": round(ex, 3), "y": round(ey, 3), "heading": round(eh, 4),
             "speed": 0.0 if is_loading else round(es, 2), "length": 9.0, "width": 4.0,
             "status": "loading" if is_loading else "moving"},
            {"id": "agent_1", "x": round(a1x, 3), "y": round(a1y, 3), "heading": round(a1h, 4),
             "speed": round(a1s, 2), "length": 8.5, "width": 3.5},
            {"id": "agent_2", "x": round(a2x, 3), "y": round(a2y, 3), "heading": round(a2h, 4),
             "speed": round(a2s, 2), "length": 8.5, "width": 3.5},
        ]
        frames.append({"frame": fi, "time": round(fi * dt, 2), "vehicles": vehicles, "completed": fi == total_frames - 1})

    road_geom = _make_demo_road_geometry("straight", 7.0)
    road_geom["grade"] = grade
    road_geom["grade_label"] = f"↗ +{grade}%" if grade > 0 else "→ 0%"
    # Platform polygon (sarımsı)
    road_geom["drivable_polygons"].append({
        "type": "loading",
        "points": [{"x": 28, "y": 1}, {"x": 55, "y": 1}, {"x": 55, "y": 12}, {"x": 28, "y": 12}],
    })
    road_geom["viewport_bounds"] = {"x_min": -90, "x_max": 70, "y_min": -18, "y_max": 22}

    return {
        "scenario_id": "ext_loading_ramp", "source": "extended",
        "total_frames": total_frames, "dt": dt, "agent_count": 3,
        "total_time": total_time, "grade": grade, "frames": frames, "road_geometry": road_geom,
    }


def _gen_ext_fog_intersection(dt: float, total_time: float) -> dict:
    """Sis Kavşağı — araçlar birbirini ancak 20m yakında görüyor."""
    total_frames = int(total_time / dt)
    visibility_radius = 20.0

    base = generate_rich_demo_frames("ext_fog_intersection", 3, "T")
    # Sis bilgisini road_geometry'ye ekle
    if "road_geometry" in base:
        base["road_geometry"]["grade"] = 0
        base["road_geometry"]["grade_label"] = "→ 0%"
        base["road_geometry"]["fog_visibility"] = visibility_radius

    base["grade"] = 0
    base["source"] = "extended"
    base["fog_visibility"] = visibility_radius
    return base
