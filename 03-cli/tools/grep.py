import re
from pathlib import Path

# 跳过这些目录
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", "dist", "build"}

def grep(pattern: str, path: str = ".", include: str | None = None) -> str:
    """在文件中搜索内容"""
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"Invalid regex: {e}"

    base = Path(path).expanduser().resolve()
    if not base.exists():
        return f"Error: {path} not found"

    if base.is_file():
        files = [base]
    else:
        files = _walk(base, include)

    matches = []
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                matches.append(f"{fp}:{lineno}: {line.rstrip()}")
                if len(matches) >= 200:
                    matches.append("... (200 match limit reached)")
                    return "\n".join(matches)

    return "\n".join(matches) if matches else "No matches found."

def _walk(root: Path, include: str | None) -> list[Path]:
    """遍历目录，跳过无关目录"""
    results = []
    for item in root.rglob(include or "*"):
        if any(part in _SKIP_DIRS for part in item.relative_to(root).parts):
            continue
        if item.is_file():
            results.append(item)
        if len(results) >= 5000:
            break
    return results
