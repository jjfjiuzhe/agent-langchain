from uuid import uuid4

from app.schemas.request import TaskRequest
from app.schemas.response import TaskAnalysisResponse, TaskRecord, TaskStatus
from app.stores.task_repository import TaskRepository


class TaskService:
    """Tracks task lifecycle state and execution events."""

    def __init__(self, repository: TaskRepository | None = None) -> None:
        self.repository = repository or TaskRepository()

    def create_task(self, request: TaskRequest) -> TaskRecord:
        task = TaskRecord(
            task_id=str(uuid4()),
            requirement=request.requirement,
            metadata={"context": request.context},
            events=["Task created."],
        )
        return self.repository.save(task)

    def mark_running(self, task_id: str) -> TaskRecord:
        return self.repository.update_status(task_id, TaskStatus.running, "Task execution started.")

    def mark_completed(self, task_id: str, result: TaskAnalysisResponse) -> TaskRecord:
        return self.repository.update_status(
            task_id,
            TaskStatus.completed,
            "Task execution completed.",
            result=result,
        )

    def mark_failed(self, task_id: str, error: str) -> TaskRecord:
        return self.repository.update_status(
            task_id,
            TaskStatus.failed,
            "Task execution failed.",
            error=error,
        )

    def get_task(self, task_id: str) -> TaskRecord | None:
        return self.repository.get(task_id)

    def list_tasks(self) -> list[TaskRecord]:
        return self.repository.list()
