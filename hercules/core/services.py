"""Typed service boundaries behind the legacy DockerManager facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hercules.core.docker_manager import DockerManager


@dataclass(frozen=True)
class ContainerService:
    """Container lifecycle service used by new integrations."""

    manager: DockerManager

    async def ensure_ready(self) -> None:
        await self.manager.ensure_ready()

    async def new_session(self) -> str:
        return await self.manager.new_session()

    async def stop(self) -> None:
        await self.manager.operator_stop()


@dataclass(frozen=True)
class ExecutionService:
    """Bounded command and owned-workspace I/O service."""

    manager: DockerManager

    async def execute(self, command: str, **options: Any):
        return await self.manager.exec_command(command, **options)

    async def read(self, path: str, **options: Any):
        return await self.manager.read_file_chunk(path, **options)

    async def write(self, path: str, content: str | bytes, **options: Any) -> None:
        await self.manager.write_file(path, content, **options)


@dataclass(frozen=True)
class JobService:
    """Generation-aware background-process service."""

    manager: DockerManager

    async def start(self, command: str, job_id: str, **options: Any) -> str:
        return await self.manager.exec_background(command, job_id, **options)

    async def check(self, job_id: str, *, tail_lines: int = 50) -> dict:
        return await self.manager.check_job(job_id, tail_lines=tail_lines)

    async def terminate(self, job_id: str) -> dict:
        return await self.manager.terminate_job(job_id)


@dataclass
class BrowserStateService:
    """Typed generation marker for browser process-local state."""

    generation: int = 0

    def reset(self, generation: int) -> None:
        self.generation = generation


@dataclass
class MetasploitStateService:
    """Typed facade over the mapping retained for existing tool imports."""

    values: dict[str, Any]
    generation: int = 0

    def reset(self, generation: int, *, disabled: bool) -> None:
        task = self.values.get("connect_task")
        if (
            task is not None
            and callable(getattr(task, "done", None))
            and not task.done()
        ):
            task.cancel()
        self.generation = generation
        self.values.update(
            {
                "client": None,
                "connect_task": None,
                "status": "disabled" if disabled else "initializing",
                "error": "",
            }
        )
