# rca-agent

AI-powered Root Cause Analysis agent using Claude (Anthropic) + GitHub + PostgreSQL.

## Quick Start

```bash
# 1. Start PostgreSQL
docker run -d --name rca-pg \
  -e POSTGRES_DB=rca_agent \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 postgres:16-alpine

# 2. Configure
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and GITHUB_PAT

# 3. Install
pip install -e ".[test]"

# 4. Migrate
alembic upgrade head

# 5. Run
uvicorn app.main:app --reload
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /error-logs | Submit a new error log |
| POST | /rca/run | Trigger RCA for an error log |
| GET | /rca/{id} | Poll RCA status/result |
| POST | /onboard | Register a service ↔ GitHub repo mapping |
| GET | /services | List onboarded services |

## Architecture

```
FastAPI → RCAAgent → ReAct Loop (Claude)
                        ↓ tools
              GitHub API  │  CICD Adapter  │  Cache (PostgreSQL)
```

## Adapters

- **Observability**: `local` (PostgreSQL) or `datadog` (stub — implement with your API key)
- **CI/CD**: `mock` (hardcoded fixtures for demo) or `real` (implement with your CI/CD API)

## Running Evals

```bash
pytest evals/ -v
```

Requires mocked GitHub responses (see `evals/github_mocks.py`).
