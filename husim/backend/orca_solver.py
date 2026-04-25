"""ORCA — Optimal Reciprocal Collision Avoidance (pure numpy).

van den Berg et al., "Reciprocal n-Body Collision Avoidance", 2011.
"""
import math
import numpy as np

_EPS = 1e-8


class ORCASolver:
    """
    ORCA solver: her frame'de tüm araçlar için çarpışmasız hız hesaplar.
    """

    def __init__(self, time_horizon: float = 5.0, time_step: float = 0.1):
        self.time_horizon = time_horizon
        self.time_step = time_step

    def compute_new_velocities(self, agents: list) -> list:
        """
        Tüm araçlar için çarpışmasız yeni hız hesapla.

        agents: Her eleman şu alanları içeren dict:
            id, x, y, vx, vy, pref_vx, pref_vy, radius, max_speed
            Optional: reciprocal (bool, default True)
                      False ise bu araç kendi yönünü değiştirmez (NPC);
                      EGO tek başına tüm sorumluluk alır.

        Döndür: [{id, new_vx, new_vy, new_speed, new_heading}, ...]
        """
        results = []
        for i, a in enumerate(agents):
            orca_lines = []
            for j, b in enumerate(agents):
                if i == j:
                    continue
                line = self._compute_orca_line(a, b, b.get("reciprocal", True))
                if line is not None:
                    orca_lines.append(line)

            pref = np.array([a["pref_vx"], a["pref_vy"]], dtype=float)
            max_spd = float(a["max_speed"])

            new_vel, fail_idx = self._lp2(orca_lines, max_spd, pref, False)
            if fail_idx < len(orca_lines):
                new_vel = self._lp3(orca_lines, 0, fail_idx, max_spd, new_vel)

            speed = float(np.linalg.norm(new_vel))
            if speed > 0.01:
                heading = math.atan2(float(new_vel[1]), float(new_vel[0]))
            elif abs(a["vx"]) + abs(a["vy"]) > 0.01:
                heading = math.atan2(float(a["vy"]), float(a["vx"]))
            else:
                heading = 0.0

            results.append({
                "id": a["id"],
                "new_vx": float(new_vel[0]),
                "new_vy": float(new_vel[1]),
                "new_speed": speed,
                "new_heading": heading,
            })

        return results

    # ── ORCA yarı düzlemi ──────────────────────────────────────────────────────

    def _compute_orca_line(self, a: dict, b: dict, b_reciprocal: bool = True):
        """
        Agent a için, agent b'ye göre ORCA yarı düzlemini hesapla.
        Döndür: (point, direction) veya None.

        RVO2 C++ kaynak koduna dayalı implementasyon.
        """
        inv_tau = 1.0 / self.time_horizon

        rel_pos = np.array([b["x"] - a["x"], b["y"] - a["y"]], dtype=float)
        rel_vel = np.array([a["vx"] - b["vx"], a["vy"] - b["vy"]], dtype=float)
        dist_sq = float(np.dot(rel_pos, rel_pos))
        combined_r = float(a["radius"] + b["radius"])
        combined_r_sq = combined_r * combined_r

        # b reciprocal değilse (NPC, sabit yörüngeli) EGO tam sorumluluk alır
        resp = 0.5 if b_reciprocal else 1.0

        if dist_sq > combined_r_sq:
            # Çakışma yok
            w = rel_vel - inv_tau * rel_pos
            w_sq = float(np.dot(w, w))
            dot1 = float(np.dot(w, rel_pos))

            if dot1 < 0.0 and dot1 * dot1 > combined_r_sq * w_sq:
                # Cut-off çemberine project et
                w_len = math.sqrt(max(w_sq, 0.0))
                if w_len < _EPS:
                    return None
                unit_w = w / w_len
                direction = np.array([unit_w[1], -unit_w[0]])
                u = (combined_r * inv_tau - w_len) * unit_w
            else:
                # VO konisinin bacaklarına project et
                leg_sq = max(0.0, dist_sq - combined_r_sq)
                leg = math.sqrt(leg_sq)
                cross_pw = float(rel_pos[0] * w[1] - rel_pos[1] * w[0])

                if cross_pw > 0.0:
                    # Sol bacak
                    direction = np.array([
                        rel_pos[0] * leg - rel_pos[1] * combined_r,
                        rel_pos[0] * combined_r + rel_pos[1] * leg,
                    ]) / dist_sq
                else:
                    # Sağ bacak
                    direction = -np.array([
                        rel_pos[0] * leg + rel_pos[1] * combined_r,
                        -rel_pos[0] * combined_r + rel_pos[1] * leg,
                    ]) / dist_sq

                dot2 = float(np.dot(rel_vel, direction))
                u = dot2 * direction - rel_vel
        else:
            # Çakışma var — time_step anında çemberden çık
            inv_ts = 1.0 / self.time_step
            w = rel_vel - inv_ts * rel_pos
            w_len = float(np.linalg.norm(w))
            if w_len < _EPS:
                if dist_sq > _EPS:
                    d = math.sqrt(dist_sq)
                    direction = np.array([-rel_pos[1] / d, rel_pos[0] / d])
                else:
                    direction = np.array([0.0, 1.0])
                u = combined_r * inv_ts * np.array([-direction[1], direction[0]])
            else:
                unit_w = w / w_len
                direction = np.array([unit_w[1], -unit_w[0]])
                u = (combined_r * inv_ts - w_len) * unit_w

        point = np.array([a["vx"], a["vy"]]) + resp * u
        return (point, direction)

    # ── Lineer Programlama ─────────────────────────────────────────────────────

    def _lp1(self, lines, line_no, radius, opt_vel, dir_opt):
        """Tek bir kısıt üzerinde optimal nokta bul (hız dairesi + önceki kısıtlar)."""
        lp, ld = lines[line_no]
        dot = float(np.dot(lp, ld))
        disc = dot * dot + radius * radius - float(np.dot(lp, lp))
        if disc < 0.0:
            return False, None

        sqrt_d = math.sqrt(disc)
        t_lo = -dot - sqrt_d
        t_hi = -dot + sqrt_d

        for i in range(line_no):
            op, od = lines[i]
            denom = float(ld[0] * od[1] - ld[1] * od[0])
            numer = float(od[0] * (lp[1] - op[1]) - od[1] * (lp[0] - op[0]))
            if abs(denom) < _EPS:
                if numer < 0.0:
                    return False, None
                continue
            t = numer / denom
            if denom >= 0.0:
                t_hi = min(t_hi, t)
            else:
                t_lo = max(t_lo, t)
            if t_lo > t_hi + _EPS:
                return False, None

        if dir_opt:
            t = t_hi if float(np.dot(opt_vel, ld)) > 0.0 else t_lo
        else:
            t = float(np.dot(opt_vel - lp, ld))
            t = max(t_lo, min(t, t_hi))

        return True, lp + t * ld

    def _lp2(self, lines, radius, opt_vel, dir_opt):
        """
        Tüm ORCA kısıtlarını sağlayan, opt_vel'e en yakın hızı bul.
        Döndür: (velocity, fail_index) — fail_index == len(lines) ise başarılı.
        """
        if dir_opt:
            n = float(np.linalg.norm(opt_vel))
            result = opt_vel * (radius / n) if n > _EPS else np.array([radius, 0.0])
        elif float(np.dot(opt_vel, opt_vel)) > radius * radius:
            result = opt_vel * (radius / float(np.linalg.norm(opt_vel)))
        else:
            result = opt_vel.copy()

        for i, (lp, ld) in enumerate(lines):
            normal = np.array([-ld[1], ld[0]])
            if float(np.dot(normal, lp - result)) > 0.0:
                old = result.copy()
                ok, new_r = self._lp1(lines, i, radius, opt_vel, dir_opt)
                if not ok:
                    return old, i
                result = new_r

        return result, len(lines)

    def _lp3(self, lines, num_obs, begin, radius, result):
        """
        İnfeasible durum: minimum penetrasyonu minimize eden hızı bul.
        """
        distance = 0.0
        for i in range(begin, len(lines)):
            lp_i, ld_i = lines[i]
            n_i = np.array([-ld_i[1], ld_i[0]])
            if float(np.dot(n_i, lp_i - result)) > distance:
                proj = list(lines[:num_obs])
                for j in range(num_obs, i):
                    lp_j, ld_j = lines[j]
                    det2 = float(ld_i[0] * ld_j[1] - ld_i[1] * ld_j[0])
                    if abs(det2) < _EPS:
                        if float(np.dot(ld_i, ld_j)) > 0.0:
                            continue
                        new_pt = 0.5 * (lp_i + lp_j)
                        dn = float(np.linalg.norm(ld_j))
                        new_dir = ld_j / dn if dn > _EPS else np.array([1.0, 0.0])
                    else:
                        t = float(ld_j[0] * (lp_i[1] - lp_j[1]) - ld_j[1] * (lp_i[0] - lp_j[0])) / det2
                        new_pt = lp_i + t * ld_i
                        diff = ld_j - ld_i
                        dn = float(np.linalg.norm(diff))
                        new_dir = diff / dn if dn > _EPS else ld_i / max(float(np.linalg.norm(ld_i)), _EPS)
                    proj.append((new_pt, new_dir))

                opt = np.array([-ld_i[1], ld_i[0]])
                temp = result.copy()
                new_r, fi2 = self._lp2(proj, radius, opt, True)
                if fi2 >= len(proj):
                    result = new_r
                else:
                    result = temp
                distance = float(np.dot(n_i, lp_i - result))
        return result


# ── Yardımcı dönüşüm fonksiyonları ───────────────────────────────────────────

def heading_to_velocity(heading: float, speed: float) -> tuple:
    """heading (radyan) ve speed (m/s) → (vx, vy)"""
    return speed * math.cos(heading), speed * math.sin(heading)


def velocity_to_heading(vx: float, vy: float) -> tuple:
    """(vx, vy) → (heading radyan, speed m/s)"""
    speed = math.sqrt(vx * vx + vy * vy)
    heading = math.atan2(vy, vx)
    return heading, speed
