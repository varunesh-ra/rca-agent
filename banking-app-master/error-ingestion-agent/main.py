"""
Error Ingestion Agent — Entry Point (File Watcher / DB Mode)

Watches a log file for new lines containing errors and feeds them
through the LangGraph incident processing pipeline.

Run:
    MODE=db LOG_FILE_PATH=/var/log/banking-app/app.log python main.py
"""
import asyncio
import logging
import os
import sys
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config.settings import settings
from db.database import ensure_table, close_pool
from agents.log_monitor.graph import process_log_entry
from utils.log_parser import is_error_line

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("error-ingestion-agent")


class LogFileHandler(FileSystemEventHandler):
    """Watchdog handler that tails a log file for new error lines."""

    def __init__(self, log_path: str):
        self.log_path = log_path
        self._pos = self._get_file_size()
        self._buffer: list[str] = []
        logger.info("Watching log file: %s (starting at byte %d)", log_path, self._pos)

    def _get_file_size(self) -> int:
        try:
            return os.path.getsize(self.log_path)
        except FileNotFoundError:
            return 0

    def on_modified(self, event):
        if event.src_path != self.log_path:
            return
        self._read_new_lines()

    def _read_new_lines(self):
        try:
            with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._pos)
                new_content = f.read()
                self._pos = f.tell()

            if not new_content:
                return

            for line in new_content.splitlines():
                if line.strip():
                    self._buffer.append(line)
                    # Flush buffer on blank line or if line doesn't look like a stack frame
                    if not line.startswith("\t") and not line.startswith("    at "):
                        if len(self._buffer) > 1:
                            self._flush_buffer()
                        elif is_error_line(line):
                            self._flush_buffer()
                        else:
                            self._buffer.clear()
                else:
                    if self._buffer:
                        self._flush_buffer()

        except Exception as exc:
            logger.error("Error reading log file: %s", exc)

    def _flush_buffer(self):
        if not self._buffer:
            return
        raw_log = "\n".join(self._buffer)
        self._buffer.clear()
        if is_error_line(raw_log):
            asyncio.create_task(self._process(raw_log))

    async def _process(self, raw_log: str):
        logger.info("Processing error log entry (%d chars)", len(raw_log))
        state = await process_log_entry(raw_log, source="db_watcher")
        if state.get("stored"):
            logger.info("✓ Incident #%d stored", state["incident_id"])
        else:
            logger.error("✗ Failed to store incident: %s", state.get("error"))


async def run_file_watcher():
    """Main file watcher loop."""
    await ensure_table()

    log_path = settings.log_file_path
    if not os.path.exists(log_path):
        logger.warning("Log file not found: %s — creating empty file", log_path)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        open(log_path, "w").close()

    handler = LogFileHandler(log_path)
    observer = Observer()
    observer.schedule(handler, path=os.path.dirname(log_path) or ".", recursive=False)
    observer.start()
    logger.info("Error Ingestion Agent started in DB/file-watcher mode")

    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down file watcher...")
        observer.stop()
        observer.join()
        await close_pool()


def main():
    if settings.mode == "db":
        asyncio.run(run_file_watcher())
    elif settings.mode == "datadog":
        import uvicorn
        from datadog_webhook import app
        logger.info("Starting Error Ingestion Agent in Datadog webhook mode on port %d", settings.webhook_port)
        uvicorn.run(app, host="0.0.0.0", port=settings.webhook_port)
    else:
        logger.error("Unknown MODE: %s — must be 'db' or 'datadog'", settings.mode)
        sys.exit(1)


if __name__ == "__main__":
    main()
