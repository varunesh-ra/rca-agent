"""
Error Ingestion Agent — PostgreSQL Database Layer
Connects to the unified rca_db and writes to the error_incidents table.
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import asyncpg

from config.settings import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Return (or create) the shared connection pool."""
    global _pool
    if _pool is None:
        # asyncpg uses postgresql:// DSN directly
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        logger.info("PostgreSQL connection pool created — %s", dsn.split("@")[-1])
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_connection():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def ensure_table() -> None:
    """Create error_incidents table if it doesn't exist (idempotent)."""
    async with get_connection() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS error_incidents (
                id              SERIAL PRIMARY KEY,
                service_name    VARCHAR(255) NOT NULL,
                environment     VARCHAR(100) NOT NULL DEFAULT 'production',
                error_type      VARCHAR(500),
                message         TEXT NOT NULL,
                severity        VARCHAR(50)  DEFAULT 'ERROR',
                stack_trace     TEXT,
                raw_log         TEXT,
                occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                source          VARCHAR(50)  NOT NULL DEFAULT 'db_watcher'
                                CHECK (source IN ('db_watcher', 'datadog_webhook')),
                rca_status      VARCHAR(50)  NOT NULL DEFAULT 'pending'
                                CHECK (rca_status IN ('pending', 'in_progress', 'completed', 'failed')),
                rca_result      TEXT,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_error_incidents_lookup
                ON error_incidents (service_name, rca_status, created_at DESC)
        """)
        logger.info("error_incidents table ready")


async def insert_incident(
    service_name: str,
    environment: str,
    error_type: Optional[str],
    message: str,
    severity: str,
    stack_trace: Optional[str],
    raw_log: str,
    source: str,
    occurred_at: Optional[datetime] = None,
) -> int:
    """
    Insert a new error incident and return its id.

    Args:
        service_name:  Name of the originating service (e.g. 'banking-app')
        environment:   Deployment environment (e.g. 'production')
        error_type:    Exception class or error category
        message:       Human-readable error description
        severity:      Log level string: ERROR, WARN, INFO, etc.
        stack_trace:   Extracted stack trace (None if unavailable)
        raw_log:       Full raw log entry text
        source:        'db_watcher' or 'datadog_webhook'
        occurred_at:   When the error occurred (defaults to NOW())

    Returns:
        The new incident's id (int)
    """
    async with get_connection() as conn:
        incident_id = await conn.fetchval(
            """
            INSERT INTO error_incidents
                (service_name, environment, error_type, message, severity,
                 stack_trace, raw_log, source, occurred_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
            """,
            service_name,
            environment,
            error_type,
            message,
            severity,
            stack_trace,
            raw_log,
            source,
            occurred_at or datetime.utcnow(),
        )
        logger.info(
            "Incident #%d inserted — service=%s severity=%s source=%s",
            incident_id, service_name, severity, source,
        )
        return incident_id
