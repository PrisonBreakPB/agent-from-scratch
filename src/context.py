"""上下文压缩模块

三层压缩策略：
- Layer 1：截断冗长的工具输出
- Layer 2：LLM 总结旧对话
- Layer 3：只保留摘要和最近消息
"""


def estimate_tokens(messages):
    """估算 token 数量（粗略：3字符 ≈ 1token）"""
    total = 0
    for m in messages:
        if m.get("content"):
            total += len(m["content"]) // 3
        if m.get("tool_calls"):
            total += len(str(m["tool_calls"])) // 3
    return total


class ContextManager:
    def __init__(self, max_tokens=128000):
        self.max_tokens = max_tokens
        self._snip_at = int(max_tokens * 0.50)  # 50% 截断工具输出
        self._summarize_at = int(max_tokens * 0.70)  # 70% LLM 总结
        self._collapse_at = int(max_tokens * 0.90)  # 90% 硬压缩

    def maybe_compress(self, messages, llm_client=None):
        """检查是否需要压缩，执行压缩"""
        current = estimate_tokens(messages)
        compressed = False

        # Layer 1: 截断工具输出
        if current > self._snip_at:
            if self._snip_tool_outputs(messages):
                compressed = True
                current = estimate_tokens(messages)

        # Layer 2: LLM 总结
        if current > self._summarize_at and len(messages) > 10:
            if self._summarize_old(messages, llm_client):
                compressed = True
                current = estimate_tokens(messages)

        # Layer 3: 硬压缩
        if current > self._collapse_at and len(messages) > 4:
            self._hard_collapse(messages, llm_client)
            compressed = True

        return compressed

    @staticmethod
    def _snip_tool_outputs(messages):
        """Layer 1: 截断冗长的工具输出"""
        changed = False
        for m in messages:
            if m.get("role") != "tool":
                continue
            content = m.get("content", "")
            if len(content) <= 1500:
                continue
            lines = content.splitlines()
            if len(lines) <= 6:
                continue
            # 保留前3行和后3行
            snipped = (
                "\n".join(lines[:3])
                + f"\n... ({len(lines)} lines, snipped to save context) ...\n"
                + "\n".join(lines[-3:])
            )
            m["content"] = snipped
            changed = True
        return changed

    def _summarize_old(self, messages, llm_client, keep_recent=8):
        """Layer 2: LLM 总结旧对话"""
        if len(messages) <= keep_recent:
            return False

        # 找到安全的分割点（不分离 tool 和 tool_call）
        split = max(0, len(messages) - keep_recent)
        while split > 0 and messages[split].get("role") == "tool":
            split -= 1

        old = messages[:split]
        tail = messages[split:]

        summary = self._get_summary(old, llm_client)

        messages.clear()
        messages.append({
            "role": "user",
            "content": f"[Context compressed - conversation summary]\n{summary}"
        })
        messages.append({
            "role": "assistant",
            "content": "Got it, I have the context from our earlier conversation."
        })
        messages.extend(tail)
        return True

    def _hard_collapse(self, messages, llm_client):
        """Layer 3: 硬压缩，只保留摘要和最近4条消息"""
        split = max(0, len(messages) - 4)
        while split > 0 and messages[split].get("role") == "tool":
            split -= 1

        tail = messages[split:]
        summary = self._get_summary(messages[:split], llm_client)

        messages.clear()
        messages.append({
            "role": "user",
            "content": f"[Hard context reset]\n{summary}"
        })
        messages.append({
            "role": "assistant",
            "content": "Context restored. Continuing from where we left off."
        })
        messages.extend(tail)

    def _get_summary(self, messages, llm_client):
        """生成摘要"""
        if llm_client:
            try:
                flat = self._flatten(messages)
                response = llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Compress this conversation into a brief summary. "
                                "Preserve: file paths edited, key decisions made, "
                                "errors encountered, current task state. "
                                "Drop: verbose command output, code listings, "
                                "redundant back-and-forth."
                            )
                        },
                        {"role": "user", "content": flat[:15000]}
                    ]
                )
                return response.choices[0].message.content
            except Exception:
                pass

        # Fallback: 提取关键信息
        return self._extract_key_info(messages)

    @staticmethod
    def _flatten(messages):
        """把消息列表转成文本"""
        parts = []
        for m in messages:
            role = m.get("role", "?")
            text = m.get("content", "") or ""
            if text:
                parts.append(f"[{role}] {text[:400]}")
        return "\n".join(parts)

    @staticmethod
    def _extract_key_info(messages):
        """提取关键信息（不依赖 LLM）"""
        import re
        files = set()
        errors = []

        for m in messages:
            text = m.get("content", "") or ""
            # 提取文件路径
            for match in re.finditer(r'[\w./\-]+\.\w{1,5}', text):
                files.add(match.group())
            # 提取错误信息
            for line in text.splitlines():
                if "error" in line.lower():
                    errors.append(line.strip()[:150])

        parts = []
        if files:
            parts.append(f"Files: {', '.join(sorted(files)[:20])}")
        if errors:
            parts.append(f"Errors: {'; '.join(errors[:5])}")
        return "\n".join(parts) or "(no context)"
