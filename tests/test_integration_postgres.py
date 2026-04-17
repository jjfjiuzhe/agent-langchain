import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.schemas.request import TaskRequest
from app.schemas.response import RetrievedItem, TaskStatus
from app.services.embedding_service import EmbeddingService
from app.services.ingest_service import IngestService
from app.services.task_service import TaskService
from app.services.workflow_service import WorkflowService
from app.stores.pgvector_store import PGVectorStore
from app.stores.task_repository import TaskRepository

pytestmark = pytest.mark.skipif(not settings.test_database_url, reason="AGENT_TEST_DATABASE_URL is not configured")


def _names() -> tuple[str, str, str]:
    suffix = uuid.uuid4().hex[:10]
    return f"test_vectors_{suffix}", f"test_tasks_{suffix}", f"test_collection_{suffix}"


def _drop_table(database_url: str, table: str) -> None:
    with psycopg.connect(database_url) as conn:
        conn.execute(f'DROP TABLE IF EXISTS "{table}"')


def test_pgvector_upsert_and_similarity_search() -> None:
    database_url = settings.test_database_url
    vector_table, _, collection = _names()
    try:
        store = PGVectorStore(
            database_url=database_url,
            table_name=vector_table,
            collection=collection,
            embedding_service=EmbeddingService(dimension=16),
            embedding_dimension=16,
        )
        inserted = store.upsert_documents(
            [
                RetrievedItem(
                    source="docs",
                    title="login-audit.md",
                    content="登录审计需要记录用户登录成功失败和 IP 地址",
                    score=1.0,
                    metadata={"domain": "auth", "kind": "document"},
                )
            ]
        )
        results = store.search_documents("登录审计 IP", limit=3, metadata_filter={"domain": "auth"}, score_threshold=0.0)

        assert inserted == 1
        assert results
        assert results[0].metadata["domain"] == "auth"
    finally:
        _drop_table(database_url, vector_table)


def test_ingest_pipeline_indexes_documents_and_code(tmp_path) -> None:
    database_url = settings.test_database_url
    vector_table, _, collection = _names()
    docs_dir = tmp_path / "docs"
    code_dir = tmp_path / "code"
    docs_dir.mkdir()
    code_dir.mkdir()
    (docs_dir / "login.md").write_text("# 登录审计\n记录登录成功、失败和风险原因。", encoding="utf-8")
    (code_dir / "audit.py").write_text("def create_audit_log():\n    return 'ok'\n", encoding="utf-8")

    try:
        store = PGVectorStore(
            database_url=database_url,
            table_name=vector_table,
            collection=collection,
            embedding_service=EmbeddingService(dimension=16),
            embedding_dimension=16,
        )
        counts = IngestService(store=store).ingest_all(docs_path=docs_dir, code_path=code_dir)
        results = store.search("登录审计", limit=5)

        assert counts["documents"] == 1
        assert counts["code"] == 1
        assert {item.source for item in results} == {"docs", "code"}
    finally:
        _drop_table(database_url, vector_table)


def test_task_repository_persists_task_records() -> None:
    database_url = settings.test_database_url
    _, task_table, _ = _names()
    try:
        repository = TaskRepository(database_url=database_url, table_name=task_table)
        service = TaskService(repository=repository)
        task = service.create_task(TaskRequest(requirement="分析登录审计"))
        service.mark_running(task.task_id)
        service.mark_failed(task.task_id, "boom")

        loaded = repository.get(task.task_id)
        assert loaded is not None
        assert loaded.status == TaskStatus.failed
        assert loaded.error == "boom"
        assert repository.list()
    finally:
        _drop_table(database_url, task_table)


def test_complete_api_flow_with_postgres_and_pgvector(tmp_path, monkeypatch) -> None:
    database_url = settings.test_database_url
    vector_table, task_table, collection = _names()
    docs_dir = tmp_path / "docs"
    code_dir = tmp_path / "code"
    docs_dir.mkdir()
    code_dir.mkdir()
    (docs_dir / "login.md").write_text("# 登录审计\n登录审计影响认证模块和安全日志。", encoding="utf-8")
    (code_dir / "audit.py").write_text("def create_audit_log(user_id: str):\n    return user_id\n", encoding="utf-8")

    monkeypatch.setattr(settings, "database_url", database_url)
    monkeypatch.setattr(settings, "pgvector_table", vector_table)
    monkeypatch.setattr(settings, "pgvector_collection", collection)
    monkeypatch.setattr(settings, "task_table", task_table)
    monkeypatch.setattr(settings, "embedding_dimension", 16)

    try:
        import app.main as main

        main.workflow_service = WorkflowService(
            task_service=TaskService(repository=TaskRepository(database_url=database_url, table_name=task_table))
        )
        client = TestClient(main.app)

        ingest_response = client.post("/ingest", json={"docs_path": str(docs_dir), "code_path": str(code_dir)})
        analyze_response = client.post("/analyze", json={"requirement": "分析登录审计影响范围和实施方案"})
        tasks_response = client.get("/tasks")

        assert ingest_response.status_code == 200
        assert ingest_response.json() == {"documents": 1, "code": 1}
        assert analyze_response.status_code == 200
        assert analyze_response.json()["retrieved_items"]
        assert tasks_response.status_code == 200
        assert tasks_response.json()[-1]["status"] == "completed"
    finally:
        _drop_table(database_url, vector_table)
        _drop_table(database_url, task_table)
