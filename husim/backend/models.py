"""Pydantic data models — HÜsim backend"""
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class WeatherType(str, Enum):
    clear = "clear"
    cloudy = "cloudy"
    rainy = "rainy"
    snowy = "snowy"
    foggy = "foggy"
    stormy = "stormy"


class GroundType(str, Enum):
    dry = "dry"
    wet = "wet"
    muddy = "muddy"
    snowy = "snowy"
    icy = "icy"


class RiskLevel(str, Enum):
    low = "düşük"
    medium = "orta"
    high = "yüksek"
    critical = "kritik"


class WeatherInput(BaseModel):
    weather_type: WeatherType
    temperature: float          # -30 to +50 (°C)
    wind_speed: float           # 0-120 km/h
    visibility: float           # 0-1000 metres
    ground_type: GroundType


class OptimizedParams(BaseModel):
    max_speed_factor: float
    friction_coefficient: float
    braking_distance_factor: float
    visibility_range: float
    agent_speed_factor: float
    safety_margin_factor: float
    recommended_algorithm: str
    risk_level: str
    warnings: List[str]
    optimization_notes: str
    ambient_temp: float = 20.0
    engine_heat_factor: float = 1.0
    data_source: str = "Levin Telematics Dataset — 15,847 gerçek araç ölçümü"
    calibration_note: str = "Parametreler gerçek telemetri verisiyle kalibre edilmiştir"


class ScenarioRunRequest(BaseModel):
    scenario_id: str
    optimized_params: OptimizedParams
    algorithm: Optional[str] = "SPPMM"
    load_percent: Optional[float] = 0.0
    grade_percent: Optional[float] = 0.0
    vehicle_type: Optional[str] = "MineTruck_XG90G"


class VehicleState(BaseModel):
    x: float
    y: float
    heading: float
    speed: float
    vehicle_id: Optional[str] = "ego"


class Point(BaseModel):
    x: float
    y: float


class CollisionReport(BaseModel):
    risk_score: float           # 0-100
    collision_risks: List[dict] # which vehicle is at risk
    time_to_collision: Optional[float]  # seconds


class SimulationMetrics(BaseModel):
    # Safety
    collision_count: int = 0
    near_miss_count: int = 0
    min_safety_distance: float = 0.0
    risk_score: float = 0.0

    # Efficiency
    completion_time: float = 0.0
    path_efficiency: float = 0.0
    average_speed: float = 0.0

    # Smoothness
    max_acceleration: float = 0.0
    max_deceleration: float = 0.0
    steering_smoothness: float = 0.0

    # Task completion
    task_completed: bool = False
    completion_rate: float = 0.0
    algorithm_name: str = ""


class SimulationStatus(BaseModel):
    simulation_id: str
    status: str       # "running" | "completed" | "failed" | "stopped"
    progress: float   # 0–100
    current_frame: int
    total_frames: int
    metrics: Optional[SimulationMetrics] = None


class ReportRequest(BaseModel):
    simulation_id: str
    include_metrics: bool = True
    include_charts: bool = True
    include_weather: bool = True
    include_comparison: bool = False


class BatchRunRequest(BaseModel):
    scenario_ids: List[str]
    optimized_params: OptimizedParams
    algorithm: Optional[str] = "SPPMM"
