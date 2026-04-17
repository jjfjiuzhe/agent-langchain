import json
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import settings
from app.schemas.response import TaskAnalysisResponse, TaskRecord, TaskStatus


class TaskRepository:
    """PostgreSQL repository for task lifecycle records."""

    def __init__(self, database_url: str | None = None, table_name: str | None = None, auto_setup: bool = True) -> None:
        self.database_url = database_url or settings.database_url
        self.table_name = table_name or settings.task_table
        self.auto_setup = auto_setup
        self._setup_done = False

    def setup(self) -> None:
        with self._connect() as conn:
            conn.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {table} (
                        task_id TEXT PRIMARY KEY,
                        requirement TEXT NOT NULL,
                        status TEXT NOT NULL,
                        events JSONB NOT NULL DEFAULT '[]'::jsonb,
                        result JSONB,
                        error TEXT,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                ).format(table=sql.Identifier(self.table_name))
            )
            conn.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {idx} ON {table} (status)").format(
                    idx=sql.Identifier(f"{self.table_name}_status_idx"),
                    table=sql.Identifier(self.table_name),
                )
            )
            conn.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {idx} ON {table} USING gin (metadata)").format(
                    idx=sql.Identifier(f"{self.table_name}_metadata_idx"),
                    table=sql.Identifier(self.table_name),
                )
            )
        self._setup_done = True

    def save(self, task: TaskRecord) -> TaskRecord:
        self._ensure_setup()
        task.updated_at = datetime.now(timezone.utc)
        payload = self._task_to_row(task)
        with self._connect() as conn:
            conn.execute(
                sql.SQL(
                    """
                    INSERT INTO {table}
                        (task_id, requirement, status, events, result, error, metadata, created_at, updated_at)
                    VALUES
                        (%(task_id)s, %(requirement)s, %(status)s, %(events)s, %(result)s, %(error)s, %(metadata)s, %(created_at)s, %(updated_at)s)
                    ON CONFLICT (task_id) DO UPDATE SET
                        requirement = EXCLUDED.requirement,
                        status = EXCLUDED.status,
                        events = EXCLUDED.events,
                        result = EXCLUDED.result,
                        error = EXCLUDED.error,
                        metadata = EXCLUDED.metadata,
                        updated_at = EXCLUDED.updated_at
                    """
                ).format(table=sql.Identifier(self.table_name)),
                payload,
            )
        return task

    def get(self, task_id: str) -> TaskRecord | None:
        self._ensure_setup()
        with self._connect(row_factory=dict_row) as conn:
            row = conn.execute(
                sql.SQL("SELECT * FROM {table} WHERE task_id = %s").format(table=sql.Identifier(self.table_name)),
                [task_id],
            ).fetchone()
        return self._row_to_task(row) if row else None

    def list(self) -> list[TaskRecord]:
        self._ensure_setup()
        with self._connect(row_factory=dict_row) as conn:
            rows = conn.execute(
                sql.SQL("SELECT * FROM {table} ORDER BY created_at ASC").format(table=sql.Identifier(self.table_name))
            ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        event: str,
        result: TaskAnalysisResponse | None = None,
        error: str | None = None,
    ) -> TaskRecord:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"Task not found: {task_id}")

        task.status = status
        task.events.append(event)
        task.updated_at = datetime.now(timezone.utc)
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        if status == TaskStatus.completed:
            task.error = None
        return self.save(task)

    def delete_all(self) -> int:
        self._ensure_setup()
        with self._connect() as conn:
            result = conn.execute(sql.SQL("DELETE FROM {table}").format(table=sql.Identifier(self.table_name)))
            return result.rowcount or 0

    def _ensure_setup(self) -> None:
        if self.auto_setup and not self._setup_done:
            self.setup()

    def _connect(self, **kwargs):
        return psycopg.connect(self.database_url, **kwargs)

    def _task_to_row(self, task: TaskRecord) -> dict[str, Any]:
        return {
            "task_id": task.task_id,
            "requirement": task.requirement,
            "status": task.status.value,
            "events": Jsonb(task.events),
            "result": Jsonb(self._model_to_data(task.result)) if task.result else None,
            "error": task.error,
            "metadata": Jsonb(task.metadata),
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

    def _row_to_task(self, row: dict[str, Any]) -> TaskRecord:
        result = row.get("result")
        if result is not None:
            result = TaskAnalysisResponse.model_validate(result) if hasattr(TaskAnalysisResponse, "model_validate") else TaskAnalysisResponse.parse_obj(result)
        return TaskRecord(
            task_id=row["task_id"],
            requirement=row["requirement"],
            status=TaskStatus(row["status"]),
            events=list(row["events"] or []),
            result=result,
            error=row.get("error"),
            metadata=dict(row["metadata"] or {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _model_to_data(self, value: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return json.loads(value.json())
