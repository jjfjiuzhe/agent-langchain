from pathlib import Path

from app.config import settings
from app.schemas.response import RetrievedItem
from app.stores.pgvector_store import PGVectorStore
from app.tools.code_tools import extract_python_symbol_chunks, list_code_files, read_code_file
from app.tools.doc_tools import load_markdown_chunks, read_text_file, split_text

_DOC_EXTENSIONS = {".md", ".markdown", ".txt"}


class IngestService:
    """Builds document/code chunks and upserts them into PGVector."""

    def __init__(self, store: PGVectorStore | None = None) -> None:
        self.store = store or PGVectorStore()

    def ingest_documents(self, docs_path: str | Path | None = None) -> int:
        root = Path(docs_path) if docs_path else settings.resolve_docs_path()
        if not root.exists():
            return 0
        items: list[RetrievedItem] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in _DOC_EXTENSIONS:
                continue
            chunks = self._document_chunks(path)
            for index, chunk in enumerate(chunks):
                items.append(
                    RetrievedItem(
                        source="docs",
                        title=f"{path.name}#{index}",
                        content=chunk,
                        score=1.0,
                        metadata={
                            "kind": "document",
                            "path": str(path),
                            "filename": path.name,
                            "chunk_index": index,
                            "extension": path.suffix.lower(),
                        },
                    )
                )
        return self.store.upsert_documents(items)

    def ingest_code(self, code_path: str | Path | None = None) -> int:
        root = Path(code_path) if code_path else settings.resolve_code_index_path()
        if not root.exists():
            return 0
        items: list[RetrievedItem] = []
        for path in list_code_files(root):
            chunks = self._code_chunks(path)
            for index, chunk in enumerate(chunks):
                metadata = {
                    "kind": "code",
                    "path": str(path),
                    "filename": path.name,
                    "chunk_index": index,
                    "extension": path.suffix.lower(),
                    **chunk.get("metadata", {}),
                }
                items.append(
                    RetrievedItem(
                        source="code",
                        title=str(chunk["title"]),
                        content=str(chunk["content"]),
                        score=1.0,
                        metadata=metadata,
                    )
                )
        return self.store.upsert_code_chunks(items)

    def ingest_all(self, docs_path: str | Path | None = None, code_path: str | Path | None = None) -> dict[str, int]:
        return {
            "documents": self.ingest_documents(docs_path),
            "code": self.ingest_code(code_path),
        }

    def _document_chunks(self, path: Path) -> list[str]:
        if path.suffix.lower() in {".md", ".markdown"}:
            return load_markdown_chunks(path, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
        return split_text(read_text_file(path), chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)

    def _code_chunks(self, path: Path) -> list[dict[str, object]]:
        source = read_code_file(path)
        if path.suffix.lower() == ".py":
            symbol_chunks = extract_python_symbol_chunks(source)
            if symbol_chunks:
                return [
                    {
                        "title": f"{path.name}:{chunk['name']}",
                        "content": chunk["content"],
                        "metadata": {
                            "symbol_name": chunk["name"],
                            "symbol_type": chunk["type"],
                            "lineno": chunk["lineno"],
                            "end_lineno": chunk["end_lineno"],
                        },
                    }
                    for chunk in symbol_chunks
                ]
        return [
            {
                "title": f"{path.name}#{index}",
                "content": chunk,
                "metadata": {},
            }
            for index, chunk in enumerate(split_text(source, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap))
        ]
