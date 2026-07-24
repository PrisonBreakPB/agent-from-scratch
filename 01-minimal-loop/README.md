# 01 - 最小 Agent 循环

## 目标

用最少的代码实现一个能调用工具的 Agent。

**完成后你将理解：**
- Agent 的核心是一个循环
- LLM 如何决定调用工具
- 工具结果如何反馈给 LLM

## 开始之前

### 什么是 Agent？

普通的大模型只能聊天，你问一句，它答一句。

Agent 不一样，它能**主动做事**。比如：
- 你说"现在几点了"，它会去调用时间工具获取真实时间
- 你说"帮我算一下 100 * 2"，它会调用计算器工具得到结果

关键区别：**普通大模型只能"说"，Agent 能"做"。**

### 为什么需要循环？

你可能会想，调用工具不就是执行一个函数吗？为什么需要循环？

因为**一次调用不够**。考虑这个场景：

```
用户：先告诉我现在几点，然后计算 100 * 2
```

Agent 需要：
1. 调用时间工具 → 得到时间
2. 调用计算工具 → 得到结果
3. 把两个结果组合成回答

这就是为什么需要循环：**LLM 可能需要多次调用工具才能完成任务。**

### 整体流程

```
        ┌──────────────────────────────────────┐
        │                                      │
        ▼                                      │
   ┌─────────┐                                │
   │ 用户输入 │                                │
   └────┬────┘                                │
        ▼                                      │
   ┌─────────┐                                │
   │ LLM 思考 │                                │
   └────┬────┘                                │
        │                                      │
        ▼                                      │
   ┌───────────────┐                          │
   │ 需要调用工具？ │                          │
   └───────┬───────┘                          │
           │                                   │
     ┌─────┴─────┐                            │
     │           │                            │
    是           否                           │
     │           │                            │
     ▼           ▼                            │
┌─────────┐ ┌─────────┐                      │
│ 执行工具 │ │ 最终回答 │                      │
└────┬────┘ └─────────┘                        │
     │                                         │
     ▼                                         │
┌─────────────┐                                │
│ 结果告诉 LLM │────────────────────────────────┘
└─────────────┘
```

## 核心代码

理解了原理，我们来看代码。整个实现只有 30 行：

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
def agent_loop(user_input):
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
