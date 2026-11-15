from typing import Literal
from pydantic import Field, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# src/react_orchestrator/settings.py -> from the resolved path we have parents[0]=react_orchestrator, [1]=src, [2]=project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    together_api_key: str
    websearch_api_key: str
    llm_model: str = Field(default=...)
    llm_max_tokens: int = Field(default=...)
    ask_tool_permissions: Literal["y", "n"] = Field(default=...)
    parallel_tool_calls: Literal["y", "n"] = Field(default=...)
    use_telemetry: Literal["y", "n"] = Field(default=...)

    search_logs: str
    agent_response_logs: str
    general_logs: str
    logging_level: str
    research_reports_dir: str
    skills_dir: str

    @field_validator(
        "search_logs",
        "agent_response_logs",
        "general_logs",
        "research_reports_dir",
        "skills_dir",
    )
    @classmethod
    def anchor_paths_to_root(cls, value: str) -> str:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return str(path.resolve())

    @model_validator(mode="after")
    def check_permission_parallel_conflict(self) -> "Settings":
        if self.ask_tool_permissions == "y" and self.parallel_tool_calls == "y":
            raise ValueError(
                "parallel_tool_calls cannot be 'y' when ask_tool_permissions is 'y'"
            )
        return self

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"), extra="ignore"
    )


settings = Settings()


if __name__ == "__main__":
    print(Path(settings.skills_dir).resolve())
