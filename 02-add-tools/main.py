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

# Schema 定义：告诉 LLM 有哪些工具可用
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

# 函数映射：根据名字调用对应函数
available_functions = {
    "get_time": get_time,
    "calculate": calculate
}

# ========== Agent 循环 ==========

def agent_loop(user_input: str) -> str:
    messages = [
        {"role": "system", "content": "你是一个有用的助手，可以使用工具来回答问题。"},
        {"role": "user", "content": user_input}
    ]

    for step in range(MAX_STEPS):
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

        if not msg.tool_calls:
            return msg.content or "无响应内容"

        # 处理工具调用
        for tc in msg.tool_calls:
            func_name = tc.function.name

            # 安全解析参数
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            # 查找并执行工具
            if func_name not in available_functions:
                result = f"Error: 未知工具 {func_name}"
            else:
                try:
                    result = available_functions[func_name](**args)
                except Exception as e:
                    result = f"Error: {e}"

            # 把结果放回消息
            messages.append({
                "tool_call_id": tc.id,
                "role": "tool",
                "content": str(result)
            })

    return "达到最大步数限制"

# ========== CLI 入口 ==========

if __name__ == "__main__":
    print("=== 02-add-tools ===")
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
