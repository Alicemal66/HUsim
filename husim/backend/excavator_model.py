"""HÜsim — Ekskavatör modeli (kazı döngüsü ve üretim hesaplama)"""


class ExcavatorModel:
    """Maden ekskavatörü için kazı döngüsü ve üretim simülasyonu."""

    IDLE_STATE = "beklemede"
    DIGGING_STATE = "kazıyor"
    SWINGING_STATE = "dönüyor"
    DUMPING_STATE = "boşaltıyor"
    WAITING_STATE = "araç_bekliyor"

    def __init__(self, excavator_id: str = "EX-001", bucket_capacity_m3: float = 15.0):
        self.excavator_id = excavator_id
        self.bucket_capacity_m3 = bucket_capacity_m3
        self.state: str = self.IDLE_STATE
        self.cycle_time_s: float = 0.0
        self.total_cycles: int = 0
        self.total_volume_m3: float = 0.0
        self.current_truck_id: str | None = None
        self._state_elapsed: float = 0.0

        # Ortalama döngü süreleri (saniye)
        self._phase_times = {
            self.DIGGING_STATE: 15.0,
            self.SWINGING_STATE: 10.0,
            self.DUMPING_STATE: 8.0,
            self.WAITING_STATE: 0.0,
        }

    def assign_truck(self, truck_id: str) -> None:
        self.current_truck_id = truck_id
        if self.state == self.WAITING_STATE:
            self.state = self.DIGGING_STATE
            self._state_elapsed = 0.0

    def release_truck(self) -> None:
        self.current_truck_id = None
        self.state = self.WAITING_STATE
        self._state_elapsed = 0.0

    def update(self, dt: float = 0.1) -> dict:
        if self.state == self.IDLE_STATE or self.state == self.WAITING_STATE:
            return self._status()

        self._state_elapsed += dt
        self.cycle_time_s += dt
        phase_dur = self._phase_times.get(self.state, 10.0)

        if self._state_elapsed >= phase_dur:
            self._state_elapsed = 0.0
            if self.state == self.DIGGING_STATE:
                self.state = self.SWINGING_STATE
            elif self.state == self.SWINGING_STATE:
                self.state = self.DUMPING_STATE
            elif self.state == self.DUMPING_STATE:
                self.total_cycles += 1
                self.total_volume_m3 += self.bucket_capacity_m3
                self.cycle_time_s = 0.0
                if self.current_truck_id:
                    self.state = self.DIGGING_STATE
                else:
                    self.state = self.WAITING_STATE

        return self._status()

    def production_rate_m3h(self) -> float:
        full_cycle = sum(self._phase_times.values())
        if full_cycle <= 0:
            return 0.0
        return (self.bucket_capacity_m3 / full_cycle) * 3600.0

    def _status(self) -> dict:
        return {
            "excavator_id": self.excavator_id,
            "state": self.state,
            "total_cycles": self.total_cycles,
            "total_volume_m3": round(self.total_volume_m3, 1),
            "production_rate_m3h": round(self.production_rate_m3h(), 1),
            "assigned_truck": self.current_truck_id,
        }
