# 01 - 最小 ReAct 循环

## 目标

用最少的代码实现一个能调用工具的 Agent。

**完成后你将理解：**
- Agent 的核心是一个循环
- LLM 如何决定调用工具
- 工具结果如何反馈给 LLM

## 核心代码

```python
from openai import OpenAI

client = OpenAI()

# 1. 定义工具
tools = [{
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "获取当前时间",
        "parameters": {"type": "object", "properties": {}}
    }
}]

# 2. 循环
def react_loop(user_input):
    messages = [
        {"role": "user", "content": user_input}
    ]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools
        )

        msg = response.choices[0].message
        messages.append(msg)

        # 没有工具调用，结束
        if not msg.tool_calls:
            return msg.content

        # 执行工具，结果放回消息
        for tc in msg.tool_calls:
            from datetime import datetime
            result = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            messages.append({
                "tool_call_id": tc.id,
                "role": "tool",
                "content": result
            })
```

## 逐行讲解

### 第一部分：工具定义

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "获取当前时间",
        "parameters": {"type": "object", "properties": {}}
    }
}]
```

这段代码告诉 LLM："你有一个叫 get_time 的工具可以用"。

- `name`：工具名称，LLM 会用这个名字来调用
- `description`：工具描述，LLM 根据这个决定什么时候用
- `parameters`：参数定义，这个工具不需要参数

### 第二部分：消息列表

```python
messages = [
    {"role": "user", "content": user_input}
]
```

`messages` 是对话历史，OpenAI API 需要这个来理解上下文。

每次调用 API 都要把完整的历史传进去，否则 LLM 会"失忆"。

### 第三部分：调用 LLM

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools
)

msg = response.choices[0].message
messages.append(msg)
```

- `model`：使用的模型
- `messages`：对话历史
- `tools`：可用工具列表

返回的 `msg` 可能包含：
- `content`：文本回答
- `tool_calls`：工具调用请求

### 第四部分：判断是否结束

```python
if not msg.tool_calls:
    return msg.content
```

如果 LLM 没有请求调用工具，说明它已经得到答案了，循环结束。

### 第五部分：执行工具

```python
for tc in msg.tool_calls:
    result = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages.append({
        "tool_call_id": tc.id,
        "role": "tool",
        "content": result
    })
```

- `tc.id`：调用 ID，用于匹配结果
- `role: "tool"`：告诉 LLM 这是工具返回的结果
- 执行完后继续循环，让 LLM 决定下一步

## 运行效果

```
你: 现在几点了？

AI: 现在是 2026-07-24 15:30:45。
```

## 思考题

1. 为什么需要 `messages.append(msg)`？
2. 如果去掉 `if not msg.tool_calls` 会怎样？
3. `tool_call_id` 的作用是什么？

## 下一步

[02-add-tools](../02-add-tools) - 学习如何注册多个工具，让 Agent 更强大。
