# Agent From Scratch

从零开始，一步一步搭建一个可用的 AI Agent。

## 适合谁？

- 想了解 Agent 原理的开发者
- 想自己动手做一个 Agent 的学习者
- 有 Python 基础，了解 OpenAI API 基本用法

## 项目结构

```
├── docs/          # 教程文档（分章节）
├── src/           # 完整的 agent 代码
├── run.bat        # 快速启动脚本
└── requirements.txt
```

## 前置准备

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
# 在 src/.env 文件中设置：
# OPENAI_API_KEY=your-key
# OPENAI_BASE_URL=your-base-url
# MODEL=your-model
```

## 运行方式

```bash
cd src
python main.py
```

或使用快捷脚本：

```bash
run.bat
```

## 章节列表

| 章节 | 内容 | 你将学到 |
|------|------|----------|
| [01 - 最小 Agent 循环](./docs/01-minimal-loop.md) | Agent 原理 | ReAct 范式、工具调用 |
| [02 - 工具系统](./docs/02-tools.md) | 工具实现 | Schema 定义、参数解析 |
| [03 - CLI 界面与流式输出](./docs/03-cli.md) | 命令行工具 | prompt_toolkit、rich、流式输出 |
| [04 - 上下文压缩](./docs/04-context-compression.md) | 长对话处理 | 三层压缩策略 |
| 05 - 多工具并行 | 待定 | 并行执行 |
| [06 - Hooks](./docs/06-hooks.md) | 扩展机制 | Hook 注册与触发 |

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

## 技术栈

- Python 3.13
- OpenAI SDK
- prompt_toolkit（输入）
- rich（输出）
