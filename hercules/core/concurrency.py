"""
Concurrency manager for Hercules MCP tools.

Uses asyncio.Semaphore with acquisition timeouts to enforce limits
on parallel tool execution. Heavy operations (aggressive nmap scans,
large sqlmap runs, brute-force attacks) share a smaller semaphore
pool, while light operations (searchsploit queries, quick scans)
share a larger one.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager

logger = logging.getLogger("hercules.concurrency")


class ConcurrencyManager:
    """
    Semaphore-based concurrency controller with timeouts and active counts.

    Heavy jobs: limited pool (default 3), 30s acquisition timeout.
    Light jobs: larger pool (default 10), 10s acquisition timeout.
    """

    def __init__(
        self,
        max_heavy: int = 3,
        max_light: int = 10,
        heavy_timeout: float = 30.0,
        light_timeout: float = 10.0,
    ) -> None:
        self._semaphores = {
            "heavy": asyncio.Semaphore(max_heavy),
            "light": asyncio.Semaphore(max_light),
        }
        self._timeouts = {"heavy": heavy_timeout, "light": light_timeout}
        self._active = {"heavy": 0, "light": 0}

        logger.info(
            "ConcurrencyManager initialized: max_heavy=%d, max_light=%d",
            max_heavy,
            max_light,
        )

    def acquire_heavy(self, tool_name: str) -> AbstractAsyncContextManager[str]:
        """Acquire a heavy-job slot or raise RuntimeError on timeout."""
        return self._acquire("heavy", tool_name)

    def acquire_light(self, tool_name: str) -> AbstractAsyncContextManager[str]:
        """Acquire a light-job slot or raise RuntimeError on timeout."""
        return self._acquire("light", tool_name)

    @asynccontextmanager
    async def _acquire(self, kind: str, tool_name: str) -> AsyncIterator[str]:
        semaphore = self._semaphores[kind]
        job_id = f"{tool_name}-{uuid.uuid4().hex[:6]}"
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=self._timeouts[kind])
        except TimeoutError:
            logger.warning(
                "%s concurrency limit reached: %s could not be scheduled.",
                kind.capitalize(),
                tool_name,
            )
            raise RuntimeError(
                f"Concurrency limit reached: cannot schedule '{tool_name}' ({kind}). "
                f"Currently active: {self._active[kind]} {kind} jobs."
            )

        self._active[kind] += 1
        try:
            logger.debug("Acquired %s slot: %s (%s)", kind, tool_name, job_id)
            yield job_id
        finally:
            semaphore.release()
            self._active[kind] -= 1
            logger.debug("Released %s slot: %s (%s)", kind, tool_name, job_id)
