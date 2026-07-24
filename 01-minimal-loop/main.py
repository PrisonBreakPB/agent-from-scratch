from openai import OpenAI

client = OpenAI()
MAX_STEPS = 10

# 硬编码一个工具：获取当前时间
def get_time():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

tools = [{
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "获取当前时间",
        "parameters": {"type": "object", "properties": {}}
    }
}]

def react_loop(user_input: str) -> str:
    messages = [
        {"role": "system", "content": "你是一个有用的助手，可以使用工具来回答问题。"},
        {"role": "user", "content": user_input}
    ]

    for _ in range(MAX_STEPS):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools
        )

        msg = response.choices[0].message
        messages.append(msg)

        # 没有工具调用，返回最终回答
        if not msg.tool_calls:
            return msg.content

        # 执行工具
        for tc in msg.tool_calls:
            result = get_time()  # 硬编码调用
            messages.append({
                "tool_call_id": tc.id,
                "role": "tool",
                "content": result
            })

    return "达到最大步数限制"

if __name__ == "__main__":
    print("=== 01-minimal-loop ===")
    print("这是一个最小的 ReAct 循环，只有一个 get_time 工具")
    print("输入 exit 退出\n")

    while True:
        user_input = input("你: ").strip()
        if user_input.lower() in ["exit", "quit", "q"]:
            break
        if not user_input:
            continue
        print(f"\nAI: {react_loop(user_input)}\n")
