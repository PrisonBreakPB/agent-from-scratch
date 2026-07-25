from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory

console = Console()


def create_repl(agent, config):
    """创建 REPL 循环"""
    # ASCII Art 欢迎信息
    console.print()
    console.print("[bold blue]   _                 _           [/bold blue]")
    console.print("[bold blue]  /_\\  _ __   __ _  | |_ ___  _ __  [/bold blue]")
    console.print("[bold cyan] //_\\\\| '_ \\ / _` | | __/ _ \\| '__| [/bold cyan]")
    console.print("[bold green]/  _  \\ |_) | (_| | | || (_) | |    [/bold green]")
    console.print("[bold yellow]\\_/ \\_/ .__/ \\__,_|  \\__\\___/|_|    [/bold yellow]")
    console.print("[bold yellow]      |_|                            [/bold yellow]")
    console.print()
    console.print(f"[bold]Model:[/bold] [cyan]{config.model}[/cyan]")
    console.print("[bold]Type[/bold] [cyan]/help[/cyan] [bold]for commands,[/bold] [cyan]quit[/cyan] [bold]to exit.[/bold]")
    console.print()

    # 历史记录
    history_path = Path.home() / ".agent_history"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history = FileHistory(str(history_path))

    while True:
        try:
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
        if user_input == "/save":
            from session import save_session
            sid = save_session(agent.messages, config.model)
            console.print(f"[green]Session saved: {sid}[/green]")
            continue
        if user_input == "/sessions":
            from session import list_sessions
            sessions = list_sessions()
            if not sessions:
                console.print("[dim]No saved sessions.[/dim]")
            else:
                for s in sessions:
                    console.print(f"  [cyan]{s['id']}[/cyan] ({s['model']}, {s['saved_at']})")
            continue
        if user_input == "/compact":
            from context import estimate_tokens
            before = estimate_tokens(agent.messages)
            agent.context.check_and_compress(agent.messages, agent.client)
            after = estimate_tokens(agent.messages)
            console.print(f"[green]Compressed: {before} → {after} tokens[/green]")
            continue

        # 未知命令
        if user_input.startswith("/"):
            console.print(f"[yellow]Unknown command: {user_input.split()[0]} (try /help)[/yellow]")
            continue

        # 调用 Agent（流式输出）
        try:
            streamed = []

            def on_token(token):
                streamed.append(token)
                print(token, end="", flush=True)

            response = agent.chat(user_input, on_token=on_token)

            # 如果有流式输出，打印换行
            if streamed:
                print()
            else:
                # 没有流式输出（工具调用后返回），用 Markdown 渲染
                console.print(Markdown(response))
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted.[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")


def _show_help():
    """显示帮助信息"""
    console.print(Panel(
        "[bold]Commands:[/bold]\n"
        "  /help      Show this help\n"
        "  /reset     Clear conversation history\n"
        "  /compact   Compress conversation context\n"
        "  /save      Save current session\n"
        "  /sessions  List saved sessions\n"
        "  quit       Exit",
        title="Help",
        border_style="dim",
    ))
