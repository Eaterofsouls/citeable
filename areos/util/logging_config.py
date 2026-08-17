import contextvars
import json
import logging
from datetime import UTC, datetime

_error_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_error_id_ctx", default=None
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ctx = getattr(record, "context", {})
        if record.exc_info:
            ctx["exc_info"] = self.formatException(record.exc_info)

        log_obj = {
            "timestamp": datetime.now(UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "error_id": _error_id_ctx.get(),
            "message": record.getMessage(),
            "context": ctx,
        }
        return json.dumps(log_obj)


def setup_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
