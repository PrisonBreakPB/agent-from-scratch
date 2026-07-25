from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory

console = Console()


def create_repl(agent, config):
    """创建 REPL 循环"""
    console.print(Panel(
        f"[bold]Agent[/bold]\n"
        f"Model: [cyan]{config.model}[/cyan]\n"
        "Type [bold]/help[/bold] for commands, [bold]quit[/bold] to exit.",
        border_style="blue",
    ))

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

        # 未知命令
        if user_input.startswith("/"):
            console.print(f"[yellow]Unknown command: {user_input.split()[0]} (try /help)[/yellow]")
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
        "  /help      Show this help\n"
        "  /reset     Clear conversation history\n"
        "  /save      Save current session\n"
        "  /sessions  List saved sessions\n"
        "  quit       Exit",
        title="Help",
        border_style="dim",
    ))
