import sqlite3


def supersede_open(conn: sqlite3.Connection) -> None:
    """签发新令牌前，把所有未使用的旧令牌立即作废。"""
    conn.execute("UPDATE fare_tokens SET invalidated=1 WHERE used_at IS NULL AND invalidated=0")


def insert(conn: sqlite3.Connection, token: str, result: dict, trip_id, created_at: str, expires_at: str) -> None:
    conn.execute(
        """INSERT INTO fare_tokens(token,distance_km,slow_min,night,night_factor,start,mileage,slow_fee,total,trip_id,created_at,expires_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            token,
            result["distance_km"], result["slow_min"], int(result["night"]), result["night_factor"],
            result["start"], result["mileage"], result["slow_fee"], result["total"],
            trip_id, created_at, expires_at,
        ),
    )


def get_by_token(conn: sqlite3.Connection, token: str) -> dict | None:
    row = conn.execute("SELECT * FROM fare_tokens WHERE token=?", (token,)).fetchone()
    return dict(row) if row else None


def mark_used(conn: sqlite3.Connection, token_id: int, used_at: str) -> int:
    """条件更新保证每个令牌只落表一次；返回受影响行数。"""
    cur = conn.execute(
        "UPDATE fare_tokens SET used_at=? WHERE id=? AND used_at IS NULL AND invalidated=0",
        (used_at, token_id),
    )
    return cur.rowcount
