import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from .config import settings


@contextmanager
def get_conn():
    conn = psycopg2.connect(settings.database_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute(sql: str, params=None) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            try:
                return [dict(r) for r in cur.fetchall()]
            except Exception:
                return []


def execute_one(sql: str, params=None) -> dict | None:
    rows = execute(sql, params)
    return rows[0] if rows else None
