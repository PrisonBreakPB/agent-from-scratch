# 02 - 工具系统

## 目标

实现一个真正的 Agent，能够调用 bash 工具执行命令。

**完成后你将学到：**
- 如何定义工具的 Schema
- 如何把工具名映射到实际函数
- 如何安全地解析参数
- 如何执行 bash 命令

## 开始之前

### 上一节的回顾

上一节我们了解了 Agent 的核心原理：一个能调用工具的循环。

但那只是伪代码，这一节我们来实现真正的 Agent。

### 为什么选择 bash 工具？

bash 是最通用的工具之一，能做很多事情：
- 查看文件列表：`ls`
- 读取文件内容：`cat file.txt`
- 创建目录：`mkdir new_dir`
- 运行脚本：`python script.py`

有了 bash 工具，Agent 就能和文件系统交互，执行各种操作。

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
import subprocess
from openai import OpenAI

client = OpenAI()
MAX_STEPS = 10

# 1. 工具实现
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

# 2. 工具 Schema（告诉 LLM）
tools = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "执行 bash 命令，用于文件操作、运行程序等",
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
    }
]

# 3. 函数映射
available_functions = {"bash": bash}

# 4. Agent 循环
def agent_loop(user_input: str) -> str:
    messages = [
        {"role": "system", "content": "你是一个有用的助手，可以使用 bash 工具执行命令。"},
        {"role": "user", "content": user_input}
    ]

    for step in range(MAX_STEPS):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools
        )

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
                "tool_call_id": tc.id,
                "role": "tool",
                "content": str(result)
            })

    return "达到最大步数限制"

# 5. CLI 入口
if __name__ == "__main__":
    print("=== Agent with Bash Tool ===")
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

### 第一部分：bash 工具实现

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

这是 bash 工具的核心实现：

- `subprocess.run()`：执行系统命令
- `shell=True`：允许使用 shell 语法（如管道、重定向）
- `capture_output=True`：捕获标准输出和标准错误
- `text=True`：返回字符串而不是字节
- `timeout=30`：超时 30 秒自动终止

**安全提示：** 这里为了简单，直接执行用户输入的命令。在生产环境中，需要添加命令白名单或沙箱。

### 第二部分：工具 Schema

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "执行 bash 命令，用于文件操作、运行程序等",
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
    }
]
```

这是 JSON Schema 格式，告诉 LLM：
- 工具叫什么名字
- 工具是干什么的
- 需要什么参数

**关键：** `description` 写得好，LLM 就能更准确地决定什么时候用这个工具。

### 第三部分：函数映射

```python
available_functions = {"bash": bash}
```

用字典把工具名和实际函数关联起来。

这样 LLM 返回 `"bash"` 时，我们知道要调用 `bash()` 函数。

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

### 第五部分：CLI 入口

```python
if __name__ == "__main__":
    while True:
        user_input = input("你: ")
        print(f"AI: {agent_loop(user_input)}")
```

简单的命令行界面，让用户可以和 Agent 对话。

## 运行效果

```
你: 当前目录有什么文件？
AI: 当前目录有以下文件：
- main.py
- README.md
- requirements.txt

你: 创建一个新文件 test.txt，写入 hello
AI: 已创建文件 test.txt，内容为 "hello"。

你: 读取 test.txt 的内容
AI: test.txt 的内容是 "hello"。
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

## 思考题

1. 为什么需要 `available_functions` 字典？
2. `json.loads()` 和 `eval()` 有什么区别？
3. 如果 LLM 调用一个不存在的工具会怎样？
4. `timeout=30` 的作用是什么？

## 下一步

[03-error-handling](../03-error-handling) - 添加错误处理，让 Agent 更健壮。
