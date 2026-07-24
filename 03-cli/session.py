import json
import time
from pathlib import Path

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
