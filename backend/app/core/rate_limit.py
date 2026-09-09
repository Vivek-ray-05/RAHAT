"""
Rate limiting for auth endpoints -- the ones most worth protecting
against brute force (password/OTP guessing) and SMS-bombing (OTP
request spam). In-memory, keyed by client IP: fine for a single
backend worker, same tradeoff as the OTP store and per-run engine
caches elsewhere in this codebase. Move to a Redis backend if/when
this ever runs multi-worker.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
