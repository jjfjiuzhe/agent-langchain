from pathlib import Path
import re


_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_MARKDOWN_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)


def read_text_file(path: str | Path, encoding: str = "utf-8") -> str:
    """Reads a text document from disk."""
    return Path(path).read_text(encoding=encoding)


def normalize_markdown(markdown: str) -> str:
    """Converts common Markdown markup into cleaner searchable text."""
    without_code = _MARKDOWN_CODE_FENCE_RE.sub(" ", markdown)
    without_links = _MARKDOWN_LINK_RE.sub(r"\1", without_code)
    without_headings = _MARKDOWN_HEADING_RE.sub("", without_links)
    return normalize_whitespace(without_headings)


def split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 120) -> list[str]:
    """Splits text into overlapping chunks suitable for embedding."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    normalized = normalize_whitespace(text)
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = end - chunk_overlap
    return chunks


def load_markdown_chunks(path: str | Path, chunk_size: int = 1000, chunk_overlap: int = 120) -> list[str]:
    """Reads, normalizes, and chunks a Markdown document."""
    return split_text(normalize_markdown(read_text_file(path)), chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())
