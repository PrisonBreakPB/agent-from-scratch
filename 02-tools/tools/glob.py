from pathlib import Path

def glob(pattern: str, path: str = ".") -> str:
    """查找匹配模式的文件"""
    try:
        base = Path(path).expanduser().resolve()
        if not base.is_dir():
            return f"Error: {path} is not a directory"

        hits = list(base.glob(pattern))
        # 按修改时间排序，最新在前
        hits.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)

        total = len(hits)
        shown = hits[:100]
        lines = [str(h) for h in shown]
        result = "\n".join(lines)

        if total > 100:
            result += f"\n... ({total} matches, showing first 100)"
        return result or "No files matched."
    except Exception as e:
        return f"Error: {e}"
