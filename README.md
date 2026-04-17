# Agent LangChain

面向研发任务分析场景的多 Agent 协同系统。项目基于 LangChain、LangGraph 和 FastAPI，接收研发需求后完成任务分类、文档与代码检索、影响范围分析、实施方案生成和结果审查。

## 主要功能

- 多 Agent 协作：包含 Router、Retrieval、Analysis、Planning、Review 五类 Agent。
- 有状态工作流：基于 LangGraph 编排任务流，支持条件路由和 Review 不通过后的方案修订回环。
- 文档与代码双检索：支持文档检索、代码检索和混合检索，结合 metadata filter、top-k、score threshold、去重和轻量 rerank。
- 向量存储：基于 PostgreSQL + PGVector 写入 embedding，并执行相似度检索。
- 数据入库：支持扫描文档和代码，完成切块、embedding、upsert 到 PGVector。
- 结构化输出：使用 Pydantic 定义请求、响应、分析结果、方案和审查结果。
- API 服务：基于 FastAPI 提供数据入库、任务分析和任务状态查询接口。
- OpenAI 兼容转接口：通过 `AGENT_OPENAI_BASE_URL` 配置模型代理地址。

## 技术栈

- Python
- FastAPI
- LangChain
- LangGraph
- PostgreSQL
- PGVector
- Pydantic

## API

- `GET /health`：健康检查
- `POST /ingest`：将文档和代码写入 PGVector
- `POST /analyze`：提交研发需求并返回分析结果
- `GET /tasks`：查询任务记录
- `GET /tasks/{task_id}`：查询单个任务状态

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

示例请求：

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d "{\"requirement\": \"分析新增登录审计功能的影响范围和实施方案\"}"
```

## 配置

常用环境变量见 [.env.example](.env.example)。核心配置包括：

- `AGENT_DATABASE_URL`：PostgreSQL 数据库连接
- `AGENT_OPENAI_BASE_URL`：OpenAI 兼容转接口地址
- `AGENT_OPENAI_API_KEY`：模型 API Key
- `AGENT_LLM_MODEL_NAME`：LLM 模型名称
- `AGENT_EMBEDDING_MODEL_NAME`：Embedding 模型名称

## 测试

运行单元测试：

```bash
python -m pytest
```

运行 PostgreSQL + PGVector 集成测试：

```bash
AGENT_TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agent_test python -m pytest tests/test_integration_postgres.py
```
