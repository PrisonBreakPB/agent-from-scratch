import json
from openai import OpenAI

from tools import tools, available_functions


class AgentLoop:
    def __init__(self, config):
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        self.model = config.model
        self.messages = [
            {"role": "system", "content": "你是一个有用的助手，可以使用工具来操作文件系统。"}
        ]
        self.max_steps = 10

    def reset(self):
        """重置对话"""
        self.messages = [
            {"role": "system", "content": "你是一个有用的助手，可以使用工具来操作文件系统。"}
        ]

    def chat(self, user_input: str) -> str:
        """发送消息并获取回复"""
        self.messages.append({"role": "user", "content": user_input})

        for step in range(self.max_steps):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=tools
                )
            except Exception as e:
                return f"API 调用失败: {e}"

            msg = response.choices[0].message
            self.messages.append(msg)

            if not msg.tool_calls:
                return msg.content or "无响应内容"

            for tc in msg.tool_calls:
                func_name = tc.function.name

                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                if func_name not in available_functions:
                    result = f"Error: 未知工具 {func_name}"
                else:
                    try:
                        result = available_functions[func_name](**args)
                    except Exception as e:
                        result = f"Error: {e}"

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result)
                })

        return "达到最大步数限制"
