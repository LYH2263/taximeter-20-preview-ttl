import json
import secrets
from datetime import datetime, timedelta, timezone

from app.db import connect
from app.engines.night_compare import compare_day_night
from app.engines.tariff_breakdown import calc_fare
from app.repositories import runs, settings, tariff, tokens, trips

PREVIEW_TTL_SECONDS = 120  # 预览令牌有效期（秒）

class FareTokenError(Exception):
    """落表令牌校验失败（缺失/过期/已用/已作废/与预览不一致）。"""

def _close(a, b):
    return abs(float(a) - float(b)) <= 1e-6

class TaxiService:
    def __init__(self): self._c = connect()
    def close(self): self._c.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def list_trips(self): return trips.list_all(self._c)
    def trip(self, tid): return trips.get(self._c, tid)
    def tariff(self): return tariff.get_active(self._c)
    def settings(self): return settings.get_map(self._c)
    def history(self, limit=50): return runs.list_recent(self._c, limit)

    def preview_fare(self, distance_km, slow_min, night, trip_id=None):
        """只读预览：计算并签发时效令牌，不写记录。连续预览会使旧令牌立即失效。"""
        t = tariff.get_active(self._c)
        r = calc_fare(distance_km, slow_min, night, t)
        payload = {"distance_km": r["distance_km"], "slow_min": r["slow_min"], "night": r["night"]}
        token = secrets.token_urlsafe(16)
        expires = datetime.now(timezone.utc) + timedelta(seconds=PREVIEW_TTL_SECONDS)
        tokens.issue(self._c, token, trip_id, payload, r, expires.isoformat())
        return {"token": token, "expires_at": expires.isoformat(), "ttl_seconds": PREVIEW_TTL_SECONDS, **r}

    def commit_fare(self, token, distance_km, slow_min, night, start, mileage, slow_fee, total):
        """落表：令牌未过期、未使用、未作废，且入参与金额均与预览一致才写入；令牌一次性。"""
        row = tokens.get(self._c, token)
        if not row:
            raise FareTokenError("令牌缺失或无效，请先预览")
        if row["used"]:
            raise FareTokenError("令牌已被使用，请重新预览")
        if row["superseded"]:
            raise FareTokenError("令牌已失效，请重新预览")
        now = datetime.now(timezone.utc)
        if now > datetime.fromisoformat(row["expires_at"]):
            raise FareTokenError("令牌已过期，请重新预览")
        pin = json.loads(row["input_json"])
        pres = json.loads(row["result_json"])
        if not (_close(distance_km, pin["distance_km"]) and _close(slow_min, pin["slow_min"]) and bool(night) == bool(pin["night"])):
            raise FareTokenError("公里/低速/夜间与预览不一致，请重新预览")
        if not (_close(start, pres["start"]) and _close(mileage, pres["mileage"])
                and _close(slow_fee, pres["slow_fee"]) and _close(total, pres["total"])):
            raise FareTokenError("起步/里程/低速/应付与预览不一致，请重新预览")
        if not tokens.claim(self._c, token, now.isoformat()):
            raise FareTokenError("令牌已被使用，请重新预览")
        rid = runs.insert(self._c, "fare", pin, pres, row["trip_id"])
        return {"run_id": rid, **pres}

    def quote_fare(self, distance_km, slow_min, night):
        """行程详情等只读试算：不签发令牌、不写记录，结果不可用于落表。"""
        t = tariff.get_active(self._c)
        return calc_fare(distance_km, slow_min, night, t)

    def compare(self, distance_km, slow_min, persist):
        t = tariff.get_active(self._c)
        r = compare_day_night(distance_km, slow_min, t)
        rid = runs.insert(self._c, "compare", {"distance_km": distance_km, "slow_min": slow_min}, r, None) if persist else None
        return {"run_id": rid, **r}
    def dashboard(self):
        items = trips.list_all(self._c)
        clean = [x for x in items if "种子" not in x["label"]]
        dirty = [x for x in items if "种子" in x["label"]]
        return {"trip_count": len(items), "clean": len(clean), "dirty": len(dirty)}
