from typing import Any

from app.config import settings
from app.retrievers.code_retriever import CodeRetriever
from app.retrievers.doc_retriever import DocRetriever
from app.retrievers.reranker import KeywordReranker
from app.schemas.response import RetrievedItem


class HybridRetriever:
    """Combines document and code retrieval results for downstream analysis."""

    def __init__(
        self,
        doc_retriever: DocRetriever | None = None,
        code_retriever: CodeRetriever | None = None,
        reranker: KeywordReranker | None = None,
    ) -> None:
        self.doc_retriever = doc_retriever or DocRetriever()
        self.code_retriever = code_retriever or CodeRetriever()
        self.reranker = reranker or KeywordReranker()

    def retrieve(
        self,
        query: str,
        limit: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float | None = None,
        rerank: bool = True,
    ) -> list[RetrievedItem]:
        top_k = limit or settings.retrieval_top_k
        threshold = settings.retrieval_score_threshold if score_threshold is None else score_threshold
        recall_limit = max(top_k * 2, top_k)
        doc_limit = max(1, recall_limit // 2)
        code_limit = max(1, recall_limit - doc_limit)
        results = [
            *self.doc_retriever.retrieve(query, limit=doc_limit, metadata_filter=metadata_filter, score_threshold=threshold),
            *self.code_retriever.retrieve(query, limit=code_limit, metadata_filter=metadata_filter, score_threshold=threshold),
        ]
        deduped = self._dedupe(results)
        sorted_results = sorted(deduped, key=lambda item: item.score, reverse=True)
        if rerank:
            return self.reranker.rerank(query, sorted_results, top_k)
        return sorted_results[:top_k]

    def _dedupe(self, items: list[RetrievedItem]) -> list[RetrievedItem]:
        best_by_key: dict[tuple[str, str, str], RetrievedItem] = {}
        for item in items:
            key = (item.source, item.title, item.content)
            existing = best_by_key.get(key)
            if existing is None or item.score > existing.score:
                best_by_key[key] = item
        return list(best_by_key.values())
