from pathlib import Path
import re


_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_MARKDOWN_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_MARKDOWN_HEADING_LINE_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
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


def split_markdown_by_headings(markdown: str, chunk_size: int = 1000, chunk_overlap: int = 120) -> list[str]:
    """Splits Markdown into semantic chunks using headings as boundaries.

    Each chunk contains the heading path plus the content under that heading. If a
    heading section is still too large, it falls back to overlapping length-based
    chunks while keeping the heading context in each chunk.
    """
    sections = _markdown_sections(markdown)
    chunks: list[str] = []
    for heading_path, body in sections:
        heading_context = " > ".join(heading_path)
        cleaned_body = normalize_markdown("`n".join(body))
        section_text = normalize_whitespace(f"{heading_context} {cleaned_body}" if heading_context else cleaned_body)
        if not section_text:
            continue
        if len(section_text) <= chunk_size:
            chunks.append(section_text)
            continue
        prefix = f"{heading_context} " if heading_context else ""
        body_chunks = split_text(cleaned_body, chunk_size=max(1, chunk_size - len(prefix)), chunk_overlap=chunk_overlap)
        chunks.extend(normalize_whitespace(f"{prefix}{chunk}") for chunk in body_chunks if chunk)
    return chunks


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
    """Reads and chunks a Markdown document by heading sections."""
    return split_markdown_by_headings(read_text_file(path), chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _markdown_sections(markdown: str) -> list[tuple[list[str], str]]:
    lines = markdown.splitlines()
    sections: list[tuple[list[str], list[str]]] = []
    heading_stack: list[tuple[int, str]] = []
    current_body: list[str] = []
    current_path: list[str] = []

    def flush() -> None:
        if current_body or current_path:
            sections.append((current_path.copy(), current_body.copy()))

    for line in lines:
        match = _MARKDOWN_HEADING_LINE_RE.match(line)
        if not match:
            current_body.append(line)
            continue

        flush()
        level = len(match.group(1))
        title = match.group(2).strip()
        heading_stack[:] = [(existing_level, existing_title) for existing_level, existing_title in heading_stack if existing_level < level]
        heading_stack.append((level, title))
        current_path = [heading for _, heading in heading_stack]
        current_body = []

    flush()
    return sections

