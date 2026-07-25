# 01 - 最小 Agent 循环

## 目标

理解 Agent 的核心原理：一个能调用工具的循环。

**完成后你将理解：**
- 什么是 ReAct 范式
- Agent 的核心是一个循环
- 工具调用的基本原理

## 开始之前

### 什么是 Agent？

普通的大模型只能聊天，你问一句，它答一句。

Agent 不一样，它能**主动做事**。比如：
- 你说"现在几点了"，它会去调用时间工具获取真实时间
- 你说"帮我算一下 100 * 2"，它会调用计算器工具得到结果
- 你说"列出当前目录的文件"，它会调用 bash 工具执行命令

关键区别：**普通大模型只能"说"，Agent 能"做"。**

### ReAct 范式

ReAct 是一种让大模型"做事"的方法论，全称是 **Re**asoning + **Act**ing（推理 + 行动）。

传统的大模型只能一次性回答，而 ReAct 让大模型能够：

1. **思考**（Thought）：分析当前情况，决定下一步该做什么
2. **行动**（Action）：执行具体操作，比如调用工具
3. **观察**（Observation）：获取行动的结果
4. **循环**：根据观察结果继续思考，直到完成任务

用一个例子来理解：

```
用户：帮我看看当前目录有什么文件

[思考] 用户想看目录内容，我需要调用 bash 工具执行 ls 命令
[行动] 调用 bash 工具，参数是 "ls"
[观察] 得到结果：file1.txt  file2.py  README.md

[思考] 结果拿到了，可以告诉用户
[行动] 不需要工具了，直接回答
```

**ReAct 的核心思想：让大模型像人一样，先想再做，做了再想。**

### 为什么需要循环？

你可能会想，调用工具不就是执行一个函数吗？为什么需要循环？

因为**一次调用不够**。考虑这个场景：

```
用户：帮我看看当前目录有什么文件，然后告诉我 file1.txt 的内容
```

Agent 需要：
1. 调用 bash 执行 `ls` → 得到文件列表
2. 调用 bash 执行 `cat file1.txt` → 得到文件内容
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

## 代码概览

整个 Agent 的核心逻辑非常简单，只有 30 行左右：

```python
from openai import OpenAI

client = OpenAI()

def agent_loop(user_input):
    messages = [
        {"role": "system", "content": "你是一个有用的助手，可以使用工具来完成任务。"},
        {"role": "user", "content": user_input}
    ]

    while True:
        # 1. 调用 LLM
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

        # 2. 没有工具调用，结束
        if not msg.tool_calls:
            return msg.content

        # 3. 执行工具，结果放回消息
        for tc in msg.tool_calls:
            result = execute_tool(tc)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result
            })
```

**注意：** 这里 `execute_tool()` 是简写，具体实现（工具定义、参数解析等）在下一章介绍。

### 代码解释

这段代码做了 3 件事：

**1. 初始化消息列表**

```python
messages = [
    {"role": "system", "content": "你是一个有用的助手，可以使用工具来完成任务。"},
    {"role": "user", "content": user_input}
]
```

- `system`：系统提示词，告诉 LLM 它的角色和能力
- `user`：用户的输入

**2. 调用 LLM 并判断是否结束**

```python
response = client.chat.completions.create(...)
msg = response.choices[0].message

if not msg.tool_calls:
    return msg.content
```

每次循环都会调用 LLM，如果它没有请求调用工具，说明已经有了最终答案。

**3. 执行工具并继续循环**

```python
for tc in msg.tool_calls:
    result = execute_tool(tc)
    messages.append({
        "tool_call_id": tc.id,
        "role": "tool",
        "content": result
    })
```

执行工具后，把结果放回 `messages`，让 LLM 看到执行结果，然后继续循环。

**这就是整个 Agent 的核心：调用 LLM → 执行工具 → 把结果告诉 LLM → 循环直到完成。**

## 关键概念

### 消息列表（messages）

`messages` 是对话历史，每次调用 LLM 都要传进去。

LLM 需要看到完整的历史才能理解上下文，否则会"失忆"。

### 工具调用（tool_calls）

LLM 返回的响应可能包含 `tool_calls`，表示它想调用某个工具。

每个 tool_call 包含：
- 工具名
- 参数

### 工具结果

执行工具后，要把结果放回 messages，让 LLM 看到执行结果。

## 运行方式

本章提供了一个完整的 CLI 入口文件 `main.py`，你可以直接运行：

```bash
cd 01-minimal-loop
python main.py
```

然后就可以和 Agent 对话了。

### main.py - 入口文件

第一章的 main.py 是一个独立文件，包含所有代码，可以直接运行：

```bash
python main.py
```

详见 `01-minimal-loop/main.py`。

## 下一步

[02-tools](../02-tools) - 学习如何定义工具、解析参数，实现一个真正的 Agent。
