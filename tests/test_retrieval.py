from app.schemas.response import RetrievedItem
from app.services.retrieval_service import RetrievalService


class FakeHybridRetriever:
    def retrieve(self, query, limit=5, metadata_filter=None, score_threshold=None, rerank=True):
        return [
            RetrievedItem(source="docs", title="doc", content="登录审计文档", score=0.9, metadata={}),
            RetrievedItem(source="code", title="code", content="登录审计代码", score=0.8, metadata={}),
        ][:limit]


def test_retrieval_service_returns_document_and_code_items() -> None:
    results = RetrievalService(retriever=FakeHybridRetriever()).search_related_context("登录审计")

    assert len(results) == 2
    assert {item.source for item in results} == {"docs", "code"}
    assert results[0].score >= results[1].score
