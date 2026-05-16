import json
import os
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from rca_agent.config import settings
from rca_agent.db import execute, execute_one, json_loads
from rca_agent.adapters.observability.local_db import LocalDBAdapter
from rca_agent.adapters.cicd.mock_adapter import MockCICDAdapter
from rca_agent.agent import RCAAgent
from rca_agent.report_renderer import render_rca_html

app = FastAPI(
    title="rca-agent",
    description="AI-powered Root Cause Analysis API",
    version="0.1.0",
)

obs_adapter = LocalDBAdapter()
cicd_adapter = MockCICDAdapter()
agent = RCAAgent(obs_adapter=obs_adapter, cicd_adapter=cicd_adapter)

# Path to the seeded IDs file (written by demo_seed_data.py)
_SEEDED_IDS_PATH = Path(__file__).parent.parent.parent / "demo-repos" / "seeded_ids.json"
# Also check next to the script itself (for flexibility)
_SEEDED_IDS_ALT = Path(__file__).parent.parent / "seeded_ids.json"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": settings.model,
        "github_org": settings.github_org,
        "observability_adapter": settings.observability_adapter,
        "cicd_adapter": settings.cicd_adapter,
    }


# ── Run RCA ───────────────────────────────────────────────────────────────────

class RunRCARequest(BaseModel):
    error_log_id: str


@app.post("/rca/run")
def run_rca(req: RunRCARequest):
    execute(
        "UPDATE error_logs SET rca_status='in_progress', rca_started_at=NOW() WHERE id=%s",
        (req.error_log_id,),
    )
    try:
        report = agent.run(req.error_log_id)
        execute(
            """UPDATE error_logs
               SET rca_status='completed', rca_completed_at=NOW(), rca_result=%s
               WHERE id=%s""",
            (json.dumps(report.model_dump()), req.error_log_id),
        )
        return report.model_dump()
    except Exception as e:
        execute(
            "UPDATE error_logs SET rca_status='failed', rca_error=%s WHERE id=%s",
            (str(e), req.error_log_id),
        )
        raise HTTPException(status_code=500, detail=str(e))


# ── SSE Streaming RCA ─────────────────────────────────────────────────────────

class StreamRCARequest(BaseModel):
    error_log_id: str


@app.post("/rca/run/stream")
def run_rca_stream(req: StreamRCARequest):
    """
    Run the RCA agent and stream trace events as Server-Sent Events.
    Each event is: data: <json>\\n\\n
    On completion: data: {"type": "done", "report": <full_rca_json>}\\n\\n
    """
    event_queue: queue.Queue = queue.Queue()

    def trace_callback(event: dict) -> None:
        event_queue.put(event)

    def agent_thread():
        try:
            execute(
                "UPDATE error_logs SET rca_status='in_progress', rca_started_at=NOW() WHERE id=%s",
                (req.error_log_id,),
            )
            report = agent.run(req.error_log_id, trace_callback=trace_callback)
            execute(
                """UPDATE error_logs
                   SET rca_status='completed', rca_completed_at=NOW(), rca_result=%s
                   WHERE id=%s""",
                (json.dumps(report.model_dump()), req.error_log_id),
            )
            # Push final done event with full report
            event_queue.put({
                "type": "done",
                "report": report.model_dump(),
                "ts": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as exc:
            execute(
                "UPDATE error_logs SET rca_status='failed', rca_error=%s WHERE id=%s",
                (str(exc), req.error_log_id),
            )
            event_queue.put({
                "type": "error",
                "message": str(exc),
                "ts": datetime.now(timezone.utc).isoformat(),
            })
        finally:
            event_queue.put(None)  # Sentinel to end the stream

    thread = threading.Thread(target=agent_thread, daemon=True)
    thread.start()

    def sse_generator():
        while True:
            try:
                event = event_queue.get(timeout=120)  # 2-minute timeout per event
            except queue.Empty:
                yield "data: {\"type\": \"error\", \"message\": \"Timed out waiting for agent\"}\n\n"
                break
            if event is None:
                break
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── HTML RCA Report ──────────────────────────────────────────────────────────

@app.get("/rca/{error_log_id}/report", response_class=HTMLResponse)
def get_rca_report(error_log_id: str):
    """Return a human-readable HTML RCA report."""
    row = execute_one(
        "SELECT rca_result, rca_status FROM error_logs WHERE id = %s",
        (error_log_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="Error log not found")
    if row["rca_status"] != "completed" or not row["rca_result"]:
        return HTMLResponse(
            content=f"<html><body><h2>RCA {row['rca_status']}</h2><p>No report available yet.</p></body></html>",
            status_code=202,
        )
    # MySQL returns JSON columns as strings — parse before rendering
    report_dict = json_loads(row["rca_result"])
    return HTMLResponse(content=render_rca_html(report_dict))


# ── Demo UI ──────────────────────────────────────────────────────────────────

@app.get("/demo", response_class=HTMLResponse)
def demo_ui():
    """Serve the self-contained demo UI."""
    demo_path = Path(__file__).parent / "demo_ui.html"
    if not demo_path.exists():
        raise HTTPException(status_code=404, detail="demo_ui.html not found")
    return HTMLResponse(content=demo_path.read_text())


@app.get("/demo/scenarios")
def demo_scenarios():
    """Return all pending error log IDs for the demo dropdown."""
    rows = execute(
        """SELECT service_name, id, error_type, occurred_at
           FROM error_logs
           WHERE rca_status IN ('pending', 'failed')
           ORDER BY occurred_at DESC
           LIMIT 50"""
    )
    # Build label -> id map; label = "service — ErrorType (date)"
    scenarios = {}
    for row in rows:
        svc = row["service_name"]
        err = row.get("error_type") or "UnknownError"
        ts = str(row["occurred_at"])[:16]  # "2026-05-16 15:04"
        label = f"{svc} — {err} ({ts})"
        scenarios[label] = str(row["id"])
    return {"scenarios": scenarios}
