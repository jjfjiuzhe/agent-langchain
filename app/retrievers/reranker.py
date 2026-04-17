import re
from collections import Counter

from app.schemas.response import RetrievedItem

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


class KeywordReranker:
    """Lightweight reranker that boosts vector results by lexical overlap."""

    def rerank(self, query: str, items: list[RetrievedItem], limit: int) -> list[RetrievedItem]:
        query_terms = Counter(_tokenize(query))
        if not query_terms:
            return sorted(items, key=lambda item: item.score, reverse=True)[:limit]

        reranked: list[RetrievedItem] = []
        for item in items:
            content_terms = Counter(_tokenize(f"{item.title} {item.content}"))
            overlap = sum(min(query_terms[term], content_terms[term]) for term in query_terms)
            lexical_score = overlap / max(1, sum(query_terms.values()))
            combined_score = min(1.0, (item.score * 0.8) + (lexical_score * 0.2))
            reranked.append(
                RetrievedItem(
                    source=item.source,
                    title=item.title,
                    content=item.content,
                    score=combined_score,
                    metadata={**item.metadata, "vector_score": item.score, "rerank_score": lexical_score},
                )
            )
        return sorted(reranked, key=lambda item: item.score, reverse=True)[:limit]


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]
