from pathlib import Path

def read_file(path: str, offset: int = 1, limit: int = 2000) -> str:
    """读取文件内容，支持分页"""
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: {path} not found"
        if not p.is_file():
            return f"Error: {path} is a directory, not a file"

        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        total = len(lines)

        start = max(0, offset - 1)
        chunk = lines[start : start + limit]
        numbered = [f"{start + i + 1}\t{ln}" for i, ln in enumerate(chunk)]
        result = "\n".join(numbered)

        if total > start + limit:
            result += f"\n... ({total} lines total, showing {start+1}-{start+len(chunk)})"
        return result or "(empty file)"
    except Exception as e:
        return f"Error: {e}"
