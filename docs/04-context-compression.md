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
