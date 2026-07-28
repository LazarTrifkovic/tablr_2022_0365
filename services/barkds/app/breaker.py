"""Circuit Breaker (Faza 4) — otpornost na pad/sporost nizvodnog servisa.

Tri stanja, kao Resilience4j:
- ZATVOREN (closed): pozivi prolaze; broji uzastopne greške.
- OTVOREN (open): posle `fail_max` grešaka prestaje da zove — odmah odbija poziv
  (bez pokušaja) narednih `reset_timeout` sekundi; ne davi već pali servis.
- POLU-OTVOREN (half_open): posle pauze pušta JEDAN probni poziv; uspeh → zatvoren,
  neuspeh → opet otvoren.
"""
import logging
import time
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger("breaker")

T = TypeVar("T")


class CircuitOpenError(Exception):
    """Prekidač je otvoren — poziv se odbija bez pokušaja."""


class CircuitBreaker:
    def __init__(self, name: str, fail_max: int = 3, reset_timeout: float = 10.0):
        self.name = name
        self.fail_max = fail_max          # koliko uzastopnih grešaka otvara prekidač
        self.reset_timeout = reset_timeout  # koliko sekundi ostaje otvoren pre probe
        self.failures = 0
        self.state = "closed"             # closed | open | half_open
        self._opened_at = 0.0

    def _can_attempt(self) -> bool:
        if self.state == "open":
            if time.monotonic() - self._opened_at >= self.reset_timeout:
                self.state = "half_open"   # vreme za probni poziv
                logger.info("Prekidač '%s' → POLU-OTVOREN (probni poziv)", self.name)
                return True
            return False
        return True  # closed ili half_open

    def _on_success(self) -> None:
        if self.state != "closed":
            logger.info("Prekidač '%s' → ZATVOREN (oporavak)", self.name)
        self.failures = 0
        self.state = "closed"

    def _on_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.fail_max and self.state != "open":
            self.state = "open"
            self._opened_at = time.monotonic()
            logger.warning("Prekidač '%s' → OTVOREN posle %d grešaka",
                           self.name, self.failures)

    async def call(self, fn: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """Izvrši async poziv kroz prekidač. Diže CircuitOpenError ako je otvoren."""
        if not self._can_attempt():
            raise CircuitOpenError(f"{self.name}: prekidač otvoren")
        try:
            result = await fn(*args, **kwargs)
        except Exception:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result
