"""
Error Ingestion Agent — Log Parser
Extracts structured fields from raw Java/Spring log lines.

Handles formats:
  - Standard Spring Boot: "2024-01-15 10:30:01.123  ERROR 12345 --- [main] c.d.b.service.AccountService : <message>"
  - Simple:               "2024-01-15 10:30:01 ERROR ServiceName - <message>"
  - Multi-line with stack trace (lines starting with \tat or exception class)
"""
import re
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Matches standard Spring Boot log prefix
_SPRING_LOG_RE = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)"
    r"\s+(?P<severity>TRACE|DEBUG|INFO|WARN|ERROR|FATAL)"
    r"(?:\s+\d+\s+---\s+\[.*?\]\s+[\w.$]+\s+:\s+)?"
    r"\s*(?P<message>.+)"
)

# Matches simple log format: "TIMESTAMP LEVEL ServiceName - message"
_SIMPLE_LOG_RE = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"
    r"\s+(?P<severity>TRACE|DEBUG|INFO|WARN|ERROR|FATAL)"
    r"\s+\S+"
    r"\s+-\s+(?P<message>.+)"
)

# Exception class name on its own line (e.g. "java.lang.NullPointerException: msg")
_EXCEPTION_LINE_RE = re.compile(
    r"^(?P<exception>(?:[\w$]+\.)+[\w$]*Exception(?:Error)?)"
    r"(?::\s*(?P<exc_msg>.+))?$"
)

# Stack frame line
_STACK_FRAME_RE = re.compile(r"^\s+at\s+[\w.$]+\(")

# Common Java exception short names
_EXCEPTION_SHORT_RE = re.compile(
    r"(?:^|[\s:])("
    r"NullPointerException|IllegalArgumentException|IllegalStateException|"
    r"RuntimeException|IndexOutOfBoundsException|ClassCastException|"
    r"UnsupportedOperationException|ArithmeticException|NumberFormatException|"
    r"TimeoutException|IOException|SQLException|"
    r"InsufficientFundsException|AccountNotFoundException|ChaosException|"
    r"HikariPool\$PoolInitializationException"
    r")"
)


@dataclass
class ParsedLogEntry:
    timestamp: Optional[datetime]
    severity: str
    message: str
    error_type: Optional[str]
    stack_trace: Optional[str]
    raw_log: str


def parse_log_entry(raw_log: str) -> ParsedLogEntry:
    """
    Parse a raw log entry (potentially multi-line) into a ParsedLogEntry.

    The raw_log may be a single line or multiple lines representing one log event
    (e.g. exception header + stack frames).

    Returns:
        ParsedLogEntry with all fields populated where detectable.
    """
    lines = raw_log.strip().splitlines()
    if not lines:
        return ParsedLogEntry(
            timestamp=None, severity="ERROR", message=raw_log,
            error_type=None, stack_trace=None, raw_log=raw_log,
        )

    first_line = lines[0]

    # --- Parse timestamp + severity + message from first line ---
    timestamp = None
    severity = "ERROR"
    message = first_line.strip()

    for pattern in (_SPRING_LOG_RE, _SIMPLE_LOG_RE):
        m = pattern.match(first_line)
        if m:
            ts_str = m.group("timestamp")
            severity = m.group("severity")
            message = m.group("message").strip()
            try:
                ts_str = ts_str.replace("T", " ")
                timestamp = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
            break

    # --- Extract error_type from message or subsequent lines ---
    error_type = _extract_error_type(message, lines)

    # --- Extract stack trace ---
    stack_trace = _extract_stack_trace(lines)

    return ParsedLogEntry(
        timestamp=timestamp,
        severity=severity,
        message=message,
        error_type=error_type,
        stack_trace=stack_trace,
        raw_log=raw_log,
    )


def _extract_error_type(message: str, lines: list[str]) -> Optional[str]:
    """
    Extract the exception class name from message text or exception header lines.
    Returns the short class name (e.g. 'NullPointerException').
    """
    # Check message text for known exception names
    m = _EXCEPTION_SHORT_RE.search(message)
    if m:
        return m.group(1)

    # Check subsequent lines for a full exception class
    for line in lines[1:]:
        em = _EXCEPTION_LINE_RE.match(line.strip())
        if em:
            full_name = em.group("exception")
            return full_name.split(".")[-1]

    return None


def _extract_stack_trace(lines: list[str]) -> Optional[str]:
    """
    Extract stack trace text from a multi-line log entry.
    Stack trace begins at either:
      (a) a line matching a full Java exception class (e.g. 'java.lang.NullPointerException:')
      (b) the first '\tat ' frame line
    """
    stack_start = None

    for i, line in enumerate(lines[1:], start=1):
        stripped = line.strip()
        # Check for exception class line
        if _EXCEPTION_LINE_RE.match(stripped):
            stack_start = i
            break
        # Check for stack frame
        if _STACK_FRAME_RE.match(line):
            stack_start = i
            break

    if stack_start is None:
        return None

    stack_lines = lines[stack_start:]
    if not stack_lines:
        return None

    return "\n".join(stack_lines).strip()


def is_error_line(raw_log: str) -> bool:
    """Quick check: does this log line indicate an error that should be ingested?"""
    upper = raw_log.upper()
    return " ERROR " in upper or " WARN " in upper or "EXCEPTION" in upper
