from __future__ import annotations

import time
from dataclasses import dataclass

from django.core.cache import cache


class RateLimitExceeded(Exception):
    pass


@dataclass
class RateLimitRule:
    key: str
    limit: int
    window_seconds: int


def check_rate_limit(rule: RateLimitRule) -> None:
    cache_key = f"rl:{rule.key}"
    added = cache.add(cache_key, 0, timeout=rule.window_seconds)
    if added:
        cache.touch(cache_key, timeout=rule.window_seconds)
    try:
        current = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=rule.window_seconds)
        current = 1
    if current > rule.limit:
        raise RateLimitExceeded()


def build_rule(prefix: str, identifier: str, limit: int, window_seconds: int) -> RateLimitRule:
    key = f"{prefix}:{identifier}"
    return RateLimitRule(key=key, limit=limit, window_seconds=window_seconds)
