"""Shared slowapi Limiter instance, keyed by client IP. A single instance is
imported by main.py (to wire up the middleware/exception handler) and by any
route module that needs a stricter per-endpoint limit than the default."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
