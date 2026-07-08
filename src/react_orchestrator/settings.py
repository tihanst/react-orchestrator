from typing import Literal
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings
from pathlib import Path



class Settings(BaseSettings):
    together_api_key: str
    websearch_api_key: str
    llm_model: str = Field(default=...)
    llm_max_tokens: int = Field(default=...)
    ask_tool_permissions: Literal['y', 'n'] = Field(default=...)
    parallel_tool_calls: Literal['y', 'n'] = Field(default=...)
    use_telemetry: Literal['y', 'n'] = Field(default=...)

    search_logs: str
    agent_response_logs: str
    general_logs: str
    logging_level: str

    @model_validator(mode='after')
    def check_permission_parallel_conflict(self) -> 'Settings':
        if self.ask_tool_permissions == 'y' and self.parallel_tool_calls == 'y':
            raise ValueError("parallel_tool_calls cannot be 'y' when ask_tool_permissions is 'y'")
        return self


    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        extra = 'ignore'


settings = Settings()