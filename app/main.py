from fastapi import FastAPI, HTTPException

from app.schemas.request import IngestRequest, TaskRequest
from app.schemas.response import TaskAnalysisResponse, TaskRecord
from app.services.ingest_service import IngestService
from app.services.workflow_service import WorkflowService

app = FastAPI(title="Agent Retrieval API")
workflow_service = WorkflowService()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest")
def ingest_sources(request: IngestRequest) -> dict[str, int]:
    return IngestService().ingest_all(docs_path=request.docs_path, code_path=request.code_path)


@app.post("/analyze", response_model=TaskAnalysisResponse)
def analyze_task(request: TaskRequest) -> TaskAnalysisResponse:
    return workflow_service.analyze(request)


@app.get("/tasks", response_model=list[TaskRecord])
def list_tasks() -> list[TaskRecord]:
    return workflow_service.list_tasks()


@app.get("/tasks/{task_id}", response_model=TaskRecord)
def get_task(task_id: str) -> TaskRecord:
    task = workflow_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
