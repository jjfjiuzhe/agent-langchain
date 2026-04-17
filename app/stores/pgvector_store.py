import hashlib
from collections.abc import Iterable
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import settings
from app.schemas.response import RetrievedItem
from app.services.embedding_service import EmbeddingService


class PGVectorStore:
    """PostgreSQL + PGVector-backed vector store for docs and code chunks."""

    def __init__(
        self,
        database_url: str | None = None,
        table_name: str | None = None,
        collection: str | None = None,
        embedding_service: EmbeddingService | None = None,
        embedding_dimension: int | None = None,
        auto_setup: bool = True,
    ) -> None:
        self.database_url = database_url or settings.database_url
        self.table_name = table_name or settings.pgvector_table
        self.collection = collection or settings.pgvector_collection
        self.embedding_service = embedding_service or EmbeddingService(dimension=embedding_dimension)
        self.embedding_dimension = embedding_dimension or self.embedding_service.dimension
        if auto_setup:
            self.setup()

    def setup(self) -> None:
        with self._connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {table} (
                        id TEXT PRIMARY KEY,
                        collection TEXT NOT NULL,
                        item_type TEXT NOT NULL,
                        source TEXT NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({dimension}) NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                ).format(table=sql.Identifier(self.table_name), dimension=sql.Literal(self.embedding_dimension))
            )
            conn.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {idx} ON {table} USING ivfflat (embedding vector_cosine_ops)").format(
                    idx=sql.Identifier(f"{self.table_name}_embedding_idx"),
                    table=sql.Identifier(self.table_name),
                )
            )
            conn.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {idx} ON {table} USING gin (metadata)").format(
                    idx=sql.Identifier(f"{self.table_name}_metadata_idx"),
                    table=sql.Identifier(self.table_name),
                )
            )
            conn.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {idx} ON {table} (collection, item_type)").format(
                    idx=sql.Identifier(f"{self.table_name}_collection_type_idx"),
                    table=sql.Identifier(self.table_name),
                )
            )

    def search_documents(
        self,
        query: str,
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[RetrievedItem]:
        return self.search(
            query=query,
            item_type="document",
            limit=limit,
            metadata_filter=metadata_filter,
            score_threshold=score_threshold,
        )

    def search_code(
        self,
        query: str,
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[RetrievedItem]:
        return self.search(
            query=query,
            item_type="code",
            limit=limit,
            metadata_filter=metadata_filter,
            score_threshold=score_threshold,
        )

    def search(
        self,
        query: str,
        item_type: str | None = None,
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
        score_threshold: float = 0.0,
    ) -> list[RetrievedItem]:
        query_embedding = self.embedding_service.embed_query(query)
        vector = self._to_vector_literal(query_embedding)
        filters = [sql.SQL("collection = %s")]
        params: list[Any] = [self.collection]
        if item_type:
            filters.append(sql.SQL("item_type = %s"))
            params.append(item_type)
        if metadata_filter:
            filters.append(sql.SQL("metadata @> %s"))
            params.append(Jsonb(metadata_filter))

        where_clause = sql.SQL(" AND ").join(filters)
        query_sql = sql.SQL(
            """
            SELECT source, title, content, metadata,
                   GREATEST(0, 1 - (embedding <=> %s::vector)) AS score
            FROM {table}
            WHERE {where_clause}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """
        ).format(table=sql.Identifier(self.table_name), where_clause=where_clause)

        with self._connect(row_factory=dict_row) as conn:
            rows = conn.execute(query_sql, [vector, *params, vector, limit]).fetchall()

        results = [self._row_to_item(row) for row in rows]
        return [item for item in results if item.score >= score_threshold]

    def upsert_documents(self, items: list[RetrievedItem]) -> int:
        return self.upsert_items(items, item_type="document")

    def upsert_code_chunks(self, items: list[RetrievedItem]) -> int:
        return self.upsert_items(items, item_type="code")

    def upsert_items(self, items: Iterable[RetrievedItem], item_type: str) -> int:
        item_list = list(items)
        if not item_list:
            return 0
        embeddings = self.embedding_service.embed_documents([item.content for item in item_list])
        rows = []
        for item, embedding in zip(item_list, embeddings, strict=True):
            metadata = {**item.metadata, "kind": item.metadata.get("kind", item_type)}
            rows.append(
                (
                    self._item_id(item, item_type),
                    self.collection,
                    item_type,
                    item.source,
                    item.title,
                    item.content,
                    Jsonb(metadata),
                    self._to_vector_literal(embedding),
                )
            )

        insert_sql = sql.SQL(
            """
            INSERT INTO {table} (id, collection, item_type, source, title, content, metadata, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
            ON CONFLICT (id) DO UPDATE SET
                collection = EXCLUDED.collection,
                item_type = EXCLUDED.item_type,
                source = EXCLUDED.source,
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                metadata = EXCLUDED.metadata,
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
            """
        ).format(table=sql.Identifier(self.table_name))

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(insert_sql, rows)
        return len(rows)

    def delete_collection(self) -> int:
        with self._connect() as conn:
            result = conn.execute(
                sql.SQL("DELETE FROM {table} WHERE collection = %s").format(table=sql.Identifier(self.table_name)),
                [self.collection],
            )
            return result.rowcount or 0

    def _connect(self, **kwargs):
        return psycopg.connect(self.database_url, **kwargs)

    def _row_to_item(self, row: dict[str, Any]) -> RetrievedItem:
        return RetrievedItem(
            source=row["source"],
            title=row["title"],
            content=row["content"],
            score=float(row["score"]),
            metadata=dict(row["metadata"] or {}),
        )

    def _item_id(self, item: RetrievedItem, item_type: str) -> str:
        raw = f"{self.collection}:{item_type}:{item.source}:{item.title}:{item.content}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _to_vector_literal(self, embedding: list[float]) -> str:
        if len(embedding) != self.embedding_dimension:
            raise ValueError(f"Expected embedding dimension {self.embedding_dimension}, got {len(embedding)}")
        return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"
