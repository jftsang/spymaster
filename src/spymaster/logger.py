import logging
import os

logger = logging.getLogger("spymaster")
level = logging.DEBUG if os.environ.get("SPYMASTER_DEBUG") else logging.INFO
logger.setLevel(level)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)

logger.propagate = False
