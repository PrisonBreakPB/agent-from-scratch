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

这一节的代码和上一节基本相同，错误处理已经内置在每个工具和 agent 循环中：

### agent.py 中的错误处理

```python
# API 调用错误
try:
    response = client.chat.completions.create(...)
except Exception as e:
    return f"API 调用失败: {e}"

# 参数解析错误
try:
    args = json.loads(tc.function.arguments)
except json.JSONDecodeError:
    args = {}

# 未知工具错误
if func_name not in available_functions:
    result = f"Error: 未知工具 {func_name}"
else:
    # 工具执行错误
    try:
        result = available_functions[func_name](**args)
    except Exception as e:
        result = f"Error: {e}"

# 把结果（成功或失败）告诉 LLM
messages.append({
    "role": "tool",
    "tool_call_id": tc.id,
    "content": str(result)
})
```

### tools/bash.py 中的错误处理

```python
def bash(command: str) -> str:
    # 危险命令检查
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return f"Error: 检测到危险命令，拒绝执行: {command}"

    # 命令执行错误
    try:
        result = subprocess.run(...)
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"
```

## 运行效果

### 正常情况

```
你: 计算 100 * 2
AI: 100 * 2 = 200
```

### 工具错误，LLM 自己调整

```
你: 读取不存在的文件
AI: 抱歉，文件不存在。请检查文件路径是否正确。
```

### 未知工具，LLM 知道犯错了

```
你: 帮我翻译一句话
AI: 抱歉，我目前只有文件操作工具，没有翻译功能。
```

## 下一步

[04-cli-interface](../04-cli-interface) - 做一个真正可用的命令行工具。
