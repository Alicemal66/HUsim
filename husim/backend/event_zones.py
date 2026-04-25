"""HÜsim — Olay bölgesi yönetimi (Faza F)"""
import uuid
import math
import random

EVENT_TYPES: dict[str, dict] = {
    "kaya_dusme": {
        "name": "Kaya Düşmesi",
        "speed_factor": 0.0,
        "radius_m": 15,
        "duration_s": 30,
        "color": "#ef4444",
        "icon": "🪨",
    },
    "yol_calismasi": {
        "name": "Yol Çalışması",
        "speed_factor": 0.3,
        "radius_m": 25,
        "duration_s": 120,
        "color": "#f59e0b",
        "icon": "🚧",
    },
    "su_birikintisi": {
        "name": "Su Birikintisi",
        "speed_factor": 0.5,
        "radius_m": 10,
        "duration_s": 60,
        "color": "#3b82f6",
        "icon": "💧",
    },
    "toz_bulutu": {
        "name": "Toz Bulutu",
        "speed_factor": 0.4,
        "radius_m": 30,
        "duration_s": 45,
        "color": "#92400e",
        "icon": "💨",
    },
    "diger_arac_arizasi": {
        "name": "Araç Arızası",
        "speed_factor": 0.0,
        "radius_m": 12,
        "duration_s": 90,
        "color": "#7c3aed",
        "icon": "🔧",
    },
}


class EventZoneManager:
    def __init__(self):
        self._events: dict[str, dict] = {}

    def add_event(self, x: float, y: float, event_type: str, start_time: float) -> str:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"Bilinmeyen olay tipi: {event_type}")
        eid = str(uuid.uuid4())[:8]
        info = EVENT_TYPES[event_type]
        self._events[eid] = {
            "id": eid,
            "type": event_type,
            "name": info["name"],
            "x": x,
            "y": y,
            "radius_m": info["radius_m"],
            "speed_factor": info["speed_factor"],
            "duration_s": info["duration_s"],
            "color": info["color"],
            "icon": info["icon"],
            "start_time": start_time,
            "end_time": start_time + info["duration_s"],
        }
        return eid

    def remove_event(self, event_id: str) -> None:
        self._events.pop(event_id, None)

    def get_active_events(self, current_time: float) -> list[dict]:
        expired = [eid for eid, ev in self._events.items() if current_time > ev["end_time"]]
        for eid in expired:
            del self._events[eid]
        return [
            {**ev, "remaining_time": round(ev["end_time"] - current_time, 1)}
            for ev in self._events.values()
        ]

    def check_vehicle_in_event(self, vx: float, vy: float, current_time: float) -> dict | None:
        in_zone = [
            ev for ev in self.get_active_events(current_time)
            if math.hypot(vx - ev["x"], vy - ev["y"]) < ev["radius_m"]
        ]
        return min(in_zone, key=lambda e: e["speed_factor"]) if in_zone else None

    def get_speed_factor(self, vx: float, vy: float, current_time: float) -> float:
        ev = self.check_vehicle_in_event(vx, vy, current_time)
        return ev["speed_factor"] if ev else 1.0

    def clear(self) -> None:
        self._events.clear()

    def get_all_events(self) -> list[dict]:
        return list(self._events.values())

    def add_random_events(self, count: int, x_range: tuple, y_range: tuple, start_time: float) -> list[str]:
        types = list(EVENT_TYPES.keys())
        ids = []
        for _ in range(count):
            x = random.uniform(*x_range)
            y = random.uniform(*y_range)
            t = random.choice(types)
            ids.append(self.add_event(x, y, t, start_time))
        return ids
