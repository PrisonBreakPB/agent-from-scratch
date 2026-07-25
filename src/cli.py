def create_repl(agent, config):
    """创建 REPL 循环"""
    print("=" * 50)
    print("Agent")
    print(f"Model: {config.model}")
    print("Type /help for commands, quit to exit.")
    print("=" * 50)

    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
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
            print("Conversation reset.")
            continue
        if user_input == "/save":
            from session import save_session
            sid = save_session(agent.messages, config.model)
            print(f"Session saved: {sid}")
            continue
        if user_input == "/sessions":
            from session import list_sessions
            sessions = list_sessions()
            if not sessions:
                print("No saved sessions.")
            else:
                for s in sessions:
                    print(f"  {s['id']} ({s['model']}, {s['saved_at']})")
            continue

        # 未知命令
        if user_input.startswith("/"):
            print(f"Unknown command: {user_input.split()[0]} (try /help)")
            continue

        # 调用 Agent
        try:
            response = agent.chat(user_input)
            print(response)
        except KeyboardInterrupt:
            print("\nInterrupted.")
        except Exception as e:
            print(f"\nError: {e}")


def _show_help():
    print("=" * 50)
    print("Commands:")
    print("  /help      Show this help")
    print("  /reset     Clear conversation history")
    print("  /save      Save current session")
    print("  /sessions  List saved sessions")
    print("  quit       Exit")
    print("=" * 50)
