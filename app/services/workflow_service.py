from app.agents.graph import AgentWorkflow
from app.schemas.request import TaskRequest
from app.schemas.response import TaskAnalysisResponse, TaskRecord
from app.services.task_service import TaskService


class WorkflowService:
    """Coordinates task execution across the multi-agent workflow."""

    def __init__(self, workflow: AgentWorkflow | None = None, task_service: TaskService | None = None) -> None:
        self.workflow = workflow or AgentWorkflow()
        self.task_service = task_service or TaskService()

    def analyze(self, request: TaskRequest) -> TaskAnalysisResponse:
        task = self.submit_task(request)
        return self.run_task(task.task_id, request)

    def submit_task(self, request: TaskRequest) -> TaskRecord:
        return self.task_service.create_task(request)

    def run_task(self, task_id: str, request: TaskRequest) -> TaskAnalysisResponse:
        self.task_service.mark_running(task_id)
        try:
            result = self.workflow.run(request)
        except Exception as exc:
            self.task_service.mark_failed(task_id, str(exc))
            raise
        self.task_service.mark_completed(task_id, result)
        return result

    def get_task(self, task_id: str) -> TaskRecord | None:
        return self.task_service.get_task(task_id)

    def list_tasks(self) -> list[TaskRecord]:
        return self.task_service.list_tasks()
