# 02 - 工具系统

## 目标

实现一个真正的 Agent，能够操作文件系统。

**完成后你将学到：**
- 如何定义工具的 Schema
- 如何把工具名映射到实际函数
- 如何安全地解析参数
- 如何实现多个工具

## 开始之前

### 上一节我们学了什么

第一章我们了解了 Agent 的核心原理：一个能调用工具的循环。

但第一章的代码里，工具部分是简写的：
```python
result = execute_tool(tc)  # 这是什么？怎么执行的？
```

这一节我们来补全这个 `execute_tool` 到底是怎么实现的。

### 这一节我们要学什么

| 第一章 | 这一章（新增） |
|--------|---------------|
| Agent 循环逻辑 | 工具的定义和实现 |
| `execute_tool(tc)` 简写 | 参数解析 `json.loads()` |
| 单文件结构 | 分模块结构 |
| 无 | 危险命令检查 |

### 工具的组成

每个工具由三部分组成：

1. **name**：工具名称，LLM 用这个名字来调用
2. **description**：工具描述，LLM 根据这个决定什么时候用
3. **执行函数**：实际执行的 Python 函数

例如 bash 工具：
- name: `bash`
- description: `执行 bash 命令，用于运行程序、系统操作等`
- 执行函数: `def bash(command: str) -> str: ...`

### 项目结构

```
02-tools/
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

## 核心代码

### tools/bash.py - bash 工具

**name:** `bash`
**description:** `执行 bash 命令，用于运行程序、系统操作等`

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

### tools/read_file.py - 读取文件

**name:** `read_file`
**description:** `读取文件内容`

```python
def read_file(path: str) -> str:
    """读取文件内容"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"
```

### tools/write_file.py - 写入文件

**name:** `write_file`
**description:** `写入文件内容，会覆盖原有内容`

```python
import os

def write_file(path: str, content: str) -> str:
    """写入文件内容"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error: {e}"
```

### tools/edit_file.py - 编辑文件

**name:** `edit_file`
**description:** `编辑文件，替换指定的文本内容`

```python
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
```

### tools/glob.py - 查找文件

**name:** `glob`
**description:** `查找匹配模式的文件，支持通配符`

```python
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
```

### tools/grep.py - 搜索内容

**name:** `grep`
**description:** `在文件中搜索内容`

```python
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
```

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

### agent.py - 工具参数解析

第一章的代码概览里，工具执行是简写的：

```python
# 第一章简写
for tc in msg.tool_calls:
    result = execute_tool(tc)
```

这一节我们来实现真正的参数解析：

```python
for tc in msg.tool_calls:
    # 1. 获取工具名
    func_name = tc.function.name

    # 2. 解析参数（JSON 字符串 → 字典）
    try:
        args = json.loads(tc.function.arguments)
    except json.JSONDecodeError:
        args = {}

    # 3. 查找并执行工具
    if func_name not in available_functions:
        result = f"Error: 未知工具 {func_name}"
    else:
        try:
            result = available_functions[func_name](**args)
        except Exception as e:
            result = f"Error: {e}"

    # 4. 结果放回消息
    messages.append({
        "role": "tool",
        "tool_call_id": tc.id,
        "content": str(result)
    })
```

**关键点：**
- `tc.function.arguments` 是 JSON 字符串，如 `'{"command": "ls"}'`
- `json.loads()` 把它转成字典 `{"command": "ls"}`
- `**args` 把字典展开为函数参数，等同于 `bash(command="ls")`

## 下一步

[03-error-handling](../03-error-handling) - 添加错误处理，让 Agent 更健壮。
