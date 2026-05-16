# How to Run Locally

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | ≥ 3.11 | python.org |
| MySQL | 8.0+ | dev.mysql.com or XAMPP/WAMP/Homebrew |
| Git | any | git-scm.com |

You need three API keys:
- `ANTHROPIC_API_KEY` — from console.anthropic.com
- `GITHUB_PAT` — GitHub → Settings → Developer settings → Personal access tokens (needs `repo` scope, read-only)
- `GEMINI_API_KEY` — from aistudio.google.com (free tier works)

---

## Step 1 — Create the MySQL Database

Open MySQL shell (or MySQL Workbench) and run:

```sql
CREATE DATABASE rca_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'rca'@'localhost' IDENTIFIED BY 'rca';
GRANT ALL PRIVILEGES ON rca_db.* TO 'rca'@'localhost';
FLUSH PRIVILEGES;
```

Or use root directly (simpler for local dev):
```sql
CREATE DATABASE rca_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

## Step 2 — Set Up the RCA Agent

```bash
cd banking-app-master/rca-agent

# Copy and fill in environment variables
cp .env.example .env
```

Edit `.env`:
```
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
GITHUB_PAT=ghp_YOUR_TOKEN_HERE
GITHUB_ORG=oscorpAI
DATABASE_URL=mysql+pymysql://root:YOUR_MYSQL_PASSWORD@localhost:3306/rca_db
MODEL=claude-sonnet-4-6
MAX_REACT_ITERATIONS=20
OBSERVABILITY_ADAPTER=local
CICD_ADAPTER=mock
```

Install dependencies and run migrations:

```bash
pip install -e ".[test]"

# Create all tables in rca_db
alembic upgrade head
```

Start the RCA Agent API:

```bash
uvicorn app.main:app --reload --port 8000
```

Verify it's running:
```bash
curl http://localhost:8000/health
# → {"status":"ok","model":"claude-sonnet-4-6",...}
```

---

## Step 3 — Seed Demo Data

```bash
# From banking-app-master/demo-repos/
cd ../demo-repos
python demo_seed_data.py --db-url "mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/rca_db"
```

This will:
- Insert `payment-service` and `order-service` into `service_repo_map`
- Insert 3 realistic error logs into `error_logs`
- Write `seeded_ids.json` for the demo UI

---

## Step 4 — Trigger an RCA

**Option A — Browser (recommended):**
Open http://localhost:8000/demo

**Option B — curl:**
```bash
# Get the seeded error log IDs
cat demo-repos/seeded_ids.json

# Trigger RCA (replace UUID with one from seeded_ids.json)
curl -s -X POST http://localhost:8000/rca/run \
  -H "Content-Type: application/json" \
  -d '{"error_log_id": "PASTE-UUID-HERE"}' | python3 -m json.tool
```

**Option C — Streaming (watch Claude think in real time):**
```bash
curl -N -X POST http://localhost:8000/rca/run/stream \
  -H "Content-Type: application/json" \
  -d '{"error_log_id": "PASTE-UUID-HERE"}'
```

**View the HTML report:**
```
http://localhost:8000/rca/PASTE-UUID-HERE/report
```

---

## Step 5 (Optional) — Run the Error Ingestion Agent

This is only needed if you want to watch a real log file for errors.

```bash
cd banking-app-master/error-ingestion-agent

pip install -r requirements.txt

# Create a .env
echo "DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/rca_db" > .env
echo "GEMINI_API_KEY=YOUR_KEY" >> .env
echo "MODE=db" >> .env
echo "LOG_FILE_PATH=./test.log" >> .env
echo "SERVICE_NAME=my-service" >> .env

python main.py
```

In another terminal, write an error to the log file:
```bash
echo "2026-05-16 12:00:00 ERROR MyService - NullPointerException: order is null" >> test.log
```

The agent will detect it, classify it with Gemini, and insert it into `error_incidents`.

---

## Step 6 (Optional) — Run the Eval Suite

```bash
cd banking-app-master/rca-agent

# Requires ANTHROPIC_API_KEY and GITHUB_PAT in .env
pytest evals/ -v

# Run a single case
pytest evals/ -v -k "payment-service"
```

---

## Troubleshooting

### `pymysql.err.OperationalError: Can't connect to MySQL server`
- MySQL isn't running. Start it: `net start mysql` (Windows) or `brew services start mysql` (Mac)
- Check host/port in DATABASE_URL

### `alembic.util.exc.CommandError: Can't locate revision`
- Run `alembic upgrade head` from inside `banking-app-master/rca-agent/`

### `anthropic.AuthenticationError`
- ANTHROPIC_API_KEY is wrong or missing in `.env`

### `github.GithubException.UnknownObjectException: 404`
- The GitHub repo `oscorpAI/<service>` doesn't exist, or GITHUB_PAT lacks read access
- For the eval suite this is fine — GitHub is mocked via `responses` library

### RCA returns `RuntimeError: RCA agent did not call finish_rca`
- Claude hit MAX_REACT_ITERATIONS (20) without concluding
- Try setting `MAX_REACT_ITERATIONS=30` in `.env`
- Check that GitHub PAT has access to the repo so tool calls succeed

### JSON columns return strings instead of dicts
- This is expected behaviour with PyMySQL — all JSON reads in this codebase
  already call `json_loads()` from `rca_agent.db`. If you add new queries that
  read JSON columns, wrap the result with `json_loads(row["column"])`.

---

## Directory Quick Reference

```
banking-app-master/
├── docker-compose.yml          ← Full stack (MySQL + all services)
├── .env.example                ← Copy to .env, fill API keys
│
├── rca-agent/                  ← Main AI service (FastAPI + Claude)
│   ├── .env.example            ← RCA-agent-specific env vars
│   ├── alembic/                ← Database migrations (run: alembic upgrade head)
│   ├── app/main.py             ← FastAPI routes (port 8000)
│   └── rca_agent/              ← Core agent logic
│       ├── agent.py            ← ReAct loop + tool dispatch
│       ├── config.py           ← Settings (reads .env)
│       ├── db.py               ← PyMySQL sync wrapper
│       ├── cache.py            ← GitHub context cache
│       ├── github_tools.py     ← GitHub API wrappers
│       └── repo_resolver.py    ← Service → GitHub repo mapping
│
├── error-ingestion-agent/      ← Log watcher / Datadog webhook (aiomysql + Gemini)
│   ├── main.py                 ← Entry point (db or datadog mode)
│   └── agents/log_monitor/     ← LangGraph pipeline (parse→analyze→store)
│
└── demo-repos/
    └── demo_seed_data.py       ← Seeds MySQL with error_logs for demo
```
