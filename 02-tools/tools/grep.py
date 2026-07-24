import subprocess

def grep(pattern: str, path: str = ".") -> str:
    """在文件中搜索内容"""
    try:
        result = subprocess.run(
            ["grep", "-r", "-n", pattern, path],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout or "No matches found"
    except Exception as e:
        return f"Error: {e}"
