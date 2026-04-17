import ast
from pathlib import Path


_CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs"}


def read_code_file(path: str | Path, encoding: str = "utf-8") -> str:
    """Reads a source code file from disk."""
    return Path(path).read_text(encoding=encoding)


def list_code_files(root: str | Path, extensions: set[str] | None = None) -> list[Path]:
    """Lists code files under a root directory."""
    root_path = Path(root)
    allowed = extensions or _CODE_EXTENSIONS
    return sorted(path for path in root_path.rglob("*") if path.is_file() and path.suffix in allowed)


def extract_python_symbols(source: str) -> list[dict[str, str | int]]:
    """Extracts top-level Python functions and classes from source code."""
    tree = ast.parse(source)
    symbols: list[dict[str, str | int]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(
                {
                    "name": node.name,
                    "type": _symbol_type(node),
                    "lineno": node.lineno,
                    "end_lineno": getattr(node, "end_lineno", node.lineno),
                }
            )
    return symbols


def extract_python_symbol_chunks(source: str) -> list[dict[str, str | int]]:
    """Extracts source chunks for top-level Python functions and classes."""
    lines = source.splitlines()
    chunks: list[dict[str, str | int]] = []
    for symbol in extract_python_symbols(source):
        start = int(symbol["lineno"])
        end = int(symbol["end_lineno"])
        chunks.append(
            {
                **symbol,
                "content": "\n".join(lines[start - 1 : end]),
            }
        )
    return chunks


def parse_python_file(path: str | Path) -> list[dict[str, str | int]]:
    """Reads a Python file and extracts top-level symbol chunks."""
    return extract_python_symbol_chunks(read_code_file(path))


def _symbol_type(node: ast.AST) -> str:
    if isinstance(node, ast.ClassDef):
        return "class"
    if isinstance(node, ast.AsyncFunctionDef):
        return "async_function"
    return "function"
