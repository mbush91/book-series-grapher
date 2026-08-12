from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ThinkingLevel = Literal["minimal", "low", "medium", "high", "xhigh"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    database_url: str = "postgresql+asyncpg://bookgraph:bookgraph@db:5432/bookgraph"
    mcp_url: str = "http://mcp:8001/mcp"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8001
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_name: str = "openai:gpt-5.6-sol"
    model_effort: ThinkingLevel = "medium"
    extraction_model_name: str | None = None
    extraction_model_effort: ThinkingLevel | None = None

    upload_max_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    extraction_concurrency: int = Field(default=1, ge=1, le=8)

    def agent_model_settings(self, *, extraction: bool = False) -> dict[str, str]:
        effort = self.extraction_model_effort if extraction and self.extraction_model_effort else self.model_effort
        return {"thinking": effort}

    def agent_model_name(self, *, extraction: bool = False) -> str:
        return self.extraction_model_name if extraction and self.extraction_model_name else self.model_name
