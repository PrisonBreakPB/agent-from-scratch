# 06 - Hooks

## 目标

实现 Hooks 机制，让 Agent 在特定时机执行自定义逻辑。

**完成后你将学到：**
- 什么是 Hooks
- 为什么需要 Hooks
- 如何实现 Hooks 机制

## 开始之前

### 什么是 Hooks？

Hooks 是一种在特定事件发生时执行自定义代码的机制。

**类比：**
- 门铃响了 → 执行"开门"动作
- 用户登录 → 执行"记录日志"动作
- LLM 调用前 → 执行"检查权限"动作

### 为什么需要 Hooks？

没有 Hooks 时，所有逻辑都写在一起：

```python
def chat(self, user_input):
    # 检查权限
    if not check_permission(user_input):
        return "权限不足"

    # 压缩上下文
    self.context.check_and_compress(...)

    # 记录日志
    log(user_input)

    # 调用 LLM
    response = self.call_llm(...)

    # ...
```

**问题：**
- 所有逻辑耦合在一起
- 添加新功能要修改 chat 方法
- 不好扩展

有 Hooks 时，逻辑可以分开：

```python
def chat(self, user_input):
    self.trigger_hooks("before_llm", user_input)
    response = self.call_llm(...)
    self.trigger_hooks("after_llm", response)
```

**好处：**
- 解耦：每个 hook 只做一件事
- 可扩展：随时添加新 hook
- 可配置：可以启用/禁用某些 hook

### Hooks 的时机

```
用户输入
    ↓
[before_llm] ← hook：权限检查、上下文压缩、日志
    ↓
LLM 调用
    ↓
[after_llm] ← hook：响应解析、token 统计
    ↓
[before_tool] ← hook：参数验证、权限检查
    ↓
工具执行
    ↓
[after_tool] ← hook：结果过滤、日志记录
    ↓
返回结果
```

## 核心代码

### hooks.py - Hook 管理器

```python
class HookManager:
    def __init__(self):
        self.hooks = {
            "before_llm": [],
            "after_llm": [],
            "before_tool": [],
            "after_tool": [],
        }

    def register(self, event, callback):
        """注册一个 hook"""
        if event not in self.hooks:
            raise ValueError(f"Unknown event: {event}")
        self.hooks[event].append(callback)

    def trigger(self, event, *args, **kwargs):
        """触发所有 hooks"""
        for hook in self.hooks[event]:
            hook(*args, **kwargs)
```

**作用：** 管理所有 hooks，支持注册和触发。

### 使用示例

```python
# 创建 hook 管理器
hooks = HookManager()

# 注册 hooks
hooks.register("before_llm", check_permission)
hooks.register("before_llm", log_request)
hooks.register("after_tool", log_result)

# 在 Agent 中使用
class Agent:
    def __init__(self):
        self.hooks = HookManager()

    def chat(self, user_input):
        # 触发 before_llm hooks
        self.hooks.trigger("before_llm", user_input)

        response = self.call_llm(...)

        # 触发 after_llm hooks
        self.hooks.trigger("after_llm", response)

        # ...
```

### 把上下文压缩做成 Hook

```python
# 定义 hook
def compress_hook(messages, llm_client):
    context = ContextManager()
    context.check_and_compress(messages, llm_client)

# 注册
agent.hooks.register("before_llm", compress_hook)

# 使用时自动触发
agent.hooks.trigger("before_llm", agent.messages, agent.client)
```

### 把权限检查做成 Hook

```python
# 定义 hook
def permission_hook(user_input):
    if "危险操作" in user_input:
        raise PermissionError("不允许执行危险操作")

# 注册
agent.hooks.register("before_llm", permission_hook)
```

### 把日志记录做成 Hook

```python
# 定义 hook
def log_hook(user_input):
    print(f"[LOG] User: {user_input}")

# 注册
agent.hooks.register("before_llm", log_hook)
```

## 集成到 Agent

```python
class Agent:
    def __init__(self):
        self.hooks = HookManager()
        # 注册默认 hooks
        self.hooks.register("before_llm", self._check_context)

    def _check_context(self, messages, llm_client):
        """默认的上下文压缩 hook"""
        context = ContextManager()
        context.check_and_compress(messages, llm_client)

    def chat(self, user_input):
        self.messages.append({"role": "user", "content": user_input})

        # 触发 before_llm hooks
        self.hooks.trigger("before_llm", self.messages, self.client)

        # 调用 LLM
        response = self.call_llm(...)

        # 触发 after_llm hooks
        self.hooks.trigger("after_llm", response)

        # ...
```

## Claude Code 的 Hooks

Claude Code 也提供了 hooks 机制：

| 事件 | 时机 |
|------|------|
| `PreToolUse` | 工具调用前 |
| `PostToolUse` | 工具调用后 |
| `Notification` | 发送通知时 |
| `Stop` | 即将停止响应时 |

配置方式（`.claude/settings.json`）：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "command": "echo 'About to write a file'"
      }
    ]
  }
}
```

## 下一步

敬请期待...
