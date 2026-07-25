import os
from pathlib import Path


def _load_dotenv():
    """加载 .env 文件"""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


class Config:
    def __init__(self):
        self.model = os.getenv("MODEL", "mimo-v2.5-pro")
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
        self.max_context_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", "128000"))

    @classmethod
    def from_env(cls) -> "Config":
        return cls()
