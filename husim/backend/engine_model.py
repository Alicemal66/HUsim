"""HÜsim — Engine temperature model (Phase F)"""


class EngineModel:
    WARNING_THRESHOLD = 105.0
    CRITICAL_THRESHOLD = 115.0
    EMERGENCY_THRESHOLD = 125.0

    def __init__(self, vehicle_type: str = "MineTruck_XG90G"):
        self.vehicle_type = vehicle_type
        self.temperature: float = 80.0
        self.history: list[float] = []

    def update(
        self,
        load_percent: float,
        grade_percent: float,
        ambient_temp: float,
        current_speed: float,
        dt: float = 0.1,
    ) -> dict:
        is_moving = current_speed > 0.3
        # 0.5 (empty vehicle) → 1.0 (fully loaded)
        load_factor = 0.5 + (load_percent / 100.0) * 0.5

        if is_moving:
            if grade_percent > 0:
                fraction = min(1.0, grade_percent / 15.0)
                rate_per_min = 0.8 + fraction * (2.5 - 0.8)
            elif grade_percent < 0:
                rate_per_min = 0.3
            else:
                rate_per_min = 0.8

            rate_per_min *= load_factor
            temp_factor = 1.0 + max(-0.3, (ambient_temp - 20.0) / 10.0 * 0.15)
            rate_per_min *= temp_factor
            delta = rate_per_min * dt / 60.0
        else:
            cooling = 3.0
            if ambient_temp < -10:
                cooling *= 1.5
            delta = -cooling * dt / 60.0

        self.temperature = max(60.0, min(150.0, self.temperature + delta))
        self.history.append(round(self.temperature, 1))
        if len(self.history) > 2000:
            self.history = self.history[-2000:]
        return self._status()

    def _status(self) -> dict:
        t = round(self.temperature, 1)
        if t >= self.EMERGENCY_THRESHOLD:
            return {
                "temperature": t,
                "status": "acil_durdurma",
                "speed_limit_factor": 0.0,
                "warning_message": "Kritik sıcaklık! Araç durduruluyor",
            }
        if t >= self.CRITICAL_THRESHOLD:
            return {
                "temperature": t,
                "status": "kritik",
                "speed_limit_factor": 0.4,
                "warning_message": "Motor aşırı ısınıyor, hız kısıtlandı",
            }
        if t >= self.WARNING_THRESHOLD:
            return {
                "temperature": t,
                "status": "uyarı",
                "speed_limit_factor": 0.7,
                "warning_message": "Motor ısınıyor",
            }
        return {
            "temperature": t,
            "status": "normal",
            "speed_limit_factor": 1.0,
            "warning_message": None,
        }
