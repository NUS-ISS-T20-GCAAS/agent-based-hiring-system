import json
import logging
from typing import Any, Dict

from app.config import LOG_LEVEL


class JsonLogger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

        self._logger.propagate = False

    def info(self, event: str, **fields: Any) -> None:
        self._logger.info(self._format(event, fields))

    def error(self, event: str, **fields: Any) -> None:
        self._logger.error(self._format(event, fields))

    def _format(self, event: str, fields: Dict[str, Any]) -> str:
        return json.dumps({"event": event, **fields}, default=str)


def get_logger(name: str) -> JsonLogger:
    return JsonLogger(name)
