def edit_file(path: str, old_text: str, new_text: str) -> str:
    """编辑文件，替换指定内容"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if old_text not in content:
            return f"Error: '{old_text}' not found in {path}"
        content = content.replace(old_text, new_text, 1)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully edited {path}"
    except Exception as e:
        return f"Error: {e}"
