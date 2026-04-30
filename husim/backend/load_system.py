"""HÜsim — Load and grade parameter calculation module (Phase E)"""


class LoadSystem:
    VEHICLE_SPECS = {
        "MineTruck_XG90G": {
            "empty_weight_ton": 47,
            "max_payload_ton": 90,
            "empty_max_speed_ms": 15.3,
            "loaded_max_speed_ms": 8.9,
            "empty_max_accel": 1.2,
            "loaded_max_accel": 0.45,
            "empty_brake_dist_m": 35,
            "loaded_brake_dist_m": 55,
        },
        "MineTruck_NTE200": {
            "empty_weight_ton": 98,
            "max_payload_ton": 200,
            "empty_max_speed_ms": 13.3,
            "loaded_max_speed_ms": 6.9,
            "empty_max_accel": 0.9,
            "loaded_max_accel": 0.28,
            "empty_brake_dist_m": 45,
            "loaded_brake_dist_m": 80,
        },
    }

    def get_params(self, vehicle_type: str, load_percent: float, grade_percent: float = 0.0) -> dict:
        """
        Takes load percentage (0-100) and grade percentage (-15..+15).
        Returns: max_speed_ms, max_accel, brake_distance_m,
                 fuel_consumption_factor, load_ton, total_weight_ton
        """
        load_percent = max(0.0, min(100.0, load_percent))
        grade_percent = max(-15.0, min(15.0, grade_percent))

        spec = self.VEHICLE_SPECS.get(vehicle_type, self.VEHICLE_SPECS["MineTruck_XG90G"])
        t = load_percent / 100.0

        # Linear interpolation (empty → fully loaded)
        base_speed = spec["empty_max_speed_ms"] + t * (spec["loaded_max_speed_ms"] - spec["empty_max_speed_ms"])
        base_accel = spec["empty_max_accel"] + t * (spec["loaded_max_accel"] - spec["empty_max_accel"])
        base_brake = spec["empty_brake_dist_m"] + t * (spec["loaded_brake_dist_m"] - spec["empty_brake_dist_m"])

        # Grade effect
        g = abs(grade_percent)
        if grade_percent > 0:
            # Uphill: speed -3%/degree, acceleration -5%/degree
            speed_factor = max(0.3, 1.0 - g * 0.03)
            accel_factor = max(0.2, 1.0 - g * 0.05)
            brake_factor = 1.0
        else:
            # Downhill: speed +2%/degree (cannot exceed max), braking +8%/degree
            speed_factor = min(1.0 + g * 0.02, spec["empty_max_speed_ms"] / max(base_speed, 0.1))
            accel_factor = 1.0
            brake_factor = 1.0 + g * 0.08

        max_speed_ms = round(base_speed * speed_factor, 2)
        max_accel = round(base_accel * accel_factor, 3)
        brake_distance_m = round(base_brake * brake_factor, 1)

        load_ton = round(spec["max_payload_ton"] * t, 1)
        total_weight_ton = round(spec["empty_weight_ton"] + load_ton, 1)

        # Fuel consumption factor: weight + grade
        fuel_base = 1.0 + t * 1.8
        fuel_grade = 1.0 + max(grade_percent, 0) * 0.06
        fuel_consumption_factor = round(fuel_base * fuel_grade, 3)

        return {
            "max_speed_ms": max_speed_ms,
            "max_accel": max_accel,
            "brake_distance_m": brake_distance_m,
            "fuel_consumption_factor": fuel_consumption_factor,
            "load_ton": load_ton,
            "total_weight_ton": total_weight_ton,
        }

    def get_presets(self) -> list:
        presets = []
        for vtype in self.VEHICLE_SPECS:
            for name, pct in [("Boş", 0), ("Yarı Yüklü", 50), ("Tam Yüklü", 100)]:
                params = self.get_params(vtype, pct, 0.0)
                presets.append({
                    "vehicle_type": vtype,
                    "name": name,
                    "load_percent": pct,
                    **params,
                })
        return presets
