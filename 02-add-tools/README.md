# 02 - 工具系统

## 目标

建立工具注册机制，让添加新工具变得简单。

**完成后你将学到：**
- 如何定义工具的 Schema
- 如何把工具名映射到实际函数
- 如何安全地解析参数

## 和上一节的区别

| | 01 | 02 |
|--|----|----|
| 添加工具 | 改循环代码 | 只需注册 |
| 参数解析 | 无 | json.loads |
| 错误处理 | 无 | 有 |

## 核心代码

```python
import json
from datetime import datetime

# 1. 工具实现
def get_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculate(expression: str) -> str:
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"

# 2. 工具 Schema（告诉 LLM）
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "获取当前时间",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算数学表达式",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 2+2*3"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]

# 3. 函数映射
available_functions = {
    "get_time": get_time,
    "calculate": calculate
}

# 4. 循环中使用
for tc in msg.tool_calls:
    func_name = tc.function.name
    args = json.loads(tc.function.arguments)
    result = available_functions[func_name](**args)
```

## 逐行讲解

### 第一部分：工具实现

```python
def get_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculate(expression: str) -> str:
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"
```

这就是普通的 Python 函数，没有特殊之处。

注意 `calculate` 用了 try/except，因为用户输入的表达式可能不合法。

### 第二部分：工具 Schema

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算数学表达式",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 2+2*3"
                    }
                },
                "required": ["expression"]
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
available_functions = {
    "get_time": get_time,
    "calculate": calculate
}
```

用字典把工具名和实际函数关联起来。

这样 LLM 返回 `"calculate"` 时，我们知道要调用 `calculate()` 函数。

### 第四部分：安全解析参数

```python
args = json.loads(tc.function.arguments)
result = available_functions[func_name](**args)
```

- `tc.function.arguments` 是 JSON 字符串，如 `'{"expression": "2+2"}'`
- `json.loads()` 把它转成字典
- `**args` 把字典展开为函数参数

**为什么不用 eval()？**
- `eval()` 会执行任意代码，不安全
- `json.loads()` 只解析 JSON，安全

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

## 运行效果

```
你: 现在几点了？
AI: 现在是 2026-07-24 15:30:45。

你: 计算 (3 + 5) * 12
AI: (3 + 5) * 12 = 96

你: 先告诉我现在几点，然后计算 100 * 2
AI: 现在是 15:31:00。100 * 2 = 200。
```

## 思考题

1. 为什么需要 `available_functions` 字典？
2. `json.loads()` 和 `eval()` 有什么区别？
3. 如果 LLM 调用一个不存在的工具会怎样？

## 下一步

[03-error-handling](../03-error-handling) - 添加错误处理，让 Agent 更健壮。
