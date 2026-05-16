from datetime import datetime
from ...db import execute_one
from ...models import ErrorLogEntry


class LocalDBAdapter:
    def get_error_log(self, error_id: str) -> ErrorLogEntry:
        row = execute_one("SELECT * FROM error_logs WHERE id = %s", (error_id,))
        if not row:
            raise ValueError(f"Error log {error_id} not found")
        return ErrorLogEntry(
            id=str(row["id"]),
            service_name=row["service_name"],
            environment=row["environment"],
            error_type=row["error_type"],
            error_message=row["error_message"],
            stack_trace=row["stack_trace"],
            severity=row["severity"],
            occurred_at=row["occurred_at"],
            request_id=row.get("request_id"),
            metadata=row.get("metadata") or {},
        )

    def get_service_metadata(self, service_name: str) -> dict:
        return {"service_name": service_name}
