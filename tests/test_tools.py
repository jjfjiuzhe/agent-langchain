from pathlib import Path

from app.config import Settings
from app.tools.code_tools import extract_python_symbol_chunks, list_code_files
from app.tools.doc_tools import normalize_markdown, split_markdown_by_headings, split_text


def test_normalize_markdown_removes_common_markup() -> None:
    markdown = "# Title\nSee [docs](https://example.com).\n```python\nprint('hidden')\n```"

    text = normalize_markdown(markdown)

    assert "Title" in text
    assert "docs" in text
    assert "https://example.com" not in text
    assert "hidden" not in text


def test_split_markdown_by_headings_uses_heading_sections() -> None:
    markdown = "# 登录审计\n总览内容\n## 数据库变更\n新增审计表\n## API 变更\n新增查询接口"

    chunks = split_markdown_by_headings(markdown, chunk_size=100, chunk_overlap=10)

    assert chunks == [
        "登录审计 总览内容",
        "登录审计 > 数据库变更 新增审计表",
        "登录审计 > API 变更 新增查询接口",
    ]


def test_split_markdown_by_headings_handles_content_before_first_heading() -> None:
    markdown = "项目简介\n# 需求\n登录审计"

    chunks = split_markdown_by_headings(markdown, chunk_size=100, chunk_overlap=10)

    assert chunks == ["项目简介", "需求 登录审计"]


def test_split_markdown_by_headings_falls_back_for_large_sections() -> None:
    markdown = "# 长章节\nabcdefghij"

    chunks = split_markdown_by_headings(markdown, chunk_size=8, chunk_overlap=1)

    assert len(chunks) > 1
    assert all(chunk.startswith("长章节") for chunk in chunks)


def test_split_text_uses_overlap() -> None:
    chunks = split_text("abcdefghij", chunk_size=4, chunk_overlap=1)

    assert chunks == ["abcd", "defg", "ghij"]


def test_extract_python_symbol_chunks() -> None:
    source = "class Foo:\n    pass\n\ndef bar():\n    return 1\n"

    chunks = extract_python_symbol_chunks(source)

    assert [chunk["name"] for chunk in chunks] == ["Foo", "bar"]
    assert chunks[0]["type"] == "class"
    assert "return 1" in chunks[1]["content"]


def test_list_code_files_filters_extensions() -> None:
    root = Path("test_workspace_tools")
    root.mkdir(exist_ok=True)
    py_file = root / "a.py"
    md_file = root / "b.md"
    py_file.write_text("print('x')", encoding="utf-8")
    md_file.write_text("# docs", encoding="utf-8")

    assert list_code_files(root, extensions={".py"}) == [py_file]


def test_settings_resolves_relative_paths() -> None:
    project_root = Path("project-root-test")
    settings = Settings(project_root=project_root, docs_path=Path("docs"), code_index_path=Path("src"))

    assert settings.resolve_docs_path() == project_root / "docs"
    assert settings.resolve_code_index_path() == project_root / "src"


def test_settings_supports_openai_proxy_base_url() -> None:
    settings = Settings(openai_base_url="https://proxy.example.com/v1")

    assert settings.openai_base_url == "https://proxy.example.com/v1"
