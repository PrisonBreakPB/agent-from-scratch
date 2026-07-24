# 02 - 工具系统

## 目标

实现一个真正的 Agent，能够操作文件系统。

**完成后你将学到：**
- 如何定义工具的 Schema
- 如何把工具名映射到实际函数
- 如何安全地解析参数
- 如何实现多个工具

## 开始之前

### 上一节的回顾

上一节我们了解了 Agent 的核心原理：一个能调用工具的循环。

但那只是伪代码，这一节我们来实现真正的 Agent。

### 为什么选择文件操作工具？

文件操作是最实用的工具之一，能做很多事情：
- 读取代码文件
- 修改配置文件
- 搜索特定内容
- 创建新文件

有了这些工具，Agent 就能真正帮你写代码、改配置。

### 整体结构

```
工具实现（Python 函数）
    ↓
工具 Schema（告诉 LLM）
    ↓
函数映射（名字 → 函数）
    ↓
Agent 循环中使用
```

## 核心代码

```python
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
                    "command": {
                        "type": "string",
                        "description": "要执行的 bash 命令"
                    }
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
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    }
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
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的内容"
                    }
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
                    "path": {
                        "type": "string",
                        "description": "文件路径"
                    },
                    "old_text": {
                        "type": "string",
                        "description": "要替换的原文本"
                    },
                    "new_text": {
                        "type": "string",
                        "description": "替换后的新文本"
                    }
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
                    "pattern": {
                        "type": "string",
                        "description": "文件匹配模式，如 '*.py' 或 '**/*.txt'"
                    }
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
                    "pattern": {
                        "type": "string",
                        "description": "搜索的文本或正则表达式"
                    },
                    "path": {
                        "type": "string",
                        "description": "搜索路径，默认为当前目录"
                    }
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
```

## 逐行讲解

### 第一部分：工具实现

**bash 工具**

```python
def bash(command: str) -> str:
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
```

执行系统命令，返回输出结果。

**read_file 工具**

```python
def read_file(path: str) -> str:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"
```

读取文件内容，返回字符串。

**write_file 工具**

```python
def write_file(path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error: {e}"
```

写入文件，如果目录不存在会自动创建。

**edit_file 工具**

```python
def edit_file(path: str, old_text: str, new_text: str) -> str:
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
```

编辑文件，只替换第一次出现的文本。

**glob 工具**

```python
def glob(pattern: str) -> str:
    try:
        files = glob_module.glob(pattern, recursive=True)
        if not files:
            return "No files found"
        return "\n".join(files)
    except Exception as e:
        return f"Error: {e}"
```

查找匹配模式的文件，支持 `*` 和 `**` 通配符。

**grep 工具**

```python
def grep(pattern: str, path: str = ".") -> str:
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
```

在文件中搜索内容，返回匹配的行。

### 第二部分：工具 Schema

每个工具都有一个 Schema，告诉 LLM：
- 工具叫什么名字
- 工具是干什么的
- 需要什么参数

**关键：** `description` 写得好，LLM 就能更准确地决定什么时候用这个工具。

### 第三部分：函数映射

```python
available_functions = {
    "bash": bash,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "glob": glob,
    "grep": grep
}
```

用字典把工具名和实际函数关联起来。

这样 LLM 返回 `"read_file"` 时，我们知道要调用 `read_file()` 函数。

### 第四部分：Agent 循环

```python
def agent_loop(user_input: str) -> str:
    messages = [...]

    for step in range(MAX_STEPS):
        response = client.chat.completions.create(...)
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content

        for tc in msg.tool_calls:
            # 解析参数、执行工具、结果放回消息
            ...
```

这就是上一节伪代码的真正实现。

## 运行效果

```
你: 当前目录有什么文件？
AI: 当前目录有以下文件：
- main.py
- README.md
- requirements.txt

你: 读取 main.py 的内容
AI: [显示 main.py 的内容]

你: 创建一个新文件 hello.txt，写入 "Hello World"
AI: 已创建文件 hello.txt，内容为 "Hello World"。

你: 在 hello.txt 中把 "World" 改成 "Agent"
AI: 已编辑文件 hello.txt，将 "World" 改为 "Agent"。

你: 搜索所有 Python 文件
AI: 找到以下 Python 文件：
- main.py
- utils.py

你: 在 main.py 中搜索 "def" 关键字
AI: 找到以下匹配：
- main.py:10:def bash(command: str) -> str:
- main.py:25:def read_file(path: str) -> str:
```

## 如何添加新工具

只需 3 步：

```python
# 1. 写函数
def my_new_tool(param: str) -> str:
    return "result"

# 2. 添加 Schema
tools.append({
    "type": "function",
    "function": {
        "name": "my_new_tool",
        "description": "描述这个工具干什么",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "参数说明"}
            },
            "required": ["param"]
        }
    }
})

# 3. 注册映射
available_functions["my_new_tool"] = my_new_tool
```

## 下一步

[03-error-handling](../03-error-handling) - 添加错误处理，让 Agent 更健壮。
