from app.retrievers.hybrid_retriever import HybridRetriever


class SimpleRetriever(HybridRetriever):
    """Backward-compatible alias for the hybrid retriever.

    New code should use DocRetriever, CodeRetriever, or HybridRetriever directly.
    """
