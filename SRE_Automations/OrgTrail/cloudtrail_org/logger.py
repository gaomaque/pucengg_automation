import logging
import logging.config

LOGGER_NAME = __name__.split(".")[0]

logger = logging.getLogger(LOGGER_NAME)


def setup_logger(level=logging.DEBUG, console=True):
    handlers = []
    if console:
        handlers.append("console")

    config = {
        "version": 1,
        "formatters": {
            "console": {
                "format": (
                    "%(asctime)s | %(levelname)s | %(message)s | "
                    "%(module)s.%(funcName)s:%(lineno)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {"console": {"()": logging.StreamHandler, "formatter": "console"}},
        "loggers": {LOGGER_NAME: {"level": level}},
        "root": {"handlers": handlers},
    }
    logging.config.dictConfig(config)
