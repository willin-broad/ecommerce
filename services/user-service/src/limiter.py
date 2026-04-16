import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Read from env so tests can set RATELIMIT_ENABLED=false before importing this module
_enabled = os.getenv("RATELIMIT_ENABLED", "true").lower() not in ("false", "0", "no")

limiter = Limiter(key_func=get_remote_address, enabled=_enabled)
