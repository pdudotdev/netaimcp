"""Structured logging configuration for aiNOC.

Provides a JSONFormatter and two setup functions:
  setup_logging()          — configures the 'ainoc' logger hierarchy for any process
  setup_watcher_logging()  — extends setup_logging() with a rotating file handler
                             on ainoc.watcher for the on-call watcher process

Environment variables:
  LOG_LEVEL   DEBUG | INFO | WARNING | ERROR   (default: INFO)
  LOG_FORMAT  json | text                       (default: json)
"""
import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Standard LogRecord attributes that should NOT be forwarded as extra JSON fields.
_STANDARD_ATTRS = frozenset({
    "args", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "message", "module", "msecs", "msg",
    "name", "pathname", "process", "processName", "relativeCreated",
    "stack_info", "taskName", "thread", "threadName",
})


class JSONFormatter(logging.Formatter):
    """Emit one JSON object per log record — friendly for log-aggregation pipelines."""

    def format(self, record: logging.LogRecord) -> str:
        ts = (
            datetime.fromtimestamp(record.created, tz=timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        )
        entry: dict = {
            "ts":     ts,
            "level":  record.levelname,
            "logger": record.name,
            "msg":    record.getMessage(),
        }
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        # Forward any extra fields added via logging.info("...", extra={...})
        for key, val in record.__dict__.items():
            if key not in _STANDARD_ATTRS:
                entry[key] = val
        return json.dumps(entry)


def _make_formatter() -> logging.Formatter:
    fmt = os.getenv("LOG_FORMAT", "text").lower()
    if fmt == "json":
        return JSONFormatter()
    return logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s")


def setup_logging() -> None:
    """Configure the 'ainoc' logger hierarchy with a stderr handler.

    Idempotent — safe to call multiple times; handlers are only added once.
    Respects LOG_LEVEL and LOG_FORMAT environment variables.
    """
    root = logging.getLogger("ainoc")
    if root.handlers:
        return  # Already configured

    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    root.setLevel(level)
    root.propagate = False

    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(_make_formatter())
    root.addHandler(sh)



def setup_watcher_logging(log_file: Path) -> None:
    """Extend setup_logging() with a rotating file handler on ainoc.watcher.

    The file handler captures DEBUG and above so that console=False-style
    messages (logged at DEBUG) go to file only, while INFO+ appears on stderr.

    Args:
        log_file: Path to the watcher log file (e.g. oncall_watcher.log).
    """
    setup_logging()  # Ensure ainoc logger is configured with stderr handler

    watcher_log = logging.getLogger("ainoc.watcher")

    # Avoid adding a second file handler if already set up (e.g. in tests)
    if any(isinstance(h, RotatingFileHandler) for h in watcher_log.handlers):
        return

    log_file.parent.mkdir(parents=True, exist_ok=True)
    fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=3)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(JSONFormatter())
    watcher_log.addHandler(fh)
