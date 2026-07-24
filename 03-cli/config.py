import os
from dataclasses import dataclass


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
