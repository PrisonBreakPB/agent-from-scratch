# 04 - 上下文压缩

## 目标

实现上下文压缩，处理长对话时避免 token 超限。

**完成后你将学到：**
- 为什么需要上下文压缩
- 三层压缩策略的原理
- 如何实现自动压缩

## 开始之前

### 为什么需要上下文压缩？

很多人以为"只要没超过最大 token 数就没问题"。

实际上，上下文越长，Agent 不一定越聪明，反而可能：
- 更贵（每次调用都要发送完整历史）
- 更慢（处理时间增加）
- 更容易被无关信息干扰

### Agent 的上下文增长特点

普通聊天的上下文增长：

```
用户问题 → 模型回答
用户追问 → 模型回答
```

Agent 的上下文增长：

```
用户任务
→ 模型决策
→ 调用工具
→ 工具结果
→ 再次调用工具
→ 工具报错
→ 重试
→ 生成中间结论
→ 继续执行
```

每一步都可能把以下内容加入上下文：
- 工具参数
- 工具返回结果（可能很长）
- 错误信息
- Agent 的中间计划
- 历史对话

**所以：** 没有压缩，长任务最终会因为上下文溢出而无法继续。

### 上下文质量问题

即使没有超限，上下文太长也会带来问题：

| 问题 | 说明 |
|------|------|
| 上下文干扰 | 历史里有大量和当前步骤无关的内容，模型需要在其中寻找有用信息 |
| 上下文污染 | 之前产生了一个错误判断，后面每轮都把错误当成已知事实继续使用 |
| 上下文冲突 | 较早的工具结果和较新的工具结果不一致，模型不知道该相信哪个 |
| 关键信息被淹没 | 重要的任务目标、约束或决策被大量工具输出淹没 |

**所以：** 压缩不只是防止报错，也是为了减少干扰，让模型更容易抓住当前任务。

### 压缩的目标

上下文压缩不是简单地"删除旧消息"，而是：

- **保留**对下一步决策有用的信息
- **移除**重复、过时、低价值的信息
- **把完整历史放到外部存储**，需要时再取回

**应该保留的信息：**
- 任务目标
- 硬约束
- 已经完成的步骤
- 关键决策
- 决策原因
- 已验证事实
- 未解决问题

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
        self._truncate_at = int(max_tokens * 0.50)
        self._summary_at = int(max_tokens * 0.70)
        self._reset_at = int(max_tokens * 0.90)

    def check_and_compress(self, messages, llm=None):
        """检查是否需要压缩，执行压缩"""
        current = estimate_tokens(messages)

        # Layer 1: 截断工具输出
        if current > self._truncate_at:
            self.truncate_tool_results(messages)

        # Layer 2: LLM 总结
        if current > self._summary_at:
            self.summarize_history(messages, llm)

        # Layer 3: 硬压缩
        if current > self._reset_at:
            self.emergency_compress(messages, llm)
```

**作用：** 根据 token 使用情况，自动选择压缩层级。

### Layer 1：截断工具输出

```python
def truncate_tool_results(self, messages):
    """截断冗长的工具输出"""
    for m in messages:
        if m.get("role") != "tool":
            continue
        content = m.get("content", "")
        if len(content) <= 1500:
            continue
        # 保留前3行和后3行
        lines = content.splitlines()
        truncated = (
            "\n".join(lines[:3])
            + f"\n... ({len(lines)} lines, truncated) ...\n"
            + "\n".join(lines[-3:])
        )
        m["content"] = truncated
```

**原理：** 工具输出通常很长，但大部分是中间内容，保留头尾即可。

### Layer 2：LLM 总结

```python
def summarize_history(self, messages, llm, keep_recent=8):
    """用 LLM 总结旧对话"""
    old = messages[:-keep_recent]
    tail = messages[-keep_recent:]

    summary = self._generate_summary(old, llm)

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
def emergency_compress(self, messages, llm):
    """最后手段：只保留摘要和最近4条消息"""
    tail = messages[-4:]
    summary = self._generate_summary(messages[:-4], llm)

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
        self.context = ContextManager(max_tokens=config.max_context_tokens)
        self.last_token_usage = 0

    def chat(self, user_input, on_token=None):
        self.messages.append({"role": "user", "content": user_input})

        # 检查是否需要压缩（用上一轮精确值 + 本轮输入估算）
        estimated_new = len(user_input) // 3
        current_tokens = self.last_token_usage + estimated_new
        if current_tokens > self.context.max_tokens * 0.5:
            self.context.check_and_compress(self.messages, self.client)

        # ... 调用 LLM ...

        # 更新 token 使用量
        if hasattr(chunk, 'usage') and chunk.usage:
            self.last_token_usage = chunk.usage.total_tokens
```

**关键：** 用上一轮的精确值 + 本轮输入估算，更准确地判断何时压缩。

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

## 当前实现的局限性

我们的压缩策略是"简单摘要"，可能会丢失重要信息：

**原始历史：**
```
我们因为 A 的性能问题选择方案 B，
但 B 只适用于数据规模小于 10 万条的情况。
```

**简单摘要：**
```
团队选择了方案 B。
```

这个摘要保留了"做了什么"，却丢掉了：
- 为什么这么做
- 适用条件是什么
- 哪些方案被排除了

**更好的方案：** 保留结构化状态，而不是简单摘要：
- 任务目标
- 硬约束
- 关键决策
- 决策原因
- 已验证事实
- 未解决问题

这属于 Context Engineering 的范畴，不只是字符串截断。

## 下一步

敬请期待...
