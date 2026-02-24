from typing import Dict, List


class SharedMemory:
    def __init__(self):
        self._store: List[Dict] = []

    def append(self, artifact: Dict) -> None:
        self._store.append(artifact)

    def get_by_entity(self, entity_id: str) -> List[Dict]:
        return [a for a in self._store if a["entity_id"] == entity_id]

    def all(self) -> List[Dict]:
        return list(self._store)
