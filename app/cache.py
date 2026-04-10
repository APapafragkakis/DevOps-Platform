import json
import os
import logging
from typing import Optional

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "60"))

_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    global _client
    if _client is None:
        try:
            _client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
            _client.ping()
        except Exception as exc:
            logger.warning("redis unavailable, skipping cache", extra={"error": str(exc)})
            _client = None
    return _client


def cache_get(key: str) -> Optional[list]:
    client = get_redis()
    if client is None:
        return None
    try:
        value = client.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None


def cache_set(key: str, value: list, ttl: int = CACHE_TTL) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def cache_delete(key: str) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        # delete all keys with this prefix (e.g. items:all:0:10, items:all:0:20)
        for k in client.scan_iter(f"{key}*"):
            client.delete(k)
    except Exception:
        pass


def redis_ping() -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return client.ping()
    except Exception:
        return False

