from app.retrievers.code_retriever import CodeRetriever
from app.retrievers.doc_retriever import DocRetriever
from app.retrievers.hybrid_retriever import HybridRetriever
from app.schemas.response import RetrievedItem


class FakeStore:
    def search_documents(self, query, limit=5, metadata_filter=None, score_threshold=0.0):
        items = [
            RetrievedItem(
                source="docs",
                title="design",
                content="登录审计设计文档",
                score=0.9,
                metadata={"kind": "document", "domain": "auth"},
            )
        ]
        return [item for item in items if item.score >= score_threshold][:limit]

    def search_code(self, query, limit=5, metadata_filter=None, score_threshold=0.0):
        items = [
            RetrievedItem(
                source="code",
                title="audit.py:create_audit_log",
                content="def create_audit_log(): pass",
                score=0.8,
                metadata={"kind": "code", "domain": "auth"},
            ),
            RetrievedItem(
                source="code",
                title="audit.py:create_audit_log",
                content="def create_audit_log(): pass",
                score=0.7,
                metadata={"kind": "code", "domain": "auth"},
            ),
        ]
        return [item for item in items if item.score >= score_threshold][:limit]


def test_doc_retriever_returns_document_items() -> None:
    results = DocRetriever(store=FakeStore()).retrieve("登录审计")

    assert results
    assert all(item.source == "docs" for item in results)


def test_code_retriever_returns_code_items() -> None:
    results = CodeRetriever(store=FakeStore()).retrieve("登录审计")

    assert results
    assert all(item.source == "code" for item in results)


def test_hybrid_retriever_merges_dedupes_and_reranks_results() -> None:
    store = FakeStore()
    results = HybridRetriever(
        doc_retriever=DocRetriever(store=store),
        code_retriever=CodeRetriever(store=store),
    ).retrieve("登录审计", limit=5, metadata_filter={"domain": "auth"}, score_threshold=0.0)

    assert {item.source for item in results} == {"docs", "code"}
    assert len(results) == 2
    assert all("vector_score" in item.metadata for item in results)
