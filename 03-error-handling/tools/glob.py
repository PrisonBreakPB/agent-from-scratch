import glob as glob_module

def glob(pattern: str) -> str:
    """查找匹配模式的文件"""
    try:
        files = glob_module.glob(pattern, recursive=True)
        if not files:
            return "No files found"
        return "\n".join(files)
    except Exception as e:
        return f"Error: {e}"
