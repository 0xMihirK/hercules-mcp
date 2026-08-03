"""Typed runtime services layered over the legacy lifespan mapping."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from hercules.core.services import (
    BrowserStateService,
    ContainerService,
    ExecutionService,
    JobService,
    MetasploitStateService,
)
from hercules.core.security import redact_secrets

if TYPE_CHECKING:
    from hercules.core.concurrency import ConcurrencyManager
    from hercules.core.config import HerculesConfig
    from hercules.core.docker_manager import DockerManager
    from hercules.core.workspace import WorkspaceManager

logger = logging.getLogger("hercules.runtime")


ResetCallback = Callable[[], None]
SessionCallback = Callable[[str], None]


@dataclass
class RuntimeServices:
    """Generation-bound runtime state with a mapping compatibility bridge."""

    config: HerculesConfig
    docker: DockerManager
    workspace: WorkspaceManager
    concurrency: ConcurrencyManager | None = None
    msf_state: dict[str, Any] = field(default_factory=dict)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    legacy_context: dict[str, Any] = field(default_factory=dict)
    generation_resetters: list[ResetCallback] = field(default_factory=list)
    session_callbacks: list[SessionCallback] = field(default_factory=list)
    containers: ContainerService = field(init=False)
    execution: ExecutionService = field(init=False)
    jobs: JobService = field(init=False)
    browser_state: BrowserStateService = field(init=False)
    metasploit: MetasploitStateService = field(init=False)

    def __post_init__(self) -> None:
        generation = int(getattr(self.docker, "generation", 0))
        self.containers = ContainerService(self.docker)
        self.execution = ExecutionService(self.docker)
        self.jobs = JobService(self.docker)
        self.browser_state = BrowserStateService(generation)
        self.metasploit = MetasploitStateService(
            self.msf_state,
            generation,
        )

    def register_generation_resetter(self, callback: ResetCallback) -> None:
        self.generation_resetters.append(callback)

    def register_session_callback(self, callback: SessionCallback) -> None:
        self.session_callbacks.append(callback)

    def reset_generation_bound_state(self) -> None:
        for callback in self.generation_resetters:
            try:
                callback()
            except Exception as exc:
                logger.warning("Runtime reset callback failed: %s", exc)

    def on_generation_change(self, _generation: int) -> None:
        """Invalidate clients and caches tied to a replaced container."""
        self.reset_generation_bound_state()
        self.browser_state.reset(_generation)
        self.metasploit.reset(
            _generation,
            disabled=self.config.skip_metasploit,
        )
        self._publish_msf_state()

    def _publish_msf_state(self) -> None:
        context = self.legacy_context
        state = self.msf_state
        context["msf_state"] = state
        context["msf_client"] = state.get("client")
        context["msf_connect_task"] = state.get("connect_task")
        context["msf_status"] = state.get("status", "")
        context["msf_error"] = state.get("error", "")

    def publish_runtime_state(self) -> None:
        """Mirror startup state into the legacy lifespan mapping."""
        self.legacy_context["runtime_state"] = self.runtime_state
        self.legacy_context["runtime_status"] = self.runtime_state.get(
            "status", "starting"
        )
        self.legacy_context["runtime_error"] = self.runtime_state.get(
            "error", ""
        )
        self.legacy_context["runtime_diagnostic"] = self.runtime_state.get(
            "diagnostic", self.runtime_state.get("error", "")
        )

    async def start_new_session(self) -> str:
        """Rotate the workspace and reset every generation-bound integration."""
        await self.docker.cancel_startup()
        self.docker.clear_startup_state()
        self.runtime_state.update(
            {
                "status": "starting",
                "started_at": datetime.now(UTC).isoformat(),
                "completed_at": "",
                "error": "",
                "diagnostic": "",
            }
        )
        self.publish_runtime_state()
        old_task = self.msf_state.get("connect_task")
        if (
            old_task is not None
            and callable(getattr(old_task, "done", None))
            and not old_task.done()
        ):
            old_task.cancel()
            try:
                await old_task
            except asyncio.CancelledError:
                pass

        try:
            new_session = await self.docker.new_session()
        except Exception as exc:
            safe_error = redact_secrets(
                str(exc),
                [
                    getattr(self.config, "msf_password", ""),
                    getattr(self.config, "browser_proxy_url", ""),
                ],
            )[:2000]
            self.runtime_state.update(
                {
                    "status": "unavailable",
                    "completed_at": datetime.now(UTC).isoformat(),
                    "error": safe_error,
                    "diagnostic": safe_error,
                }
            )
            self.publish_runtime_state()
            raise
        self.runtime_state.update(
            {
                "status": "ready",
                "completed_at": datetime.now(UTC).isoformat(),
                "error": "",
                "diagnostic": "",
            }
        )
        self.publish_runtime_state()
        for callback in self.session_callbacks:
            try:
                callback(new_session)
            except Exception as exc:
                logger.warning("Session callback failed: %s", exc)

        if self.config.skip_metasploit:
            self.msf_state.update(
                {
                    "client": None,
                    "connect_task": None,
                    "status": "disabled",
                    "error": "",
                }
            )
        else:
            self.msf_state.update(
                {
                    "client": None,
                    "connect_task": None,
                    "status": "initializing",
                    "error": "",
                }
            )
            try:
                client = await self.docker.wait_for_msfrpcd()
            except TimeoutError as exc:
                self.msf_state.update(
                    {
                        "status": "unavailable",
                        "error": str(exc),
                    }
                )
            else:
                self.msf_state.update(
                    {
                        "client": client,
                        "status": "ready",
                        "error": "",
                    }
                )
        self._publish_msf_state()
        return new_session

    async def stop_for_operator(self) -> None:
        """Stop the active container without allowing concurrent recovery."""
        await self.containers.stop()


def services_from_context(context: dict[str, Any]) -> RuntimeServices:
    """Return the typed service object and hydrate optional legacy services."""
    services = context.get("services")
    if not isinstance(services, RuntimeServices):
        services = RuntimeServices(
            config=context["config"],
            docker=context["docker"],
            workspace=context["docker"].workspace_manager,
            concurrency=context.get("concurrency"),
            msf_state=context.get("msf_state") or {},
            runtime_state=context.get("runtime_state") or {},
            legacy_context=context,
        )
        context["services"] = services
    if services.concurrency is None:
        services.concurrency = context.get("concurrency")
    services.legacy_context = context
    return services
