import difflib
from pathlib import Path

def edit_file(path: str, old_text: str, new_text: str) -> str:
    """编辑文件，替换指定内容"""
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return f"Error: {path} not found"

        try:
            content = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"Error: {path} is not a UTF-8 text file"

        occurrences = content.count(old_text)
        if occurrences == 0:
            preview = content[:500] + ("..." if len(content) > 500 else "")
            return f"Error: old_text not found in {path}.\nFile starts with:\n{preview}"
        if occurrences > 1:
            return f"Error: old_text appears {occurrences} times in {path}. Include more context to make it unique."

        new_content = content.replace(old_text, new_text, 1)
        p.write_text(new_content, encoding="utf-8")

        # 生成 diff
        diff = _unified_diff(content, new_content, str(p))
        return f"Edited {path}\n{diff}"
    except Exception as e:
        return f"Error: {e}"

def _unified_diff(old: str, new: str, filename: str, context: int = 3) -> str:
    """生成 unified diff"""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filename}", tofile=f"b/{filename}",
        n=context,
    )
    result = "".join(diff)
    if len(result) > 3000:
        result = result[:2500] + "\n... (diff truncated)\n"
    return result
