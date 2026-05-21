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
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

logger = logging.getLogger("hercules.concurrency")


class ConcurrencyManager:
    """
    Semaphore-based concurrency controller with timeout and job tracking.

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
        self._heavy_sem = asyncio.Semaphore(max_heavy)
        self._light_sem = asyncio.Semaphore(max_light)
        self._heavy_timeout = heavy_timeout
        self._light_timeout = light_timeout
        self._active: dict[str, dict] = {}

        logger.info(
            "ConcurrencyManager initialized: max_heavy=%d, max_light=%d",
            max_heavy,
            max_light,
        )

    @asynccontextmanager
    async def acquire_heavy(self, tool_name: str) -> AsyncIterator[str]:
        """
        Acquire a heavy-job slot. Raises RuntimeError if the semaphore
        cannot be acquired within the timeout.
        """
        job_id = f"{tool_name}-{uuid.uuid4().hex[:6]}"
        try:
            await asyncio.wait_for(
                self._heavy_sem.acquire(), timeout=self._heavy_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Heavy concurrency limit reached: %s could not be scheduled.", tool_name
            )
            raise RuntimeError(
                f"Concurrency limit reached: cannot schedule '{tool_name}' (heavy). "
                f"Currently active: {len([j for j in self._active.values() if j['type'] == 'heavy'])} heavy jobs."
            )

        self._active[job_id] = {
            "tool": tool_name,
            "type": "heavy",
            "start": time.time(),
        }
        logger.debug("Acquired heavy slot: %s (%s)", tool_name, job_id)

        try:
            yield job_id
        finally:
            self._heavy_sem.release()
            self._active.pop(job_id, None)
            logger.debug("Released heavy slot: %s (%s)", tool_name, job_id)

    @asynccontextmanager
    async def acquire_light(self, tool_name: str) -> AsyncIterator[str]:
        """
        Acquire a light-job slot. Raises RuntimeError if the semaphore
        cannot be acquired within the timeout.
        """
        job_id = f"{tool_name}-{uuid.uuid4().hex[:6]}"
        try:
            await asyncio.wait_for(
                self._light_sem.acquire(), timeout=self._light_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Light concurrency limit reached: %s could not be scheduled.", tool_name
            )
            raise RuntimeError(
                f"Concurrency limit reached: cannot schedule '{tool_name}' (light). "
                f"Currently active: {len([j for j in self._active.values() if j['type'] == 'light'])} light jobs."
            )

        self._active[job_id] = {
            "tool": tool_name,
            "type": "light",
            "start": time.time(),
        }
        logger.debug("Acquired light slot: %s (%s)", tool_name, job_id)

        try:
            yield job_id
        finally:
            self._light_sem.release()
            self._active.pop(job_id, None)
            logger.debug("Released light slot: %s (%s)", tool_name, job_id)

    def active_jobs(self) -> dict[str, dict]:
        """Return a snapshot of currently active jobs."""
        return dict(self._active)

    def active_count(self) -> dict[str, int]:
        """Return counts of active heavy and light jobs."""
        heavy = sum(1 for j in self._active.values() if j["type"] == "heavy")
        light = sum(1 for j in self._active.values() if j["type"] == "light")
        return {"heavy": heavy, "light": light, "total": heavy + light}
