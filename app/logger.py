import logging
import sys
from pythonjsonlogger import jsonlogger


def setup_logger(name: str = "app") -> logging.Logger:
    """Configures structured JSON logging directed to stdout."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(filename)s %(lineno)d"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False
    return logger
