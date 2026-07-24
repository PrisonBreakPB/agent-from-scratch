import re
import subprocess

# 危险命令模式
DANGEROUS_PATTERNS = [
    r'\brm\s+(-[a-zA-Z]*r|--recursive)',  # rm -r, rm -rf
    r'\brmdir\b',                          # rmdir
    r'\bmkfs\b',                           # mkfs
    r'\bdd\b.*of=/dev/',                   # dd of=/dev/...
    r'\bformat\b',                         # format
    r'>\s*/dev/',                          # 重定向到设备
    r'\bshutdown\b',                       # shutdown
    r'\breboot\b',                         # reboot
    r'\binit\s+0\b',                       # init 0
    r'\bkill\s+-9\s+1\b',                  # kill -9 1
    r':\(\)\{.*\|.*&\}',                   # fork bomb
]

def bash(command: str) -> str:
    """执行 bash 命令，会检查危险命令"""
    # 检查危险命令
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return f"Error: 检测到危险命令，拒绝执行: {command}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"
