from typing import Any

from app.schemas.response import RetrievedItem
from app.stores.pgvector_store import PGVectorStore


class DocRetriever:
    """Retrieves requirement, design, and other documentation chunks."""

    def __init__(self, store: PGVectorStore | None = None) -> None:
        self.store = store or PGVectorStore()

    def retrieve(
        self,
        query: str,
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[RetrievedItem]:
        return self.store.search_documents(
            query,
            limit=limit,
            metadata_filter=metadata_filter,
            score_threshold=score_threshold,
        )
