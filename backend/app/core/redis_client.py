"""
One shared Redis connection pool for everything that needs cross-process
state: the OTP store, the rate limiter, and the tick-stream WS pub/sub.
"""
import redis
import redis.asyncio as aioredis

from app.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
async_redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
