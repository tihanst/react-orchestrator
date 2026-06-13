from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings
from pathlib import Path



class Settings(BaseSettings):
    together_api_key: str
    tavily_api_key: str
    llm_model: str = Field(default=...)
    ask_tool_permissions: Literal['y', 'n'] = Field(default=...)
    parallel_tool_calls: Literal['y', 'n'] = Field(default=...)

    tavily_logs: str
    agent_response_logs: str

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
