"""Lightweight repository map — generates a compact summary of the codebase structure.

This gives agents awareness of the full project without blowing the context window.
Uses basic AST parsing (no tree-sitter dependency) to extract function/class signatures.
"""

import ast
import os
from pathlib import Path

SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", "venv", ".venv",
    ".builder", ".builder.bak", ".next", "dist", "build",
    ".expo", ".cache", "coverage",
}

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
}

MAX_MAP_CHARS = 15000


def generate_repo_map(project_dir: Path) -> str:
    """Generate a compact repository map showing file structure and key symbols."""
    parts = ["# Repository Map\n"]

    # File tree
    parts.append("## File Structure\n```")
    tree_lines = _build_file_tree(project_dir)
    parts.append("\n".join(tree_lines))
    parts.append("```\n")

    # Key symbols (functions, classes) from Python files
    symbols = _extract_symbols(project_dir)
    if symbols:
        parts.append("## Key Symbols\n")
        for filepath, file_symbols in symbols.items():
            rel_path = os.path.relpath(filepath, project_dir)
            parts.append(f"### {rel_path}")
            for sym in file_symbols:
                parts.append(f"  {sym}")
            parts.append("")

    result = "\n".join(parts)
    if len(result) > MAX_MAP_CHARS:
        result = result[:MAX_MAP_CHARS] + "\n\n... [truncated]"
    return result


def _build_file_tree(project_dir: Path, prefix: str = "", max_depth: int = 4) -> list[str]:
    lines = []
    try:
        entries = sorted(project_dir.iterdir(), key=lambda e: (not e.is_dir(), e.name))
    except PermissionError:
        return lines

    dirs = [e for e in entries if e.is_dir() and e.name not in SKIP_DIRS and not e.name.startswith(".")]
    files = [e for e in entries if e.is_file() and not e.name.startswith(".")]

    for f in files:
        lines.append(f"{prefix}{f.name}")

    if max_depth > 0:
        for d in dirs:
            lines.append(f"{prefix}{d.name}/")
            lines.extend(_build_file_tree(d, prefix=prefix + "  ", max_depth=max_depth - 1))

    return lines


def _extract_symbols(project_dir: Path) -> dict[str, list[str]]:
    """Extract function and class signatures from Python files."""
    symbols = {}

    for py_file in project_dir.rglob("*.py"):
        if any(skip in py_file.parts for skip in SKIP_DIRS):
            continue
        try:
            source = py_file.read_text(errors="ignore")
            tree = ast.parse(source, filename=str(py_file))
        except (SyntaxError, ValueError):
            continue

        file_symbols = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                methods = [
                    n.name for n in ast.iter_child_nodes(node)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not n.name.startswith("_")
                ]
                method_str = f" [{', '.join(methods)}]" if methods else ""
                file_symbols.append(f"class {node.name}{method_str}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    args = [a.arg for a in node.args.args if a.arg != "self"]
                    file_symbols.append(f"def {node.name}({', '.join(args)})")

        if file_symbols:
            symbols[str(py_file)] = file_symbols

    return symbols
