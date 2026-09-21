import secrets
from datetime import datetime, timedelta, timezone

from app import config
from app.db import connect
from app.engines.night_compare import compare_day_night
from app.engines.tariff_breakdown import calc_fare
from app.repositories import preview_tokens, runs, settings, tariff, trips


class PreviewTokenError(Exception):
    """落表被拒绝：令牌缺失/不存在/过期/已用/被取代，或与预览不一致。"""

    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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

    def fare(self, distance_km, slow_min, night):
        """只读试算：不签发令牌、不写记录（行程详情等只读场景使用）。"""
        t = tariff.get_active(self._c)
        return calc_fare(distance_km, slow_min, night, t)

    def preview_fare(self, distance_km, slow_min, night, trip_id=None):
        """只读预览：签发时效令牌并返回到期时刻，不增加记录条数。

        每次预览都发新令牌，此前未使用的旧令牌立即失效。
        """
        t = tariff.get_active(self._c)
        r = calc_fare(distance_km, slow_min, night, t)
        now = _utcnow()
        ttl = config.PREVIEW_TOKEN_TTL_SECONDS
        expires = now + timedelta(seconds=ttl)
        token = secrets.token_urlsafe(24)
        preview_tokens.supersede_open(self._c)
        preview_tokens.insert(self._c, token, r, trip_id, now.isoformat(), expires.isoformat())
        self._c.commit()
        return {"token": token, "expires_at": expires.isoformat(), "ttl_seconds": ttl, **r}

    def commit_fare(self, token, distance_km, slow_min, night, start, mileage, slow_fee, total, trip_id=None):
        """落表：令牌未过期、未使用、未被取代，且全部金额与预览一致才写入。"""
        if not token:
            raise PreviewTokenError(400, "缺少预览令牌，请先预览")
        row = preview_tokens.get_by_token(self._c, token)
        if not row:
            raise PreviewTokenError(404, "令牌不存在，请重新预览")
        if row["used_at"]:
            raise PreviewTokenError(409, "令牌已使用，每个令牌只能落表一次")
        if row["invalidated"]:
            raise PreviewTokenError(409, "令牌已失效：已有新的预览，请使用最新令牌")
        now = _utcnow()
        if now >= datetime.fromisoformat(row["expires_at"]):
            raise PreviewTokenError(410, "令牌已过期，请重新预览")
        for name, got, want in (
            ("distance_km", distance_km, row["distance_km"]),
            ("slow_min", slow_min, row["slow_min"]),
            ("start", start, row["start"]),
            ("mileage", mileage, row["mileage"]),
            ("slow_fee", slow_fee, row["slow_fee"]),
            ("total", total, row["total"]),
        ):
            if abs(float(got) - float(want)) > 1e-6:
                raise PreviewTokenError(409, f"{name} 与预览不一致，请重新预览")
        if bool(night) != bool(row["night"]):
            raise PreviewTokenError(409, "night 与预览不一致，请重新预览")
        if preview_tokens.mark_used(self._c, row["id"], now.isoformat()) != 1:
            raise PreviewTokenError(409, "令牌已使用，每个令牌只能落表一次")
        result = {
            "distance_km": row["distance_km"], "slow_min": row["slow_min"],
            "night": bool(row["night"]), "night_factor": row["night_factor"],
            "start": row["start"], "mileage": row["mileage"],
            "slow_fee": row["slow_fee"], "total": row["total"],
        }
        payload = {"distance_km": row["distance_km"], "slow_min": row["slow_min"], "night": bool(row["night"])}
        rid = runs.insert(self._c, "fare", payload, result, trip_id if trip_id is not None else row["trip_id"])
        return {"run_id": rid, **result}

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
