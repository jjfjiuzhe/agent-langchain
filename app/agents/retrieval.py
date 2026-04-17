from app.schemas.response import RetrievedItem
from app.services.retrieval_service import RetrievalService


class RetrievalAgent:
    """Retrieves related documentation and code context for the requirement."""

    def __init__(self, retrieval_service: RetrievalService | None = None) -> None:
        self.retrieval_service = retrieval_service or RetrievalService()

    def run(self, requirement: str) -> list[RetrievedItem]:
        return self.retrieval_service.search_related_context(requirement)
