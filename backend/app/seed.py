import json
from app.db import connect
from app.engines.tariff_breakdown import calc_fare

TARIFF = {"start_price": 11, "start_include_km": 3, "per_km": 2.5, "per_slow_min": 0.8, "night_factor": 1.2}

def init_db():
    conn = connect()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS tariff(id INTEGER PRIMARY KEY, start_price REAL, start_include_km REAL, per_km REAL, per_slow_min REAL, night_factor REAL);
    CREATE TABLE IF NOT EXISTS trips(id INTEGER PRIMARY KEY, label TEXT, distance_km REAL, slow_min REAL, night INTEGER);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS calc_runs(id INTEGER PRIMARY KEY, kind TEXT, trip_id INTEGER, input_json TEXT, result_json TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS fare_tokens(token TEXT PRIMARY KEY, trip_id INTEGER, input_json TEXT, result_json TEXT, expires_at TEXT, used INTEGER DEFAULT 0, superseded INTEGER DEFAULT 0, created_at TEXT);
    """)
    if conn.execute("SELECT COUNT(*) c FROM tariff").fetchone()["c"] == 0:
        conn.execute("INSERT INTO tariff(start_price,start_include_km,per_km,per_slow_min,night_factor) VALUES (11,3,2.5,0.8,1.2)")
        conn.execute("INSERT INTO trips(label,distance_km,slow_min,night) VALUES ('白天短途',5.0,2,0)")
        conn.execute("INSERT INTO trips(label,distance_km,slow_min,night) VALUES ('夜间长途(种子)',18.0,12,1)")
        conn.execute("INSERT INTO settings(key,value) VALUES ('currency','CNY')")
        r = calc_fare(5, 2, False, TARIFF)
        conn.execute("INSERT INTO calc_runs(kind,trip_id,input_json,result_json,created_at) VALUES ('fare',1,?,?,datetime('now'))",
            (json.dumps({"distance_km":5,"slow_min":2,"night":False}), json.dumps(r)))
        conn.commit()
    conn.close()
