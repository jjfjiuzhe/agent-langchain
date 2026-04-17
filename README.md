# LangChain + LangGraph R&D Task Analysis Agent System

本项目是一个基于 FastAPI、LangChain 和 LangGraph 的多 Agent 协同系统。系统接收研发任务需求，结合文档与代码检索，完成需求理解、影响分析、实施方案生成和方案审查。

## Agent Roles

- Router Agent：根据用户输入判断任务类型，并路由到对应处理流程。
- Retrieval Agent：根据需求检索相关文档和代码上下文。
- Analysis Agent：分析检索结果，输出需求分析、影响范围、风险和假设。
- Planning Agent：根据分析结果生成任务实施方案。
- Review Agent：审查方案的完整性和合理性。

## Service Layer

- `embedding_service.py`：生成 query/document/code embeddings；有 OpenAI 配置时使用真实 embedding，否则使用确定性本地向量。
- `ingest_service.py`：扫描文档和代码，切块、embedding，并 upsert 到 PGVector。
- `workflow_service.py`：管理整个工作流，调用多 Agent 执行任务，并整合结果。
- `retrieval_service.py`：负责从数据库或向量库检索相关文档和代码，通过 `HybridRetriever` 合并结果。
- `task_service.py`：管理任务生命周期，记录任务状态、执行事件、结果和错误信息。

## Retrieval Layer

- `doc_retriever.py`：文档检索模块，负责从 PGVector 向量数据库中检索相关文档。
- `code_retriever.py`：代码检索模块，负责检索与需求相关的代码块、函数或模块。
- `hybrid_retriever.py`：结合文档和代码检索结果，支持 metadata filter、top-k、score threshold、去重和 rerank。
- `reranker.py`：轻量关键词 overlap reranker，用于对向量召回结果做二次排序。

## Store Layer

- `pgvector_store.py`：管理 PostgreSQL + PGVector 的向量表、embedding 写入、metadata 过滤和 cosine similarity search。
- `task_repository.py`：管理 PostgreSQL 中的任务记录、状态、执行事件、结果和错误信息。

## Tools Layer

- `doc_tools.py`：文档处理工具，支持读取文档、清洗 Markdown、切分文本块。
- `code_tools.py`：代码处理工具，支持读取代码文件、扫描代码文件、提取 Python 函数和类。

## Configuration

`app/config.py` 使用 Pydantic Settings 管理配置，支持通过 `.env` 或环境变量覆盖。环境变量前缀为 `AGENT_`。

常用配置项：

- `AGENT_ENVIRONMENT`：运行环境，例如 `development` 或 `production`。
- `AGENT_DEBUG`：是否开启调试模式。
- `AGENT_DATABASE_URL`：PostgreSQL 数据库连接。
- `AGENT_TEST_DATABASE_URL`：集成测试使用的 PostgreSQL 数据库连接。
- `AGENT_PGVECTOR_COLLECTION`：PGVector collection 名称。
- `AGENT_PGVECTOR_TABLE`：PGVector 数据表名称。
- `AGENT_TASK_TABLE`：任务持久化表名称。
- `AGENT_OPENAI_BASE_URL`：OpenAI 兼容转接口 base URL，例如 `https://your-proxy.example.com/v1`。
- `AGENT_OPENAI_API_KEY`：转接口 API key。
- `AGENT_LLM_MODEL_NAME`：LLM 模型名称。
- `AGENT_EMBEDDING_MODEL_NAME`：Embedding 模型名称。
- `AGENT_EMBEDDING_DIMENSION`：Embedding 维度。
- `AGENT_DOCS_PATH`：文档目录。
- `AGENT_CODE_INDEX_PATH`：代码索引目录。
- `AGENT_RETRIEVAL_TOP_K`：检索返回数量。
- `AGENT_RETRIEVAL_SCORE_THRESHOLD`：检索分数阈值。
- `AGENT_CHUNK_SIZE`：文本切块大小。
- `AGENT_CHUNK_OVERLAP`：文本切块重叠长度。

## Project Structure

```text
app/
  main.py                  # FastAPI project entrypoint
  config.py                # Environment-aware project configuration
  agents/
    router.py              # Router Agent
    retrieval.py           # Retrieval Agent
    analysis.py            # Analysis Agent
    planning.py            # Planning Agent
    review.py              # Review Agent
    graph.py               # LangGraph workflow with conditional edges
    state.py               # Shared graph state definition
  schemas/
    request.py             # User request and ingest request models
    response.py            # Response, task status, plan, review data models
    task.py                # Compatibility exports for schema models
  services/
    embedding_service.py   # Embedding provider
    ingest_service.py      # Document/code ingest pipeline
    workflow_service.py    # Multi-agent workflow service
    retrieval_service.py   # Document/code retrieval service
    task_service.py        # Task lifecycle service
  retrievers/
    doc_retriever.py       # Document retriever
    code_retriever.py      # Code retriever
    hybrid_retriever.py    # Hybrid retriever combining docs and code
    reranker.py            # Lightweight reranker
    simple.py              # Backward-compatible alias for HybridRetriever
  stores/
    pgvector_store.py      # PGVector store
    task_repository.py     # PostgreSQL task repository
  tools/
    doc_tools.py           # Document processing helpers
    code_tools.py          # Code parsing helpers
tests/
  test_api.py
  test_graph.py
  test_retrieval.py
  test_retrievers.py
  test_services.py
  test_tools.py
  test_integration_postgres.py
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Ingest documents and code into PGVector:

```bash
curl -X POST http://127.0.0.1:8000/ingest \
  -H "Content-Type: application/json" \
  -d "{\"docs_path\": \"docs\", \"code_path\": \"app\"}"
```

Analyze a requirement:

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d "{\"requirement\": \"分析新增登录审计功能的影响范围和实施方案\"}"
```

List task lifecycle records:

```bash
curl http://127.0.0.1:8000/tasks
```

Run unit tests:

```bash
python -m pytest
```

Run PostgreSQL/PGVector integration tests:

```bash
AGENT_TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agent_test python -m pytest tests/test_integration_postgres.py
```

## Current Implementation Notes

- Core agents are structured as LangChain PromptTemplate -> ChatModel -> Pydantic output chains when a compatible chat model is configured.
- `AgentWorkflow` uses LangGraph conditional edges when `langgraph` is installed, and falls back to deterministic sequential execution when it is not available.
- Router conditional routing sends review tasks directly to Review, general tasks to Analysis, and requirement/impact/planning tasks through Retrieval -> Analysis -> Planning -> Review.
- Review conditional routing sends failed reviews back to Planning, with a two-iteration guard to avoid infinite loops.
- If `AGENT_OPENAI_BASE_URL` is configured, LangChain OpenAI clients call that OpenAI-compatible proxy endpoint instead of the default OpenAI endpoint.
- If no `AGENT_OPENAI_API_KEY` or `langchain-openai` package is available, agents use deterministic fallback logic so local development remains runnable.
- `PGVectorStore` creates PGVector tables, writes embedded document/code chunks, supports metadata filters, and performs cosine vector search.
- `IngestService` scans docs and code, chunks content, embeds it, and upserts it into PGVector.
- `HybridRetriever` supports metadata filters, top-k recall, score thresholds, deduplication, and keyword reranking.
- `TaskRepository` persists tasks in PostgreSQL.
- `doc_tools.py` and `code_tools.py` currently use standard-library parsing helpers and can be extended with richer parsers later.


