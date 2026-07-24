import os
import re
import subprocess
import threading

# 跟踪工作目录（cd 命令感知）
_local = threading.local()

# 危险命令模式
DANGEROUS_PATTERNS = [
    (r"\brm\s+(-\w*)?-r\w*\s+(/|~|\$HOME)", "递归删除根目录/主目录"),
    (r"\brm\b(?=(?:.*\s)?-\w*[rR])(?=(?:.*\s)?-\w*f)", "强制递归删除"),
    (r"\bmkfs\b", "格式化文件系统"),
    (r"\bdd\s+.*of=/dev/", "写入磁盘设备"),
    (r">\s*/dev/sd[a-z]", "覆盖块设备"),
    (r"\bchmod\s+(-R\s+)?777\s+/", "chmod 777 on root"),
    (r":\(\)\s*\{.*:\|:.*\}", "fork bomb"),
    (r"\bcurl\b.*\|\s*(sudo\s+)?(ba)?sh\b", "curl 管道到 shell"),
    (r"\bwget\b.*\|\s*(sudo\s+)?(ba)?sh\b", "wget 管道到 shell"),
]

def bash(command: str, timeout: int = 120) -> str:
    """执行 bash 命令，会检查危险命令"""
    # 检查危险命令
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return f"Error: 检测到危险命令 ({reason})，拒绝执行: {command}"

    # 使用跟踪的工作目录
    cwd = getattr(_local, "cwd", None) or os.getcwd()

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=cwd,
        )

        # 跟踪 cd 命令
        if result.returncode == 0:
            _update_cwd(command, cwd)

        out = result.stdout
        if result.stderr:
            out += f"\n[stderr]\n{result.stderr}"
        if result.returncode != 0:
            out += f"\n[exit code: {result.returncode}]"

        # 输出截断（保留头尾）
        if len(out) > 15_000:
            out = (
                out[:6000]
                + f"\n\n... truncated ({len(out)} chars total) ...\n\n"
                + out[-3000:]
            )

        return out.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"

def _update_cwd(command: str, current_cwd: str):
    """跟踪 cd 命令，更新工作目录"""
    running = current_cwd
    changed = False
    for part in command.split("&&"):
        part = part.strip()
        if part.startswith("cd "):
            target = part[3:].strip().strip("'\"")
            if target:
                new_dir = os.path.normpath(os.path.join(running, os.path.expanduser(target)))
                if os.path.isdir(new_dir):
                    running = new_dir
                    changed = True
    if changed:
        _local.cwd = running
