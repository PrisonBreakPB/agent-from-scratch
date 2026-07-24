from pathlib import Path

def write_file(path: str, content: str) -> str:
    """写入文件内容"""
    try:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        n_lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        return f"Wrote {n_lines} lines to {path}"
    except Exception as e:
        return f"Error: {e}"
