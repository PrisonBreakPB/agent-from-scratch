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

### 项目结构

```
02-add-tools/
├── main.py              # 入口文件
├── agent.py             # Agent 循环逻辑
└── tools/
    ├── __init__.py      # 工具注册
    ├── bash.py          # bash 工具
    ├── read_file.py     # 读文件
    ├── write_file.py    # 写文件
    ├── edit_file.py     # 编辑文件
    ├── glob.py          # 查找文件
    └── grep.py          # 搜索内容
```

为什么要这样组织？
- 每个工具一个文件，方便查找和修改
- agent.py 单独存放，逻辑清晰
- tools/__init__.py 统一注册，添加新工具只需改这里

## 核心代码

### tools/__init__.py - 工具注册

```python
from .bash import bash
from .read_file import read_file
from .write_file import write_file
from .edit_file import edit_file
from .glob import glob
from .grep import grep

# 工具 Schema
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
    # ... 其他工具
]

# 函数映射
available_functions = {
    "bash": bash,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "glob": glob,
    "grep": grep
}
```

### tools/bash.py - bash 工具

```python
import re
import subprocess

# 危险命令模式
DANGEROUS_PATTERNS = [
    r'\brm\s+(-[a-zA-Z]*r|--recursive)',  # rm -r, rm -rf
    r'\brmdir\b',                          # rmdir
    r'\bmkfs\b',                           # mkfs
    r'\bdd\b.*of=/dev/',                   # dd of=/dev/...
    r'\bformat\b',                         # format
    r'>\s*/dev/',                          # 重定向到设备
    r'\bshutdown\b',                       # shutdown
    r'\breboot\b',                         # reboot
    r'\binit\s+0\b',                       # init 0
    r'\bkill\s+-9\s+1\b',                  # kill -9 1
    r':\(\)\{.*\|.*&\}',                   # fork bomb
]

def bash(command: str) -> str:
    """执行 bash 命令，会检查危险命令"""
    # 检查危险命令
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return f"Error: 检测到危险命令，拒绝执行: {command}"

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

**危险命令检查：**
- 使用正则表达式匹配危险命令模式
- 包括：rm -r、mkfs、dd、shutdown 等
- 匹配到则拒绝执行，返回错误信息

### agent.py - Agent 循环

```python
import json
from openai import OpenAI

from tools import tools, available_functions

client = OpenAI()
MAX_STEPS = 10

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
```

### main.py - 入口文件

```python
from agent import agent_loop

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

## 运行效果

```
你: 当前目录有什么文件？
AI: 当前目录有以下文件：
- main.py
- agent.py
- tools/

你: 读取 main.py 的内容
AI: [显示 main.py 的内容]

你: 创建一个新文件 hello.txt，写入 "Hello World"
AI: 已创建文件 hello.txt，内容为 "Hello World"。

你: 删除 hello.txt
AI: Error: 检测到危险命令，拒绝执行: rm hello.txt
```

## 如何添加新工具

只需 3 步：

```python
# 1. 创建 tools/my_tool.py
def my_tool(param: str) -> str:
    return "result"

# 2. 在 tools/__init__.py 中导入
from .my_tool import my_tool

# 3. 添加 Schema 和映射
tools.append({...})
available_functions["my_tool"] = my_tool
```

## 下一步

[03-error-handling](../03-error-handling) - 添加错误处理，让 Agent 更健壮。
