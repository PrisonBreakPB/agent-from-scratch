import json
from datetime import datetime
from openai import OpenAI

client = OpenAI()
MAX_STEPS = 10

# ========== 工具实现 ==========

def get_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculate(expression: str) -> str:
    try:
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expression):
            return "Error: 只允许数字和 +-*/(). 运算符"
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"

# ========== 工具注册 ==========

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

available_functions = {"get_time": get_time, "calculate": calculate}

# ========== Agent 循环 ==========

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

# ========== CLI 入口 ==========

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
