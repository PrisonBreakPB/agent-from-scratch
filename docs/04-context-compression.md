# 04 - 上下文压缩

## 目标

实现上下文压缩，处理长对话时避免 token 超限。

**完成后你将学到：**
- 为什么需要上下文压缩
- 三层压缩策略的原理
- 如何实现自动压缩

## 开始之前

### 为什么需要上下文压缩？

LLM 有 token 限制，比如 128K tokens。当对话变长时：

```
第 1 轮：100 tokens
第 2 轮：200 tokens
...
第 50 轮：50000 tokens
第 100 轮：超出限制 ❌
```

**问题：**
- 工具返回的内容可能很长（比如读取大文件）
- 对话历史会不断累积
- 超出限制后 API 会报错

### 如何计算上下文使用量？

要决定何时压缩，首先要知道当前用了多少 token。

**方法一：完全估算**

粗略估算：1 个 token ≈ 3-4 个字符（中英文混合）

```python
def estimate_tokens(text):
    return len(text) // 3
```

**方法二：精确计算（调用 API）**

OpenAI 提供了 `tiktoken` 库，可以精确计算 token 数：

```python
import tiktoken

encoder = tiktoken.encoding_for_model("gpt-4o-mini")

def count_tokens(text):
    return len(encoder.encode(text))
```

**方法三：上一轮精确值 + 本轮输入估算（我们的选择）**

OpenAI API 的响应里包含 token 使用量：

```python
response = client.chat.completions.create(...)
print(response.usage.total_tokens)  # 精确的 token 数
```

我们可以利用这个信息：

```python
# 第一轮：没有上一轮数据，用估算
current_tokens = len(user_input) // 3

# 第二轮起：上一轮精确值 + 本轮输入估算
current_tokens = last_token_usage + len(user_input) // 3
```

**注意：** 这个计算方法假设没有发生上下文压缩。如果发生压缩，实际 token 会减少，需要用压缩后的值重新计算。

**对比：**

| 方法 | 精度 | 速度 | 依赖 |
|------|------|------|------|
| 完全估算 | 粗略 | 快 | 无 |
| tiktoken | 精确 | 慢 | 需要安装 |
| 上一轮精确 + 本轮估算 | 较精确 | 快 | 无 |

**我们的选择：** 方法三，因为：
- 不需要额外依赖
- 速度快
- 精度较高（利用 API 返回的精确值）

### 压缩策略

参考 Claude Code 和 CoreCoder，采用三层压缩：

| 层级 | 触发条件 | 策略 |
|------|---------|------|
| Layer 1 | 50% token | 截断冗长的工具输出 |
| Layer 2 | 70% token | LLM 总结旧对话 |
| Layer 3 | 90% token | 只保留摘要和最近消息 |

### 整体流程

```
每轮对话后检查 token
        ↓
    超过 50%？
    ├─ 是 → Layer 1：截断工具输出
    └─ 否 → 跳过
        ↓
    超过 70%？
    ├─ 是 → Layer 2：LLM 总结旧对话
    └─ 否 → 跳过
        ↓
    超过 90%？
    ├─ 是 → Layer 3：只保留摘要
    └─ 否 → 跳过
```

## 核心代码

### context.py - 上下文管理器

```python
def estimate_tokens(messages):
    """估算 token 数量"""
    total = 0
    for m in messages:
        if m.get("content"):
            total += len(m["content"]) // 3
    return total

class ContextManager:
    def __init__(self, max_tokens=128000):
        self.max_tokens = max_tokens
        self._snip_at = int(max_tokens * 0.50)
        self._summarize_at = int(max_tokens * 0.70)
        self._collapse_at = int(max_tokens * 0.90)

    def maybe_compress(self, messages, llm=None):
        """检查是否需要压缩，执行压缩"""
        current = estimate_tokens(messages)

        # Layer 1: 截断工具输出
        if current > self._snip_at:
            self._snip_tool_outputs(messages)

        # Layer 2: LLM 总结
        if current > self._summarize_at:
            self._summarize_old(messages, llm)

        # Layer 3: 硬压缩
        if current > self._collapse_at:
            self._hard_collapse(messages, llm)
```

**作用：** 根据 token 使用情况，自动选择压缩层级。

### Layer 1：截断工具输出

```python
def _snip_tool_outputs(self, messages):
    """截断冗长的工具输出"""
    for m in messages:
        if m.get("role") != "tool":
            continue
        content = m.get("content", "")
        if len(content) <= 1500:
            continue
        # 保留前3行和后3行
        lines = content.splitlines()
        snipped = (
            "\n".join(lines[:3])
            + f"\n... ({len(lines)} lines, snipped) ...\n"
            + "\n".join(lines[-3:])
        )
        m["content"] = snipped
```

**原理：** 工具输出通常很长，但大部分是中间内容，保留头尾即可。

### Layer 2：LLM 总结

```python
def _summarize_old(self, messages, llm, keep_recent=8):
    """用 LLM 总结旧对话"""
    old = messages[:-keep_recent]
    tail = messages[-keep_recent:]

    summary = self._get_summary(old, llm)

    messages.clear()
    messages.append({
        "role": "user",
        "content": f"[对话摘要]\n{summary}"
    })
    messages.append({
        "role": "assistant",
        "content": "好的，我了解之前的上下文了。"
    })
    messages.extend(tail)
```

**原理：** 用 LLM 把旧对话压缩成摘要，只保留最近的消息。

### Layer 3：硬压缩

```python
def _hard_collapse(self, messages, llm):
    """最后手段：只保留摘要和最近4条消息"""
    tail = messages[-4:]
    summary = self._get_summary(messages[:-4], llm)

    messages.clear()
    messages.append({
        "role": "user",
        "content": f"[上下文重置]\n{summary}"
    })
    messages.append({
        "role": "assistant",
        "content": "好的，继续。"
    })
    messages.extend(tail)
```

**原理：** 紧急情况，只保留最基本的信息。

### 集成到 Agent

```python
class AgentLoop:
    def __init__(self, config):
        self.context = ContextManager(max_tokens=128000)
        # ...

    def chat(self, user_input, on_token=None):
        self.messages.append({"role": "user", "content": user_input})

        # 每轮对话后检查压缩
        self.context.maybe_compress(self.messages, self.client)

        # ... 调用 LLM ...
```

**关键：** 在每轮对话后自动检查并压缩。

### 手动压缩：/compact 命令

除了自动压缩，还可以手动触发：

```python
# cli.py
if user_input == "/compact":
    from context import estimate_tokens
    before = estimate_tokens(agent.messages)
    agent.context.check_and_compress(agent.messages, agent.client)
    after = estimate_tokens(agent.messages)
    console.print(f"[green]Compressed: {before} → {after} tokens[/green]")
    continue
```

**使用场景：**
- 对话变长，想主动压缩
- 测试压缩效果
- 准备开始新话题前清理上下文

**运行效果：**
```
You > /compact
Compressed: 50000 → 15000 tokens
```

## 运行效果

```
You > 读取一个大文件
（文件内容显示）

You > 继续讨论
（对话变长，自动压缩）

[对话摘要]
之前读取了 config.py 文件，讨论了配置项的含义...
```

## 下一步

敬请期待...
