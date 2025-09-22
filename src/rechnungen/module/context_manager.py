from contextlib import contextmanager

from loguru import logger


@contextmanager
def log_exceptions(msg, continue_on_error=True):
    try:
        yield
    except Exception as e:
        logger.error(f"{msg}: {e}")
        if not continue_on_error:
            raise
