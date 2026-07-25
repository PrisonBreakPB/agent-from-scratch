# 03 - CLI 界面

## 目标

给 Agent 做一个好用的命令行界面。

**完成后你将学到：**
- 如何用 `rich` 美化输出
- 如何用 `prompt_toolkit` 提升输入体验
- 如何实现会话保存/恢复
- 如何处理命令行参数

## 开始之前

### 为什么用 CLI 而不是图形界面？

你可能会想，为什么不做一个 Web 界面或者桌面应用？

**CLI 的优势：**

1. **速度快**：不需要打开浏览器，直接在终端里用
2. **可组合**：可以和其他命令行工具配合，比如管道 `|`
3. **可脚本化**：可以用在自动化脚本里，比如 `python main.py -p "执行任务"`
4. **资源省**：不需要渲染 UI，占用资源很少
5. **开发者友好**：开发者本来就天天用终端，不用切换窗口

**实际上，主流的 AI 编程工具都是 CLI：**
- Claude Code（Anthropic 官方）
- GitHub Copilot CLI
- Cursor 的命令行模式

CLI 不是"简陋"，而是"高效"。

### 上一节我们学了什么

第二章我们实现了完整的工具系统：
- 6 个工具的实现
- 工具注册机制
- 参数解析

但运行方式还很原始：一个简单的 while 循环 + input()。

### 这一节我们要学什么

| 上一节 | 这一节（新增） |
|--------|---------------|
| 简单的 input() | prompt_toolkit（历史记录、多行输入） |
| print() | rich（Markdown渲染、彩色输出） |
| 无 | 会话保存/恢复 |
| 无 | 命令行参数 |
| 无 | 内置命令（/help, /reset等） |

### 项目结构

```
03-cli/
├── main.py              # 入口 + 命令行参数
├── cli.py               # REPL 界面
├── agent.py             # Agent 循环
├── session.py           # 会话保存/恢复
├── config.py            # 配置管理
└── tools/
    └── ...              # 工具（同第二章）
```

## 核心代码

### config.py - 配置管理

```python
@dataclass
class Config:
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            model=os.getenv("MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )
```

**作用：** 从环境变量读取配置，集中管理。

### session.py - 会话管理

```python
SESSIONS_DIR = Path.home() / ".agent" / "sessions"

def save_session(messages: list[dict], model: str) -> str:
    """保存会话到文件"""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session_id = f"session_{time.strftime('%Y%m%d_%H%M%S')}"
    data = {
        "id": session_id,
        "model": model,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "messages": messages,
    }
    path = SESSIONS_DIR / f"{session_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return session_id

def load_session(session_id: str) -> tuple[list[dict], str] | None:
    """加载会话"""
    path = SESSIONS_DIR / f"{session_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return data["messages"], data["model"]

def list_sessions() -> list[dict]:
    """列出所有会话"""
    if not SESSIONS_DIR.exists():
        return []
    sessions = []
    for f in sorted(SESSIONS_DIR.glob("*.json"), reverse=True):
        data = json.loads(f.read_text())
        sessions.append({
            "id": data["id"],
            "model": data["model"],
            "saved_at": data["saved_at"],
        })
    return sessions[:20]
```

**作用：** 保存和恢复对话历史。

### cli.py - REPL 界面

```python
console = Console()

def create_repl(agent, config):
    """创建 REPL 循环"""
    # 显示欢迎信息
    console.print(Panel(
        f"[bold]Agent[/bold]\n"
        f"Model: [cyan]{config.model}[/cyan]\n"
        "Type [bold]/help[/bold] for commands, [bold]quit[/bold] to exit.",
        border_style="blue",
    ))

    # 历史记录
    history = FileHistory("~/.agent_history")

    while True:
        try:
            # 输入（支持历史记录）
            user_input = prompt("You > ", history=history).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nBye!")
            break

        if not user_input:
            continue

        # 内置命令
        if user_input.lower() in ("quit", "exit"):
            break
        if user_input == "/help":
            _show_help()
            continue
        if user_input == "/reset":
            agent.reset()
            console.print("[yellow]Conversation reset.[/yellow]")
            continue

        # 调用 Agent
        try:
            response = agent.chat(user_input)
            console.print(Markdown(response))
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted.[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")

def _show_help():
    console.print(Panel(
        "[bold]Commands:[/bold]\n"
        "  /help    Show this help\n"
        "  /reset   Clear conversation history\n"
        "  quit     Exit",
        title="Help",
        border_style="dim",
    ))
```

**核心点：**
- `rich.Console`：彩色输出
- `rich.Markdown`：渲染 Markdown
- `prompt_toolkit.prompt`：带历史记录的输入
- 内置命令处理

### main.py - 入口

```python
def main():
    parser = argparse.ArgumentParser(description="AI Agent CLI")
    parser.add_argument("-m", "--model", help="Model name")
    parser.add_argument("-p", "--prompt", help="One-shot prompt")
    args = parser.parse_args()

    config = Config.from_env()
    if args.model:
        config.model = args.model

    # 创建 Agent
    from agent import AgentLoop
    agent = AgentLoop(config)

    # one-shot 模式
    if args.prompt:
        print(agent.chat(args.prompt))
        return

    # 交互模式
    create_repl(agent, config)

if __name__ == "__main__":
    main()
```

## 依赖安装

```bash
pip install rich prompt_toolkit
```

## 运行效果

```bash
# 交互模式
python main.py

# 指定模型
python main.py -m gpt-4o

# 单次执行
python main.py -p "列出当前目录的文件"
```

```
╭─── Agent ───╮
│ Model: gpt-4o-mini
│ Type /help for commands, quit to exit.
╰─────────────╯
You > 列出当前目录的文件
╭─ Response ──╮
│ 当前目录有以下文件：
│ - main.py
│ - agent.py
│ - tools/
╰─────────────╯
You > /help
╭─── Help ────╮
│ Commands:
│   /help    Show this help
│   /reset   Clear conversation history
│   quit     Exit
╰─────────────╯
You > bye!
```

## 下一步

[04-streaming](../04-streaming) - 流式输出，提升用户体验。
