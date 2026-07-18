import logging
import sys

from config import LOG_LEVEL, LOG_FORMAT

_configured = False


def configure_logger() -> None:
    """Configure the root logger for the package."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    if not root.handlers:
        root.addHandler(handler)

    _configured = True


def get_logger(nome: str) -> logging.Logger:
    """ Get a logger for the package """
    configure_logger()
    return logging.getLogger(nome)
