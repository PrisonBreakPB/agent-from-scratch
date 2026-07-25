import json
from openai import OpenAI

from tools import tools, available_functions
from context import ContextManager


class AgentLoop:
    def __init__(self, config):
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        self.model = config.model
        self.messages = [
            {"role": "system", "content": "你是一个有用的助手，可以使用工具来操作文件系统。"}
        ]
        self.max_steps = 10
        self.context = ContextManager(max_tokens=config.max_context_tokens)
        self.last_token_usage = 0  # 上一轮的精确 token 使用量

    def reset(self):
        """重置对话"""
        self.messages = [
            {"role": "system", "content": "你是一个有用的助手，可以使用工具来操作文件系统。"}
        ]

    def chat(self, user_input: str, on_token=None) -> str:
        """发送消息并获取回复

        Args:
            user_input: 用户输入
            on_token: 流式输出回调函数，接收一个 token 字符串
        """
        self.messages.append({"role": "user", "content": user_input})

        # 检查是否需要压缩上下文（用上一轮的精确值 + 本轮输入估算）
        estimated_new = len(user_input) // 3
        current_tokens = self.last_token_usage + estimated_new
        if current_tokens > self.context.max_tokens * 0.5:
            self.context.check_and_compress(self.messages, self.client)

        for step in range(self.max_steps):
            try:
                # 使用流式输出
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=tools,
                    stream=True,  # 启用流式输出
                    stream_options={"include_usage": True}  # 获取 token 使用量
                )
            except Exception as e:
                return f"API 调用失败: {e}"

            # 收集完整响应
            collected_tokens = []
            tool_calls = []
            final_content = ""

            for chunk in stream:
                # 处理文本内容
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    collected_tokens.append(token)
                    if on_token:
                        on_token(token)  # 调用回调函数

                # 处理工具调用
                if chunk.choices[0].delta.tool_calls:
                    for tc in chunk.choices[0].delta.tool_calls:
                        # 累积工具调用信息
                        while len(tool_calls) <= tc.index:
                            tool_calls.append({
                                "id": "",
                                "function": {"name": "", "arguments": ""}
                            })
                        if tc.id:
                            tool_calls[tc.index]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls[tc.index]["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments

                # 获取 token 使用量（最后一个 chunk 包含 usage）
                if hasattr(chunk, 'usage') and chunk.usage:
                    self.last_token_usage = chunk.usage.total_tokens

            # 组装完整内容
            final_content = "".join(collected_tokens)

            # 保存助手消息
            msg_dict = {"role": "assistant", "content": final_content}
            if tool_calls:
                msg_dict["tool_calls"] = tool_calls
            self.messages.append(msg_dict)

            # 如果没有工具调用，返回结果
            if not tool_calls:
                return final_content or "无响应内容"

            # 执行工具
            for tc in tool_calls:
                func_name = tc["function"]["name"]

                try:
                    args = json.loads(tc["function"]["arguments"])
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
                    "tool_call_id": tc["id"],
                    "content": str(result)
                })

        return "达到最大步数限制"
