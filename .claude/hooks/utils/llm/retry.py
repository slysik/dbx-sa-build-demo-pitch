"""
Retry utility for LLM calls.

Lightweight decorator that retries failed LLM calls with backoff.
Designed for hook scripts where reliability matters but speed is critical.
"""

import time
from functools import wraps
from typing import TypeVar, Callable, Any

T = TypeVar("T")


def with_retry(max_attempts: int = 2, backoff: float = 1.0) -> Callable:
    """
    Retry decorator for LLM calls.

    Args:
        max_attempts: Maximum number of attempts (default 2 = 1 retry)
        backoff: Base delay in seconds between attempts (multiplied by attempt number)

    Returns:
        Decorated function that retries on failure

    Usage:
        @with_retry(max_attempts=2, backoff=1.0)
        def call_llm(prompt):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    if result is not None:
                        return result
                except Exception:
                    pass
                # Only sleep between attempts, not after the last one
                if attempt < max_attempts - 1:
                    time.sleep(backoff * (attempt + 1))
            return None

        return wrapper

    return decorator
