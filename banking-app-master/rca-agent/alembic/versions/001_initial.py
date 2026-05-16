"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.execute("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            service_name    TEXT NOT NULL,
            environment     TEXT NOT NULL,
            error_type      TEXT NOT NULL,
            error_message   TEXT NOT NULL,
            stack_trace     JSONB NOT NULL,
            severity        TEXT NOT NULL,
            occurred_at     TIMESTAMPTZ NOT NULL,
            request_id      TEXT,
            user_id         TEXT,
            metadata        JSONB DEFAULT '{}',
            rca_status      TEXT NOT NULL DEFAULT 'pending',
            rca_started_at  TIMESTAMPTZ,
            rca_completed_at TIMESTAMPTZ,
            rca_result      JSONB,
            rca_error       TEXT
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS service_repo_map (
            service_name    TEXT PRIMARY KEY,
            github_org      TEXT NOT NULL,
            github_repo     TEXT NOT NULL,
            default_branch  TEXT NOT NULL DEFAULT 'main',
            language        TEXT,
            onboarded_at    TIMESTAMPTZ DEFAULT NOW(),
            onboarded_by    TEXT,
            notes           TEXT
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS service_context_cache (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            service_name    TEXT NOT NULL,
            cache_key       TEXT NOT NULL,
            content         JSONB NOT NULL,
            commit_sha      TEXT,
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            last_used_at    TIMESTAMPTZ DEFAULT NOW(),
            invalidated_at  TIMESTAMPTZ,
            UNIQUE (service_name, cache_key)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS rca_reports (
            rca_id          TEXT PRIMARY KEY,
            error_log_id    UUID REFERENCES error_logs(id),
            service_name    TEXT NOT NULL,
            generated_at    TEXT NOT NULL,
            report          JSONB NOT NULL,
            created_at      TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_service ON error_logs(service_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_occurred ON error_logs(occurred_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_error_logs_status ON error_logs(rca_status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cache_service ON service_context_cache(service_name)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rca_reports")
    op.execute("DROP TABLE IF EXISTS service_context_cache")
    op.execute("DROP TABLE IF EXISTS service_repo_map")
    op.execute("DROP TABLE IF EXISTS error_logs")
