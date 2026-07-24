# Agent From Scratch

从零开始，一步一步搭建一个可用的 AI Agent。

## 适合谁？

- 想了解 Agent 原理的开发者
- 想自己动手做一个 Agent 的学习者
- 有 Python 基础，了解 OpenAI API 基本用法

## 前置准备

```bash
# 1. 安装依赖
pip install openai

# 2. 设置 API Key
export OPENAI_API_KEY="your-key"
```

## 章节列表

| 章节 | 内目 | 你将学到 |
|------|------|----------|
| [01-minimal-loop](./01-minimal-loop) | 最小 Agent 循环 | Agent 的核心原理 |
| 02-add-tools | 工具系统 | 如何让 Agent 使用工具 |
| 03-error-handling | 错误处理 | 让 Agent 更健壮 |
| 04-cli-interface | CLI 交互 | 做一个真正可用的命令行工具 |
| 05-streaming | 流式输出 | 提升用户体验 |
| 06-memory | 上下文记忆 | 让 Agent 记住对话 |
| 07-multi-tool | 多工具协作 | 复杂任务分解 |

## 核心概念

### Agent 的工作方式

```
用户问题 → [思考] → [调用工具] → [获取结果] → [思考] → [调用工具] → ... → 最终回答
```

### 为什么需要循环？

LLM 本身不能执行代码，只能"说"要做什么。真正的执行需要我们来完成：

1. LLM 说："我想调用 get_time 工具"
2. 我们执行 get_time，得到结果
3. 把结果告诉 LLM
4. LLM 根据结果决定下一步

这就是为什么需要 while 循环。
