import pytest

import app.db as db
from app import seed
from app.services import taxi_service
from app.services.taxi_service import FareTokenError, TaxiService


@pytest.fixture()
def svc(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    seed.init_db()
    s = TaxiService()
    yield s
    s.close()


def run_count(svc):
    return len(svc.history(1000))


def commit_args(p, **over):
    a = {"token": p["token"], "distance_km": p["distance_km"], "slow_min": p["slow_min"],
         "night": p["night"], "start": p["start"], "mileage": p["mileage"],
         "slow_fee": p["slow_fee"], "total": p["total"]}
    a.update(over)
    return a


def test_preview_issues_token_and_expiry_without_record(svc):
    before = run_count(svc)
    p = svc.preview_fare(8, 3, False)
    assert p["token"] and p["expires_at"] and p["ttl_seconds"] > 0
    assert p["total"] > 0
    assert run_count(svc) == before  # 预览不落表


def test_commit_with_valid_token_writes_one_record(svc):
    p = svc.preview_fare(8, 3, False)
    r = svc.commit_fare(**commit_args(p))
    assert r["run_id"] is not None
    assert r["total"] == p["total"]
    assert run_count(svc) == 2  # 种子 1 条 + 本次 1 条


def test_commit_missing_token_rejected(svc):
    before = run_count(svc)
    with pytest.raises(FareTokenError):
        svc.commit_fare(**commit_args({"token": "no-such-token", "distance_km": 8, "slow_min": 3,
                                       "night": False, "start": 0, "mileage": 0, "slow_fee": 0, "total": 0}))
    assert run_count(svc) == before


def test_commit_expired_token_rejected(svc, monkeypatch):
    monkeypatch.setattr(taxi_service, "PREVIEW_TTL_SECONDS", -1)  # 签发即过期
    p = svc.preview_fare(8, 3, False)
    before = run_count(svc)
    with pytest.raises(FareTokenError, match="过期"):
        svc.commit_fare(**commit_args(p))
    assert run_count(svc) == before


def test_token_single_use(svc):
    p = svc.preview_fare(8, 3, False)
    svc.commit_fare(**commit_args(p))
    before = run_count(svc)
    with pytest.raises(FareTokenError, match="已被使用"):
        svc.commit_fare(**commit_args(p))
    assert run_count(svc) == before


def test_new_preview_invalidates_previous_token(svc):
    p1 = svc.preview_fare(8, 3, False)
    p2 = svc.preview_fare(5, 2, True)
    assert p1["token"] != p2["token"]
    before = run_count(svc)
    with pytest.raises(FareTokenError, match="已失效"):
        svc.commit_fare(**commit_args(p1))
    assert run_count(svc) == before
    r = svc.commit_fare(**commit_args(p2))  # 新令牌可正常落表
    assert r["run_id"] is not None
    assert run_count(svc) == before + 1


@pytest.mark.parametrize("field, bad", [
    ("distance_km", 99.0),   # 公里不一致
    ("slow_min", 99.0),      # 低速不一致
    ("night", True),         # 夜间不一致
    ("start", 0.01),         # 起步不一致
    ("mileage", 0.01),       # 里程不一致
    ("slow_fee", 0.01),      # 低速费不一致
    ("total", 0.01),         # 应付不一致
])
def test_commit_mismatched_values_rejected(svc, field, bad):
    p = svc.preview_fare(8, 3, False)
    before = run_count(svc)
    with pytest.raises(FareTokenError, match="不一致"):
        svc.commit_fare(**commit_args(p, **{field: bad}))
    assert run_count(svc) == before


def test_quote_is_read_only_and_issues_no_token(svc):
    before = run_count(svc)
    q = svc.quote_fare(18, 12, True)
    assert q["total"] > 0 and "token" not in q
    assert run_count(svc) == before
