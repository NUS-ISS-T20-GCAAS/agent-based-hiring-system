import json
import logging
from typing import Any, Dict


class JsonLogger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)

        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(message)s")
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

    def info(self, event: str, **fields: Any) -> None:
        self._logger.info(self._format(event, fields))

    def error(self, event: str, **fields: Any) -> None:
        self._logger.error(self._format(event, fields))

    def _format(self, event: str, fields: Dict[str, Any]) -> str:
        payload = {"event": event, **fields}
        return json.dumps(payload, default=str)


def get_logger(name: str) -> JsonLogger:
    return JsonLogger(name)
