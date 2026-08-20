from __future__ import annotations

from datetime import timedelta

from redis.asyncio import Redis

from app.infrastructure.caching.redis_cache import RedisCache
from app.infrastructure.caching.redis_idempotency_store import RedisIdempotencyStore


class TestRedisCache:
    async def test_set_then_get_round_trips_json_values(self, redis_client: Redis) -> None:
        cache = RedisCache(redis_client)

        await cache.set("greeting", {"hello": "world"})

        assert await cache.get("greeting") == {"hello": "world"}

    async def test_get_missing_key_returns_none(self, redis_client: Redis) -> None:
        cache = RedisCache(redis_client)

        assert await cache.get("missing") is None

    async def test_delete_removes_the_key(self, redis_client: Redis) -> None:
        cache = RedisCache(redis_client)
        await cache.set("k", 1)

        await cache.delete("k")

        assert await cache.exists("k") is False

    async def test_invalidate_prefix_removes_every_matching_key(self, redis_client: Redis) -> None:
        cache = RedisCache(redis_client)
        await cache.set("user:1:profile", "a")
        await cache.set("user:1:settings", "b")
        await cache.set("user:2:profile", "c")

        await cache.invalidate_prefix("user:1:")

        assert await cache.exists("user:1:profile") is False
        assert await cache.exists("user:1:settings") is False
        assert await cache.exists("user:2:profile") is True

    async def test_ttl_expires_the_key(self, redis_client: Redis) -> None:
        cache = RedisCache(redis_client)
        await cache.set("temp", "v", ttl_seconds=1)

        ttl = await redis_client.ttl("temp")

        assert 0 < ttl <= 1


class TestRedisIdempotencyStore:
    async def test_stores_and_retrieves_a_result_for_a_matching_fingerprint(
        self, redis_client: Redis
    ) -> None:
        store = RedisIdempotencyStore(redis_client)

        await store.store_result("key-1", "fp-1", {"id": 42}, ttl=timedelta(minutes=5))

        assert await store.get_cached_result("key-1", "fp-1") == {"id": 42}

    async def test_a_fingerprint_mismatch_is_treated_as_a_miss(self, redis_client: Redis) -> None:
        store = RedisIdempotencyStore(redis_client)
        await store.store_result("key-1", "fp-1", {"id": 42}, ttl=timedelta(minutes=5))

        assert await store.get_cached_result("key-1", "fp-2") is None

    async def test_lock_can_only_be_acquired_once_until_released(self, redis_client: Redis) -> None:
        store = RedisIdempotencyStore(redis_client)

        first = await store.try_acquire_lock("lock-1", ttl=timedelta(seconds=30))
        second = await store.try_acquire_lock("lock-1", ttl=timedelta(seconds=30))
        await store.release_lock("lock-1")
        third = await store.try_acquire_lock("lock-1", ttl=timedelta(seconds=30))

        assert first is True
        assert second is False
        assert third is True
