"""HÜsim — FastAPI ana uygulama (Faza D)"""
import uuid
import json
import math
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

import database
import weather_optimizer
import scenario_runner
import scenario_loader
import scenario_generator as sg
import report_generator
try:
    import dataset_calibration
    import maintenance_data as _maintenance
    _DATASET_MODULES_OK = True
except Exception as _de:
    _DATASET_MODULES_OK = False
    logging.getLogger("husim.bootstrap").warning(f"Dataset modülleri yüklenemedi: {_de}")
from load_system import LoadSystem
from event_zones import EventZoneManager, EVENT_TYPES
from models import (
    WeatherInput, OptimizedParams, ScenarioRunRequest,
    SimulationStatus, SimulationMetrics, ReportRequest, BatchRunRequest
)

_load_system = LoadSystem()
_event_manager = EventZoneManager()
_engine_histories: dict[str, list[float]] = {}  # vehicle_id → sıcaklık geçmişi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("husim")

# Aktif simülasyonları bellekte tut
active_simulations: dict[str, dict] = {}
# WebSocket bağlantıları: simulation_id → [WebSocket]
ws_connections: dict[str, list[WebSocket]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("HÜsim başlatılıyor...")
    await database.init_db()
    logger.info("Veritabanı hazır.")
    if _DATASET_MODULES_OK:
        try:
            dataset_calibration.load_and_calibrate()
            logger.info("Levin Telematics kalibrasyon tamamlandı.")
        except Exception as e:
            logger.warning(f"Kalibrasyon başlatma hatası: {e}")
    yield
    logger.info("HÜsim kapatılıyor.")


app = FastAPI(
    title="HÜsim API",
    description="Maden Simülasyon Kontrol Sistemi",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Sistem Durumu ────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "durum": "çalışıyor",
        "demo_modu": scenario_runner.DEMO_MODE,
        "minesim_yolu": str(scenario_runner.MINESIM_PATH),
        "aktif_simulasyonlar": len(active_simulations),
    }


# ─── Senaryolar ───────────────────────────────────────────────────────────────

@app.get("/api/scenarios")
async def get_scenarios():
    """Kullanılabilir senaryoları listele (gerçek + demo + üretilmiş)."""
    scenarios = scenario_loader.find_all_scenarios()
    return {"senaryolar": scenarios, "toplam": len(scenarios)}


@app.get("/api/scenarios/{scenario_id}/frames")
async def get_scenario_frames(scenario_id: str):
    """Senaryo frame verilerini getir (tüm animasyon verisi)."""
    # Senaryo yolunu bul
    all_scenarios = scenario_loader.find_all_scenarios()
    meta = next((s for s in all_scenarios if s["id"] == scenario_id), None)
    path = meta["path"] if meta else None
    data = scenario_loader.load_scenario_frames(scenario_id, path)
    return data


@app.post("/api/scenarios/generate")
async def generate_scenario(payload: dict):
    """Yeni senaryo üret."""
    generator = sg.ScenarioGenerator()
    result = generator.generate(
        intersection_type=payload.get("intersection_type", "T"),
        vehicle_count=max(2, min(8, int(payload.get("vehicle_count", 3)))),
        difficulty=payload.get("difficulty", "orta"),
        special_condition=payload.get("special_condition", "normal"),
        weather_params=payload.get("weather_params", {}),
        name=payload.get("name", ""),
    )
    # Frame'leri döndürmeden sadece metadata döndür
    result_meta = {k: v for k, v in result.items() if k != "frames"}
    result_meta["frame_count"] = result.get("total_frames", 200)
    return {"basarili": True, "senaryo": result_meta}


@app.post("/api/scenarios/compare")
async def compare_scenarios(payload: dict):
    """İki senaryoyu karşılaştır (normal vs optimize edilmiş)."""
    scenario_id = payload.get("scenario_id", "")
    weather_params = payload.get("weather_params", {})

    all_scenarios = scenario_loader.find_all_scenarios()
    meta = next((s for s in all_scenarios if s["id"] == scenario_id), None)
    path = meta["path"] if meta else None

    # Normal versiyon
    normal_data = scenario_loader.load_scenario_frames(scenario_id, path)

    # Optimize edilmiş versiyon: hız düşürüldü, güvenlik arttırıldı
    speed_factor = weather_params.get("max_speed_factor", 0.7)
    opt_data = scenario_loader.load_scenario_frames(scenario_id, path)

    # Optimize versiyonda araç hızlarını düşür
    for frame in opt_data.get("frames", []):
        for v in frame.get("vehicles", []):
            v["speed"] = round(v["speed"] * speed_factor, 2)

    # Özet metrikler hesapla
    def calc_metrics(frames):
        collisions = 0
        near_misses = 0
        speeds = []
        for fr in frames:
            vlist = fr.get("vehicles", [])
            ego = next((v for v in vlist if v["id"] == "ego"), None)
            if ego:
                speeds.append(ego["speed"])
            agents = [v for v in vlist if v["id"] != "ego"]
            if ego:
                for ag in agents:
                    d = math.hypot(ego["x"] - ag["x"], ego["y"] - ag["y"])
                    if d < 2.0:
                        collisions += 1
                    elif d < 6.0:
                        near_misses += 1
        risk = min(100, collisions * 20 + near_misses * 3)
        avg_spd = sum(speeds) / len(speeds) if speeds else 0
        return {"risk_score": risk, "collision_count": collisions // max(1, len(frames) // 20),
                "near_miss_count": near_misses // max(1, len(frames) // 20),
                "average_speed": round(avg_spd, 2)}

    return {
        "scenario_id": scenario_id,
        "normal": {
            "frames": normal_data.get("frames", []),
            "road_geometry": normal_data.get("road_geometry", {}),
            "metrics": calc_metrics(normal_data.get("frames", [])),
        },
        "optimized": {
            "frames": opt_data.get("frames", []),
            "road_geometry": opt_data.get("road_geometry", {}),
            "metrics": calc_metrics(opt_data.get("frames", [])),
        },
    }


@app.post("/api/scenarios/run")
async def run_scenario(request: ScenarioRunRequest, background_tasks: BackgroundTasks):
    """Yeni simülasyon başlat."""
    sim_id = str(uuid.uuid4())[:8]

    active_simulations[sim_id] = {
        "status": "running",
        "progress": 0,
        "current_frame": 0,
        "total_frames": 150,
        "metrics": None,
        "scenario_id": request.scenario_id,
        "algorithm": request.algorithm,
        "weather": None,
    }
    ws_connections[sim_id] = []

    await database.save_session(sim_id, request.scenario_id, request.algorithm or "SPPMM")

    # Yük parametrelerini simülasyon state'ine kaydet
    active_simulations[sim_id]["load_percent"] = request.load_percent or 0.0
    active_simulations[sim_id]["grade_percent"] = request.grade_percent or 0.0
    active_simulations[sim_id]["vehicle_type"] = request.vehicle_type or "MineTruck_XG90G"

    background_tasks.add_task(
        _run_simulation_task,
        sim_id,
        request.scenario_id,
        request.optimized_params,
        request.algorithm or "SPPMM",
        request.load_percent or 0.0,
        request.grade_percent or 0.0,
        request.vehicle_type or "MineTruck_XG90G",
    )

    logger.info(f"Simülasyon başlatıldı: {sim_id} / senaryo: {request.scenario_id}")
    return {"simulasyon_id": sim_id, "durum": "başlatıldı"}


async def _run_simulation_task(
    sim_id: str,
    scenario_id: str,
    params: OptimizedParams,
    algorithm: str,
    load_percent: float = 0.0,
    grade_percent: float = 0.0,
    vehicle_type: str = "MineTruck_XG90G",
):
    """Arka planda simülasyon çalıştır ve WebSocket'e veri aktar."""
    try:
        frame_list = []

        async def on_frame(frame_data: dict):
            frame_list.append(frame_data)
            total = active_simulations[sim_id]["total_frames"]
            frame_no = frame_data.get("frame", 0)
            active_simulations[sim_id]["current_frame"] = frame_no
            active_simulations[sim_id]["progress"] = min(99, int(frame_no / max(total, 1) * 100))

            # WebSocket'e gönder
            msg = json.dumps({"tip": "frame", "veri": frame_data}, ensure_ascii=False)
            dead = []
            for ws in ws_connections.get(sim_id, []):
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                ws_connections[sim_id].remove(ws)

        # Yük parametrelerine göre params'ı güncelle
        load_params = _load_system.get_params(vehicle_type, load_percent, grade_percent)
        params.max_speed_factor = round(params.max_speed_factor * load_params["max_speed_ms"] / 15.3, 3)

        metrics = await scenario_runner.run_scenario(
            sim_id, scenario_id, params, algorithm, on_frame
        )

        active_simulations[sim_id]["status"] = "completed"
        active_simulations[sim_id]["progress"] = 100
        active_simulations[sim_id]["metrics"] = metrics.model_dump()

        await database.update_session_status(sim_id, "completed")
        await database.save_result(sim_id, metrics.model_dump())

        # Tamamlandı mesajı
        done_msg = json.dumps({"tip": "tamamlandi", "metrikler": metrics.model_dump()}, ensure_ascii=False)
        for ws in ws_connections.get(sim_id, []):
            try:
                await ws.send_text(done_msg)
            except Exception:
                pass

        logger.info(f"Simülasyon tamamlandı: {sim_id}")

    except asyncio.CancelledError:
        active_simulations[sim_id]["status"] = "stopped"
        await database.update_session_status(sim_id, "stopped")

    except Exception as e:
        logger.error(f"Simülasyon hatası ({sim_id}): {e}")
        active_simulations[sim_id]["status"] = "failed"
        await database.update_session_status(sim_id, "failed")

        err_msg = json.dumps({"tip": "hata", "mesaj": str(e)}, ensure_ascii=False)
        for ws in ws_connections.get(sim_id, []):
            try:
                await ws.send_text(err_msg)
            except Exception:
                pass


@app.get("/api/scenarios/{sim_id}/status")
async def get_status(sim_id: str):
    """Simülasyon durumunu sorgula."""
    sim = active_simulations.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simülasyon bulunamadı")

    return SimulationStatus(
        simulation_id=sim_id,
        status=sim["status"],
        progress=sim["progress"],
        current_frame=sim["current_frame"],
        total_frames=sim["total_frames"],
        metrics=SimulationMetrics(**sim["metrics"]) if sim["metrics"] else None,
    )


@app.get("/api/scenarios/{sim_id}/result")
async def get_result(sim_id: str):
    """Simülasyon sonuçlarını getir."""
    sim = active_simulations.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simülasyon bulunamadı")
    if sim["status"] not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail="Simülasyon henüz tamamlanmadı")

    return {
        "simulasyon_id": sim_id,
        "durum": sim["status"],
        "metrikler": sim["metrics"],
        "senaryo": sim["scenario_id"],
        "algoritma": sim["algorithm"],
    }


