"""Gateway circuit breakers — pybreaker instances for proxy routes.

Two circuit breaker instances:
- ``defaultCircuitBreaker``: applied to ALL proxy routes (fail_max=50, 60s reset).
- ``genaiCircuitBreaker``: additional breaker for GenAI route only (fail_max=5, 60s reset).

Mirrors the Java Resilience4j configuration where ``defaultCircuitBreaker`` is a
default gateway filter and ``genaiCircuitBreaker`` is an extra filter on the
``/api/genai/**`` route.

pybreaker's built-in ``call_async`` requires Tornado, so we provide
:func:`call_breaker_async` for asyncio compatibility.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

import pybreaker
from pybreaker import CircuitBreakerError

T = TypeVar("T")

# Default circuit breaker: applied to ALL proxy routes.
# fail_max=50 approximates Resilience4j's 50% failure threshold over 100 calls.
default_breaker = pybreaker.CircuitBreaker(
    fail_max=50,
    reset_timeout=60,
    name="defaultCircuitBreaker",
)

# GenAI-specific circuit breaker: lower threshold for faster failure detection.
# Excludes CircuitBreakerError so inner breaker failures don't double-count.
genai_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    name="genaiCircuitBreaker",
    exclude=[pybreaker.CircuitBreakerError],
)


def get_breakers(service: str) -> list[pybreaker.CircuitBreaker]:
    """Return the circuit breaker chain for the given service.

    All services use the default breaker. GenAI additionally uses a
    dedicated breaker with a lower failure threshold (outer wrapper).
    """
    if service == "genai":
        return [genai_breaker, default_breaker]
    return [default_breaker]


async def call_breaker_async(
    breaker: pybreaker.CircuitBreaker,
    func: Callable[[], Awaitable[T]],
) -> T:
    """Async-compatible circuit breaker call.

    pybreaker's built-in ``call_async`` requires Tornado coroutines.
    This reimplements the state machine for native asyncio:

    - **open** → raises :class:`CircuitBreakerError`
    - **closed / half-open** → awaits *func()*, records success or failure
    - On failure threshold → transitions to open
    - On half-open success → transitions to closed
    """
    if breaker.current_state == "open":
        raise CircuitBreakerError(breaker)

    try:
        result = await func()
    except BaseException as e:
        if breaker.is_system_error(e):
            breaker._inc_counter()  # noqa: SLF001
            if (
                breaker.current_state == "half_open"
                or breaker._state_storage.counter >= breaker.fail_max  # noqa: SLF001
            ):
                breaker.open()
        raise
    else:
        breaker._state_storage.reset_counter()  # noqa: SLF001
        if breaker.current_state == "half_open":
            breaker.close()
        return result
