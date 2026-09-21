import json, sqlite3
from datetime import datetime, timezone

def issue(conn, token, trip_id, payload, result, expires_at):
    """签发新令牌：同类型旧令牌立即作废（superseded=1），再写入新令牌。"""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("UPDATE fare_tokens SET superseded=1 WHERE used=0 AND superseded=0")
    conn.execute(
        "INSERT INTO fare_tokens(token,trip_id,input_json,result_json,expires_at,used,superseded,created_at) VALUES (?,?,?,?,?,0,0,?)",
        (token, trip_id, json.dumps(payload, ensure_ascii=False), json.dumps(result, ensure_ascii=False), expires_at, now),
    )
    conn.commit()

def get(conn, token):
    if not token:
        return None
    row = conn.execute("SELECT * FROM fare_tokens WHERE token=?", (token,)).fetchone()
    return dict(row) if row else None

def claim(conn, token, now_iso):
    """原子认领：仅当令牌未使用、未作废、未过期时置 used=1。返回是否认领成功。"""
    cur = conn.execute(
        "UPDATE fare_tokens SET used=1 WHERE token=? AND used=0 AND superseded=0 AND expires_at>?",
        (token, now_iso),
    )
    return cur.rowcount == 1
