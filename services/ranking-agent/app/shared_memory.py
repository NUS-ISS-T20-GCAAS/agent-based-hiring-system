from threading import Lock
from typing import Dict, List


class SharedMemory:
    def __init__(self):
        self._store: List[Dict] = []
        self._lock = Lock()

    def append(self, artifact: Dict) -> None:
        with self._lock:
            self._store.append(artifact)

    def get_by_entity(self, entity_id: str) -> List[Dict]:
        with self._lock:
            return [artifact for artifact in self._store if artifact["entity_id"] == entity_id]

    def all(self) -> List[Dict]:
        with self._lock:
            return list(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
