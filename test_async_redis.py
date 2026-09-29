import asyncio
import redis.asyncio as redis


async def test_redis():
    r = redis.Redis.from_url(
        "redis://localhost:6379/0",
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    try:
        print("Testing async Redis connection...")

        result = await r.ping()

        print("ASYNC REDIS PING:", result)

        await r.set("bput_test_key", "hello")

        value = await r.get("bput_test_key")

        print("ASYNC REDIS GET:", value)

    except Exception as e:
        print("ASYNC REDIS ERROR:", repr(e))

    finally:
        await r.close()


asyncio.run(test_redis())