import json
import os
import glob as glob_module
import subprocess
from openai import OpenAI

client = OpenAI()
MAX_STEPS = 10

# ========== 工具实现 ==========

def bash(command: str) -> str:
    """执行 bash 命令"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"

def read_file(path: str) -> str:
    """读取文件内容"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"

def write_file(path: str, content: str) -> str:
    """写入文件内容"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error: {e}"

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

def glob(pattern: str) -> str:
    """查找匹配模式的文件"""
    try:
        files = glob_module.glob(pattern, recursive=True)
        if not files:
            return "No files found"
        return "\n".join(files)
    except Exception as e:
        return f"Error: {e}"

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

# ========== 工具注册 ==========

tools = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "执行 bash 命令，用于运行程序、系统操作等",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的 bash 命令"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "写入文件内容，会覆盖原有内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "要写入的内容"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "编辑文件，替换指定的文本内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "old_text": {"type": "string", "description": "要替换的原文本"},
                    "new_text": {"type": "string", "description": "替换后的新文本"}
                },
                "required": ["path", "old_text", "new_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "查找匹配模式的文件，支持通配符",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "文件匹配模式，如 '*.py' 或 '**/*.txt'"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "在文件中搜索内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "搜索的文本或正则表达式"},
                    "path": {"type": "string", "description": "搜索路径，默认为当前目录"}
                },
                "required": ["pattern"]
            }
        }
    }
]

available_functions = {
    "bash": bash,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "glob": glob,
    "grep": grep
}

# ========== Agent 循环 ==========

def agent_loop(user_input: str) -> str:
    messages = [
        {"role": "system", "content": "你是一个有用的助手，可以使用工具来操作文件系统。"},
        {"role": "user", "content": user_input}
    ]

    for step in range(MAX_STEPS):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools
            )
        except Exception as e:
            return f"API 调用失败: {e}"

        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content or "无响应内容"

        for tc in msg.tool_calls:
            func_name = tc.function.name

            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            if func_name not in available_functions:
                result = f"Error: 未知工具 {func_name}"
            else:
                try:
                    result = available_functions[func_name](**args)
                except Exception as e:
                    result = f"Error: {e}"

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result)
            })

    return "达到最大步数限制"

# ========== CLI 入口 ==========

if __name__ == "__main__":
    print("=== Agent with File Tools ===")
    print("支持工具：bash, read_file, write_file, edit_file, glob, grep")
    print("输入 exit 退出\n")

    while True:
        try:
            user_input = input("你: ").strip()
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            if not user_input:
                continue
            print(f"\nAI: {agent_loop(user_input)}\n")
        except KeyboardInterrupt:
            print("\n再见！")
            break
