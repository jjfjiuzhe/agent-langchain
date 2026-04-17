import hashlib
import math
from collections.abc import Sequence
from typing import Any

from app.config import settings


class EmbeddingService:
    """Creates embeddings for documents, code chunks, and queries.

    If langchain-openai and AGENT_OPENAI_API_KEY are available, this service uses
    an OpenAI-compatible embeddings endpoint. Otherwise it falls back to
    deterministic hashing vectors, which keeps tests and local development
    offline-friendly.
    """

    def __init__(self, dimension: int | None = None, embeddings=None) -> None:
        self.dimension = dimension or settings.embedding_dimension
        self.embeddings = embeddings or self._create_embeddings_client()

    def embed_query(self, text: str) -> list[float]:
        if self.embeddings is not None:
            return list(self.embeddings.embed_query(text))
        return self._hash_embedding(text)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if self.embeddings is not None:
            return [list(vector) for vector in self.embeddings.embed_documents(list(texts))]
        return [self._hash_embedding(text) for text in texts]

    def _create_embeddings_client(self):
        if not settings.openai_api_key:
            return None
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError:
            return None

        kwargs: dict[str, Any] = {
            "model": settings.embedding_model_name,
            "api_key": settings.openai_api_key,
            "dimensions": self.dimension,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url

        return OpenAIEmbeddings(**kwargs)

    def _hash_embedding(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = text.lower().split() or [text.lower()]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index, byte in enumerate(digest):
                vector[index % self.dimension] += (byte / 255.0) - 0.5
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
