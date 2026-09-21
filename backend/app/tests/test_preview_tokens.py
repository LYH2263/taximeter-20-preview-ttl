import pytest
from fastapi.testclient import TestClient

import app.db as db
from app import config
from app.main import app

INPUT = {"distance_km": 8, "slow_min": 3, "night": False}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as c:
        yield c


def runs_count():
    conn = db.connect()
    n = conn.execute("SELECT COUNT(*) c FROM calc_runs").fetchone()["c"]
    conn.close()
    return n


def preview(client, **kw):
    r = client.post("/api/fare/preview", json={**INPUT, **kw})
    assert r.status_code == 200
    return r.json()


def commit_body(p, **kw):
    body = {k: p[k] for k in ("token", "distance_km", "slow_min", "night", "start", "mileage", "slow_fee", "total")}
    body.update(kw)
    return body


def test_preview_issues_token_without_record(client):
    before = runs_count()
    p = preview(client)
    assert p["token"]
    assert p["expires_at"] and p["ttl_seconds"] > 0
    assert p["total"] == 25.9  # 11 + (8-3)*2.5 + 3*0.8
    assert runs_count() == before  # 只读预览不增加记录条数


def test_commit_with_valid_token_writes_record(client):
    before = runs_count()
    p = preview(client)
    r = client.post("/api/fare/commit", json=commit_body(p))
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] and body["total"] == p["total"]
    assert runs_count() == before + 1


def test_commit_missing_token_rejected(client):
    before = runs_count()
    r = client.post("/api/fare/commit", json={"distance_km": 8, "slow_min": 3, "start": 11, "mileage": 12.5, "slow_fee": 2.4, "total": 25.9})
    assert r.status_code == 422  # 字段缺失
    r = client.post("/api/fare/commit", json=commit_body(preview(client), token=""))
    assert r.status_code == 400
    assert runs_count() == before


def test_commit_unknown_token_rejected(client):
    before = runs_count()
    r = client.post("/api/fare/commit", json=commit_body(preview(client), token="no-such-token"))
    assert r.status_code == 404
    assert runs_count() == before


def test_token_single_use(client):
    before = runs_count()
    p = preview(client)
    assert client.post("/api/fare/commit", json=commit_body(p)).status_code == 200
    r = client.post("/api/fare/commit", json=commit_body(p))
    assert r.status_code == 409  # 每个令牌只能落表一次
    assert runs_count() == before + 1


def test_expired_token_rejected(client, monkeypatch):
    monkeypatch.setattr(config, "PREVIEW_TOKEN_TTL_SECONDS", -1)
    before = runs_count()
    p = preview(client)
    r = client.post("/api/fare/commit", json=commit_body(p))
    assert r.status_code == 410
    assert runs_count() == before


def test_new_preview_invalidates_old_token(client):
    before = runs_count()
    old = preview(client)
    new = preview(client)
    assert old["token"] != new["token"]
    r = client.post("/api/fare/commit", json=commit_body(old))
    assert r.status_code == 409  # 旧令牌立即失效
    assert runs_count() == before
    r = client.post("/api/fare/commit", json=commit_body(new))
    assert r.status_code == 200
    assert runs_count() == before + 1


def test_commit_mismatch_rejected(client):
    before = runs_count()
    p = preview(client)
    for field, bad in (("distance_km", 9), ("slow_min", 5), ("night", True),
                       ("start", 12), ("mileage", 13), ("slow_fee", 3), ("total", 99)):
        r = client.post("/api/fare/commit", json=commit_body(p, **{field: bad}))
        assert r.status_code == 409, field
    assert runs_count() == before
    # 全部一致仍可落表（前面的拒绝没有消耗令牌）
    assert client.post("/api/fare/commit", json=commit_body(p)).status_code == 200
    assert runs_count() == before + 1


def test_plain_fare_calc_is_read_only(client):
    before = runs_count()
    r = client.post("/api/fare", json=INPUT)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 25.9
    assert "token" not in body and "run_id" not in body  # 不签发可落表令牌、不写记录
    assert runs_count() == before
