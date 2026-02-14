import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 1800):
        self.ttl = ttl_seconds
        self._store: dict[str, Any] = {}
        self._time: dict[str, float] = {}

    def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        if time.time() - self._time.get(key, 0) > self.ttl:
            self._store.pop(key, None)
            self._time.pop(key, None)
            return None
        return self._store[key]

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value
        self._time[key] = time.time()
