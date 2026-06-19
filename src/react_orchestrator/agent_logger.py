import logging
from pathlib import Path

from .settings import settings


log_levels_to_ints = {
    "NOTSET": logging.NOTSET,      # Value is 0
    "DEBUG": logging.DEBUG,        # Value is 10
    "INFO": logging.INFO,          # Value is 20
    "WARNING": logging.WARNING,    # Value is 30
    "ERROR": logging.ERROR,        # Value is 40
    "CRITICAL": logging.CRITICAL,  # Value is 50
}

log_level = log_levels_to_ints[settings.logging_level]

path = Path(settings.general_logs).resolve()

if not path.exists():
    path.mkdir(parents=True, exist_ok=True)


logging.basicConfig(
    filename= path / 'general_log.log',
    level= log_level,
    format= "%(asctime)s - [%(module)s] - [%(name)s]: %(levelname)s - %(message)s",
    )


