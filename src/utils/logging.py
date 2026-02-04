"""Central logging utility.

TO USE:
from grtb.Utilites.logging import get_logger
log = get_logger(level="DEBUG")

Then log messages with:
log.info("Message here")

Available log levels:
log.debug(), log.info(), log.warning(), log.error(), log.critical()
"""

import ast
import atexit
import datetime as dt
import json
import logging
import logging.config
import logging.handlers
import pathlib
from typing import Any

# Limits
MAX_LOG_FILE_SIZE_MB = 2.5
MAX_LOG_FILE_BACKUPS = 5

# Make sure that the logs directory exists
__LOGS_DIR_PATH = pathlib.Path(__file__).parent.parent / "logs"
if not __LOGS_DIR_PATH.exists():
    __LOGS_DIR_PATH.mkdir(parents=True, exist_ok=True)

LOG_RECORD_BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}

LOGGER_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "{asctime:<23s} - {levelname:^7s} - {module} - {message}",
            "style": "{",
        },
        "json": {
            "()": "utils.logging.JSONFormatter",
            "fmt_keys": {
                "level": "levelname",
                "timestamp": "timestamp",
                "message": "message",
                "logger": "name",
                "pathname": "pathname",
                "module": "module",
                "function": "funcName",
                "line": "lineno",
                "thread_name": "threadName",
            },
        },
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "logfile": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": str(__LOGS_DIR_PATH / "app.jsonl"),
            "maxBytes": MAX_LOG_FILE_SIZE_MB * 1000000,
            "backupCount": MAX_LOG_FILE_BACKUPS,
            "encoding": "utf-8",
        },
        "queue_handler": {
            "class": "logging.handlers.QueueHandler",
            "handlers": [
                "logfile",
            ],
            "respect_handler_level": True,
        },
    },
    "loggers": {
        "root": {
            "handlers": ["stdout", "queue_handler"],
            "level": "DEBUG",
        },
    },
}


class JSONFormatter(logging.Formatter):
    """Class for formatting log messages as JSON."""

    def __init__(
        self,
        *,
        fmt_keys: dict[str, str] | None = None,
    ):
        super().__init__()
        self.fmt_keys = fmt_keys if fmt_keys is not None else {}

    # @override
    def format(self, record: logging.LogRecord) -> str:
        message = self._prepare_log_dict(record)
        return json.dumps(message, default=str)

    def _prepare_log_dict(self, record: logging.LogRecord):
        # In case the message is a multiline string, transform it into a single line
        formatted_message: str = ast.literal_eval(repr(record.getMessage()))

        formatted_message = "\\n ".join(
            [
                mess_split.strip()
                for mess_split in formatted_message.split("\n")
                if mess_split.strip() != ""
            ]
        )

        always_fields = {
            "message": formatted_message,
            "timestamp": dt.datetime.fromtimestamp(
                record.created, tz=dt.timezone.utc
            ).isoformat(),
        }
        if record.exc_info is not None:
            always_fields["exc_info"] = self.formatException(record.exc_info)

        if record.stack_info is not None:
            always_fields["stack_info"] = self.formatStack(record.stack_info)

        message = {
            key: (
                msg_val
                if (msg_val := always_fields.pop(val, None)) is not None
                else getattr(record, val)
            )
            for key, val in self.fmt_keys.items()
        }
        message.update(always_fields)

        for key, val in record.__dict__.items():
            if key not in LOG_RECORD_BUILTIN_ATTRS:
                message[key] = val

        return message


def get_logger(
    level: str | int = None,
    adjust_handler: dict[str, dict[Any, Any]] = None,
    **kwargs,
) -> logging.Logger:
    """Create logger.

    Args:
        level: Log level to set for the root logger. Defaults to None (config is set to ``WARNING``)
        adjust_handler: Dictionary to adjust handler parameters.
        **kwargs: Additional arguments for logging.getLogger().

    Returns:
        Configured logger instance.
    """
    if level:
        LOGGER_CONFIG["loggers"]["root"]["level"] = level

    if adjust_handler:
        for handler_name, params in adjust_handler.items():
            for param_key, param_val in params.items():
                LOGGER_CONFIG["handlers"][handler_name][param_key] = param_val

    # Configure logging
    logging.config.dictConfig(LOGGER_CONFIG)
    queue_handler: logging.handlers.QueueHandler = logging.getHandlerByName(
        "queue_handler"
    )
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)

    return logging.getLogger(**kwargs)
