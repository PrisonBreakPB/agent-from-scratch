import argparse
from config import Config


def main():
    parser = argparse.ArgumentParser(description="AI Agent CLI")
    parser.add_argument("-m", "--model", help="Model name")
    parser.add_argument("-p", "--prompt", help="One-shot prompt (non-interactive)")
    parser.add_argument("-r", "--resume", metavar="ID", help="Resume a saved session")
    args = parser.parse_args()

    config = Config.from_env()
    if args.model:
        config.model = args.model

    # 创建 Agent
    from agent import AgentLoop
    agent = AgentLoop(config)

    # 恢复会话
    if args.resume:
        from session import load_session
        loaded = load_session(args.resume)
        if loaded:
            agent.messages, saved_model = loaded
            if not args.model:
                config.model = saved_model
            print(f"Resumed session: {args.resume}")
        else:
            print(f"Session '{args.resume}' not found.")
            return

    # one-shot 模式
    if args.prompt:
        print(agent.chat(args.prompt))
        return

    # 交互模式
    from cli import create_repl
    create_repl(agent, config)


if __name__ == "__main__":
    main()
