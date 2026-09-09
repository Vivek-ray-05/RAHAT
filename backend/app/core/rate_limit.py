"""
Rate limiting for auth endpoints -- the ones most worth protecting
against brute force (password/OTP guessing) and SMS-bombing (OTP
request spam). Counters live in Redis (via slowapi/limits' Redis
storage backend), keyed by client IP -- shared across every backend
worker/container, so a client can't dodge the limit just by getting
routed to a different process.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)
