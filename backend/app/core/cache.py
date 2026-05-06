from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Callable
from functools import wraps
from typing import Any


class TTLCache:
    def __init__(self, max_entries: int = 512) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._max_entries = max_entries

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() >= expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            if len(self._store) >= self._max_entries:
                oldest = min(self._store.items(), key=lambda item: item[1][1])
                del self._store[oldest[0]]
            self._store[key] = (value, time.time() + ttl_seconds)

    def invalidate(self, prefix: str = "") -> int:
        with self._lock:
            keys = [key for key in self._store if key.startswith(prefix)]
            for key in keys:
                del self._store[key]
            return len(keys)


_cache = TTLCache()


def cache_key(prefix: str, **params: Any) -> str:
    payload = json.dumps(params, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def cached(prefix: str, ttl_seconds: int = 600) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            key_params = {
                key: value
                for key, value in kwargs.items()
                if key not in {"db", "request", "response", "_"}
            }
            key = cache_key(f"{prefix}:{func.__name__}", **key_params)
            cached_value = _cache.get(key)
            if cached_value is not None:
                return cached_value
            result = func(*args, **kwargs)
            _cache.set(key, result, ttl_seconds)
            return result

        return wrapper

    return decorator


def invalidate_cache(prefix: str = "") -> int:
    return _cache.invalidate(prefix)
