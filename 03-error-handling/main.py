from agent import agent_loop

if __name__ == "__main__":
    print("=== Agent with File Tools ===")
    print("支持工具：bash, read_file, write_file, edit_file, glob, grep")
    print("输入 exit 退出\n")

    while True:
        try:
            user_input = input("你: ").strip()
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            if not user_input:
                continue
            print(f"\nAI: {agent_loop(user_input)}\n")
        except KeyboardInterrupt:
            print("\n再见！")
            break
