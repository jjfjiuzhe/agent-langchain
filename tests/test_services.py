from app.schemas.request import TaskRequest
from app.schemas.response import TaskAnalysisResponse, TaskRecord, TaskStatus
from app.services.task_service import TaskService
from app.services.workflow_service import WorkflowService


class FakeTaskRepository:
    def __init__(self) -> None:
        self.tasks: dict[str, TaskRecord] = {}

    def save(self, task: TaskRecord) -> TaskRecord:
        self.tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> TaskRecord | None:
        return self.tasks.get(task_id)

    def list(self) -> list[TaskRecord]:
        return list(self.tasks.values())

    def update_status(self, task_id: str, status: TaskStatus, event: str, result: TaskAnalysisResponse | None = None, error: str | None = None) -> TaskRecord:
        task = self.tasks[task_id]
        task.status = status
        task.events.append(event)
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        if status == TaskStatus.completed:
            task.error = None
        self.tasks[task_id] = task
        return task


def test_workflow_service_records_completed_task() -> None:
    service = WorkflowService(task_service=TaskService(repository=FakeTaskRepository()))
    response = service.analyze(TaskRequest(requirement="你好"))
    tasks = service.list_tasks()

    assert response.review.passed
    assert len(tasks) == 1
    assert tasks[0].status == TaskStatus.completed
    assert tasks[0].result == response


def test_task_service_uses_repository_for_lifecycle() -> None:
    repository = FakeTaskRepository()
    service = TaskService(repository=repository)
    task = service.create_task(TaskRequest(requirement="分析登录审计"))

    service.mark_running(task.task_id)
    service.mark_failed(task.task_id, "boom")

    saved = repository.get(task.task_id)
    assert saved is not None
    assert saved.status == TaskStatus.failed
    assert saved.error == "boom"

