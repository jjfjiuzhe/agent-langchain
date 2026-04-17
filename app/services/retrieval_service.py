from typing import Any

from app.config import settings
from app.retrievers.hybrid_retriever import HybridRetriever
from app.schemas.response import RetrievedItem


class RetrievalService:
    """Service layer for document and code retrieval."""

    def __init__(self, retriever: HybridRetriever | None = None) -> None:
        self.retriever = retriever or HybridRetriever()

    def search_related_context(
        self,
        query: str,
        limit: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float | None = None,
        rerank: bool = True,
    ) -> list[RetrievedItem]:
        return self.retriever.retrieve(
            query,
            limit=limit or settings.retrieval_top_k,
            metadata_filter=metadata_filter,
            score_threshold=score_threshold,
            rerank=rerank,
        )