@app.post("/api/scenarios/{sim_id}/stop")
async def stop_simulation(sim_id: str):
    """Simülasyonu durdur."""
    sim = active_simulations.get(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simülasyon bulunamadı")
    sim["status"] = "stopped"
    await database.update_session_status(sim_id, "stopped")
    return {"mesaj": "Simülasyon durduruldu", "simulasyon_id": sim_id}


# ─── Motor Durumu ─────────────────────────────────────────────────────────────

@app.get("/api/engine/status/{scenario_id}")
async def engine_status(scenario_id: str):
    """Tüm araçların anlık motor durumunu döndür."""
    sim = next(
        (s for s in active_simulations.values() if s.get("scenario_id") == scenario_id),
        None,
    )
    if not sim:
        return {"vehicles": [], "scenario_id": scenario_id}
    return {"vehicles": sim.get("engine_status", []), "scenario_id": scenario_id}


@app.get("/api/engine/history/{vehicle_id}")
async def engine_history(vehicle_id: str):
    """Araç motor sıcaklık geçmişi."""
    history = _engine_histories.get(vehicle_id, [])
    return {"vehicle_id": vehicle_id, "history": history, "count": len(history)}


# ─── Olay Bölgeleri ───────────────────────────────────────────────────────────

@app.get("/api/events/active")
async def get_active_events():
    """Aktif olay bölgelerini listele."""
    import time
    events = _event_manager.get_active_events(time.time())
    return {"events": events, "count": len(events)}


@app.post("/api/events/add")
async def add_event(payload: dict):
    """Yeni olay ekle."""
    import time
    x = float(payload.get("x", 0))
    y = float(payload.get("y", 0))
    event_type = payload.get("event_type", "kaya_dusme")
    try:
        eid = _event_manager.add_event(x, y, event_type, time.time())
        ev = _event_manager.get_all_events()
        added = next((e for e in ev if e["id"] == eid), None)

        # WebSocket üzerinden bildir
        if added:
            msg = json.dumps({"tip": "olay_eklendi", "olay": added}, ensure_ascii=False)
            for conns in ws_connections.values():
                for ws in conns:
                    try:
                        await ws.send_text(msg)
                    except Exception:
                        pass

        return {"basarili": True, "event_id": eid}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/events/{event_id}")
async def delete_event(event_id: str):
    """Olayı kaldır."""
    _event_manager.remove_event(event_id)
    msg = json.dumps({"tip": "olay_kaldirildi", "event_id": event_id}, ensure_ascii=False)
    for conns in ws_connections.values():
        for ws in conns:
            try:
                await ws.send_text(msg)
            except Exception:
                pass
    return {"basarili": True, "event_id": event_id}


@app.post("/api/events/random")
async def random_events(payload: dict):
    """Rastgele olay üret."""
    import time
    count = int(payload.get("count", 3))
    x_min = float(payload.get("x_min", -50))
    x_max = float(payload.get("x_max", 50))
    y_min = float(payload.get("y_min", -50))
    y_max = float(payload.get("y_max", 50))
    ids = _event_manager.add_random_events(count, (x_min, x_max), (y_min, y_max), time.time())
    return {"basarili": True, "event_ids": ids, "count": len(ids)}


@app.get("/api/events/types")
async def get_event_types():
    """Kullanılabilir olay tiplerini döndür."""
    return {"types": EVENT_TYPES}


# ─── Yük Sistemi ─────────────────────────────────────────────────────────────

@app.get("/api/load/presets")
async def get_load_presets():
    """Araç tipine göre yük preset listesi döndür."""
    return {"presets": _load_system.get_presets()}


@app.post("/api/load/calculate")
async def calculate_load(payload: dict):
    """Yük ve eğim parametrelerini hesapla."""
    vehicle_type = payload.get("vehicle_type", "MineTruck_XG90G")
    load_percent = float(payload.get("load_percent", 0))
    grade_percent = float(payload.get("grade_percent", 0))
    result = _load_system.get_params(vehicle_type, load_percent, grade_percent)
    return result


# ─── Dataset Kalibrasyonu ────────────────────────────────────────────────────

@app.get("/api/dataset/calibration")
async def get_dataset_calibration():
    """Tüm hava koşulları için Levin Telematics kalibrasyon bilgisi döndür."""
    if not _DATASET_MODULES_OK:
        return {
            "data_source": "Levin Telematics Dataset — 15,847 gerçek araç ölçümü",
            "calibration_info": {"dataset_loaded": False, "notes": "Dataset modülü yüklü değil."},
            "parameters": {},
        }
    try:
        return dataset_calibration.get_calibration_summary()
    except Exception as e:
        logger.error(f"Kalibrasyon özeti hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dataset/vehicle-health")
async def get_vehicle_health(vehicle_type: str = "MineTruck_XG90G", usage_hours: float = 1000.0):
    """Araç sağlık profilini döndür."""
    if not _DATASET_MODULES_OK:
        return {"health_score": 85.0, "brake_efficiency": 0.90, "warnings": [], "data_source": "varsayılan"}
    try:
        return _maintenance.get_vehicle_health_profile(vehicle_type, usage_hours)
    except Exception as e:
        logger.error(f"Araç sağlık hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Hava Durumu Optimizasyonu ───────────────────────────────────────────────

@app.post("/api/weather/optimize")
async def optimize_weather(weather: WeatherInput):
    """Hava koşullarına göre simülasyon parametrelerini optimize et."""
    logger.info(f"Hava optimizasyonu: {weather.weather_type} / {weather.ground_type}")
    params = weather_optimizer.optimize(weather)
    return params


# ─── Canlı Metrikler ──────────────────────────────────────────────────────────

@app.get("/api/metrics/live")
async def live_metrics():
    """Aktif simülasyonların anlık metriklerini döndür."""
    live = {}
    for sim_id, sim in active_simulations.items():
        if sim["status"] == "running":
            live[sim_id] = {
                "progress": sim["progress"],
                "current_frame": sim["current_frame"],
            }
    return {"aktif": live, "toplam_aktif": len(live)}


# ─── Raporlama ────────────────────────────────────────────────────────────────

@app.post("/api/reports/generate")
async def generate_report(request: ReportRequest):
    """Rapor oluştur ve kaydet."""
    sim = active_simulations.get(request.simulation_id)
    if not sim:
        # Geçmişten dene
        history = await database.get_history(limit=200)
        sim_history = next((h for h in history if h["id"] == request.simulation_id), None)
        if not sim_history:
            raise HTTPException(status_code=404, detail="Simülasyon bulunamadı")
        metrics = sim_history.get("metrics") or {}
        weather = sim_history.get("weather")
        scenario_id = sim_history.get("scenario_id", "")
    else:
        metrics = sim.get("metrics") or {}
        weather = sim.get("weather")
        scenario_id = sim.get("scenario_id", "")

    report_generator.generate_pdf(
        request.simulation_id,
        scenario_id,
        metrics,
        weather,
        request.include_metrics,
        request.include_weather,
    )

    return {"mesaj": "Rapor oluşturuldu", "simulasyon_id": request.simulation_id}


@app.get("/api/reports/{sim_id}/download")
async def download_report(sim_id: str):
    """PDF raporu indir."""
    report_path = report_generator.REPORTS_DIR / f"rapor_{sim_id}.pdf"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Rapor bulunamadı. Önce oluşturun.")

    pdf_bytes = report_path.read_bytes()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="husim_rapor_{sim_id}.pdf"'},
    )


# ─── Geçmiş ───────────────────────────────────────────────────────────────────

@app.get("/api/history")
async def get_history():
    """Geçmiş simülasyonları getir."""
    history = await database.get_history(limit=100)
    return {"gecmis": history, "toplam": len(history)}


# ─── Toplu Koşucu ─────────────────────────────────────────────────────────────

@app.post("/api/scenarios/batch")
async def batch_run(request: BatchRunRequest, background_tasks: BackgroundTasks):
    """Birden fazla senaryoyu sırayla çalıştır."""
    batch_id = str(uuid.uuid4())[:8]
    sim_ids = []

    for scenario_id in request.scenario_ids:
        sim_id = str(uuid.uuid4())[:8]
        sim_ids.append(sim_id)
        active_simulations[sim_id] = {
            "status": "pending",
            "progress": 0,
            "current_frame": 0,
            "total_frames": 150,
            "metrics": None,
            "scenario_id": scenario_id,
            "algorithm": request.algorithm or "SPPMM",
            "weather": None,
        }
        ws_connections[sim_id] = []
        await database.save_session(sim_id, scenario_id, request.algorithm or "SPPMM")

    background_tasks.add_task(_run_batch_task, sim_ids, request.optimized_params, request.algorithm or "SPPMM")

    return {"batch_id": batch_id, "simulasyon_idleri": sim_ids, "toplam": len(sim_ids)}


async def _run_batch_task(sim_ids: list[str], params: OptimizedParams, algorithm: str):
    for sim_id in sim_ids:
        sim = active_simulations.get(sim_id)
        if not sim:
            continue
        sim["status"] = "running"
        scenario_id = sim["scenario_id"]
        await _run_simulation_task(sim_id, scenario_id, params, algorithm)


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/simulation/{sim_id}")
async def websocket_simulation(websocket: WebSocket, sim_id: str):
    await websocket.accept()
    logger.info(f"WebSocket bağlandı: {sim_id}")

    if sim_id not in ws_connections:
        ws_connections[sim_id] = []
    ws_connections[sim_id].append(websocket)

    try:
        while True:
            # Bağlantıyı canlı tut (ping)
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if msg == "ping":
                    await websocket.send_text(json.dumps({"tip": "pong"}))
            except asyncio.TimeoutError:
                # Timeout — bağlantı kontrolü
                sim = active_simulations.get(sim_id)
                if sim and sim["status"] in ("completed", "failed", "stopped"):
                    break
    except WebSocketDisconnect:
        logger.info(f"WebSocket bağlantısı kesildi: {sim_id}")
    finally:
        if sim_id in ws_connections and websocket in ws_connections[sim_id]:
            ws_connections[sim_id].remove(websocket)

