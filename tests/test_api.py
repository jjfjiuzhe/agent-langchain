from fastapi.testclient import TestClient

from app.main import app
from app.services.task_service import TaskService
from app.services.workflow_service import WorkflowService
from tests.test_services import FakeTaskRepository


def test_health_check() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_task(monkeypatch) -> None:
    import app.main as main

    monkeypatch.setattr(main, "workflow_service", WorkflowService(task_service=TaskService(repository=FakeTaskRepository())))
    client = TestClient(app)
    response = client.post("/analyze", json={"requirement": "你好"})

    assert response.status_code == 200
    body = response.json()
    assert body["route"]["task_type"]
    assert body["analysis"]["summary"]
    assert body["plan"]["steps"]
    assert body["review"]["passed"] is True


def test_task_lifecycle_is_recorded(monkeypatch) -> None:
    import app.main as main

    monkeypatch.setattr(main, "workflow_service", WorkflowService(task_service=TaskService(repository=FakeTaskRepository())))
    client = TestClient(app)
    client.post("/analyze", json={"requirement": "你好"})

    response = client.get("/tasks")

    assert response.status_code == 200
    tasks = response.json()
    assert tasks
    assert tasks[-1]["status"] == "completed"
    assert tasks[-1]["result"]["review"]["passed"] is True


def test_get_missing_task_returns_404(monkeypatch) -> None:
    import app.main as main

    monkeypatch.setattr(main, "workflow_service", WorkflowService(task_service=TaskService(repository=FakeTaskRepository())))
    client = TestClient(app)
    response = client.get("/tasks/missing")

    assert response.status_code == 404
