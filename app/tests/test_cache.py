import os
import sys

import fakeredis
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import cache


@pytest.fixture
def fake_redis(monkeypatch):
    client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(cache, "_client", client)
    return client


@pytest.fixture
def no_redis(monkeypatch):
    def broken_from_url(*args, **kwargs):
        raise ConnectionError("redis is down")

    monkeypatch.setattr(cache, "_client", None)
    monkeypatch.setattr(cache.redis, "from_url", broken_from_url)


def test_set_and_get(fake_redis):
    cache.cache_set("items:all:0:10", [{"id": 1}])
    assert cache.cache_get("items:all:0:10") == [{"id": 1}]


def test_get_missing_key(fake_redis):
    assert cache.cache_get("nope") is None


def test_set_uses_ttl(fake_redis):
    cache.cache_set("k", [1], ttl=30)
    assert 0 < fake_redis.ttl("k") <= 30


def test_delete_removes_all_keys_with_prefix(fake_redis):
    cache.cache_set("items:all:0:10", [1])
    cache.cache_set("items:all:10:10", [2])
    cache.cache_set("other", [3])

    cache.cache_delete("items:all")

    assert cache.cache_get("items:all:0:10") is None
    assert cache.cache_get("items:all:10:10") is None
    assert cache.cache_get("other") == [3]


def test_ping(fake_redis):
    assert cache.redis_ping() is True


def test_redis_down_is_not_fatal(no_redis):
    assert cache.get_redis() is None
    assert cache.cache_get("k") is None
    cache.cache_set("k", [1])
    cache.cache_delete("k")
    assert cache.redis_ping() is False
