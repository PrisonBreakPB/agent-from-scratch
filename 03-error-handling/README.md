# 03 - 错误处理

## 目标

让 Agent 在出错时不会崩溃，能优雅地处理各种异常情况。

**完成后你将学到：**
- Agent 可能遇到哪些错误
- 如何用 try/except 保护代码
- 如何把错误信息告诉 LLM，让它自己调整

## 开始之前

### 为什么需要错误处理？

上一节的代码有个问题：**任何一步出错，整个程序就崩溃了。**

```python
# 这些地方都可能出错
response = client.chat.completions.create(...)  # 网络错误、API 错误
args = json.loads(tc.function.arguments)        # JSON 解析错误
result = available_functions[func_name](**args)  # 函数执行错误
```

真实场景中，错误是常态：
- 命令执行失败
- 网络突然断了
- API Key 过期了
- LLM 返回了不存在的工具名

**一个成熟的 Agent 必须能处理这些情况。**

### 错误处理的策略

遇到错误时，有两种选择：

1. **直接告诉用户**："出错了，请重试"
2. **告诉 LLM**：让它知道发生了什么，自己调整

我们选择第二种，因为：
- LLM 可能能理解错误并重试
- 用户体验更好（不用自己判断该怎么重试）

### 整体流程

```
用户输入
    ↓
[LLM 思考]
    ↓
[执行工具] ──→ 出错了？
    │              │
    │ 是           │ 否
    ▼              ▼
[错误信息]    [正常结果]
    │              │
    └──────┬───────┘
           ▼
    [结果告诉 LLM]
           ▼
    [继续循环或结束]
```

## 核心代码

```python
import json
import subprocess
from openai import OpenAI

client = OpenAI()
MAX_STEPS = 10

# 工具实现
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

# 工具注册
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

available_functions = {"bash": bash}

def agent_loop(user_input: str) -> str:
    messages = [
        {"role": "system", "content": "你是一个有用的助手，可以使用工具来回答问题。"},
        {"role": "user", "content": user_input}
    ]

    for step in range(MAX_STEPS):
        # 1. API 调用错误
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

        # 2. 没有工具调用，返回最终回答
        if not msg.tool_calls:
            return msg.content or "无响应内容"

        # 3. 处理工具调用
        for tc in msg.tool_calls:
            func_name = tc.function.name

            # 4. 参数解析错误
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            # 5. 未知工具错误
            if func_name not in available_functions:
                result = f"Error: 未知工具 {func_name}"
            else:
                # 6. 工具执行错误
                try:
                    result = available_functions[func_name](**args)
                except Exception as e:
                    result = f"Error: {e}"

            # 7. 把结果（成功或失败）告诉 LLM
            messages.append({
                "tool_call_id": tc.id,
                "role": "tool",
                "content": str(result)
            })

    return "达到最大步数限制"

if __name__ == "__main__":
    print("=== 03-error-handling ===")
    print("支持工具：get_time, calculate")
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

### 第一部分：API 调用错误

```python
try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools
    )
except Exception as e:
    return f"API 调用失败: {e}"
```

可能的错误：
- 网络连接失败
- API Key 无效
- 额度用完了
- 服务器错误

这里选择直接返回错误信息给用户，因为没有 LLM 可以帮忙。

### 第二部分：参数解析错误

```python
try:
    args = json.loads(tc.function.arguments)
except json.JSONDecodeError:
    args = {}
```

LLM 有时会返回不合法的 JSON。解析失败时，我们给一个空字典，让工具自己处理缺失参数。

### 第三部分：未知工具错误

```python
if func_name not in available_functions:
    result = f"Error: 未知工具 {func_name}"
```

LLM 可能会"幻觉"出一个不存在的工具名。我们把错误告诉 LLM，它会意识到自己犯错了。

### 第四部分：工具执行错误

```python
try:
    result = available_functions[func_name](**args)
except Exception as e:
    result = f"Error: {e}"
```

工具执行可能失败，比如：
- 用户输入了不合法的表达式
- 除以零
- 文件不存在

**关键：** 把错误信息作为工具结果返回给 LLM，而不是崩溃。

### 第五部分：错误信息也是结果

```python
messages.append({
    "tool_call_id": tc.id,
    "role": "tool",
    "content": str(result)  # 可能是正常结果，也可能是错误信息
})
```

LLM 看到错误信息后，可能会：
- 换个方式重试
- 告诉用户发生了什么
- 放弃这个任务

## 运行效果

### 正常情况

```
你: 计算 100 * 2
AI: 100 * 2 = 200
```

### 工具错误，LLM 自己调整

```
你: 计算 abc
AI: 抱歉，"abc" 不是一个有效的数学表达式。请提供一个数字表达式，比如 2+2 或 100*2。
```

### 未知工具，LLM 知道犯错了

```
你: 帮我翻译一句话
AI: 抱歉，我目前只有获取时间和计算数学表达式的工具，没有翻译功能。
```

## 思考题

1. 为什么要把错误信息返回给 LLM，而不是直接告诉用户？
2. 如果 API 调用失败，为什么选择直接返回而不是重试？
3. `MAX_STEPS` 的作用是什么？如果没有会怎样？

## 下一步

[04-cli-interface](../04-cli-interface) - 做一个真正可用的命令行工具。
