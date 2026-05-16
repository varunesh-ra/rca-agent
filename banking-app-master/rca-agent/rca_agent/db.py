import json
import pymysql
import pymysql.cursors
from contextlib import contextmanager
from urllib.parse import urlparse
from .config import settings


def _conn_kwargs() -> dict:
    url = settings.database_url
    # Accept mysql+pymysql:// or mysql://
    url = url.replace("mysql+pymysql://", "mysql://").replace("mysql+mysqldb://", "mysql://")
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
    }


@contextmanager
def get_conn():
    conn = pymysql.connect(**_conn_kwargs())
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
        with conn.cursor() as cur:
            cur.execute(sql, params)
            try:
                rows = cur.fetchall()
                return [dict(r) for r in rows] if rows else []
            except Exception:
                return []


def execute_one(sql: str, params=None) -> dict | None:
    rows = execute(sql, params)
    return rows[0] if rows else None


def json_loads(v):
    """Safely parse a JSON value that may already be a dict/list (from ORM) or a string."""
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    return json.loads(v)
