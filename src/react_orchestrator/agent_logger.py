import logging
from pathlib import Path

from .settings import settings


log_levels_to_ints = {
    "NOTSET": logging.NOTSET,  # Value is 0
    "DEBUG": logging.DEBUG,  # Value is 10
    "INFO": logging.INFO,  # Value is 20
    "WARNING": logging.WARNING,  # Value is 30
    "ERROR": logging.ERROR,  # Value is 40
    "CRITICAL": logging.CRITICAL,  # Value is 50
}

log_level = log_levels_to_ints[settings.logging_level]


def ensure_log_dirs() -> None:
    for dir in (
        settings.general_logs,
        settings.search_logs,
        settings.agent_response_logs,
        settings.research_reports_dir,
        settings.skills_dir,
    ):
        Path(dir).expanduser().resolve().mkdir(parents=True, exist_ok=True)


def configure_logging(level: str | None = None, log_dir: str | None = None) -> None:
    ensure_log_dirs()

    root = logging.getLogger()
    if root.handlers:
        return

    path = Path(settings.general_logs).resolve()

    logging.basicConfig(
        filename=path / "general_log.log",
        level=log_level,
        format="%(asctime)s - [%(module)s] - [%(name)s]: %(levelname)s - %(message)s",
    )
