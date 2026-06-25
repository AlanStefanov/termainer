from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional, Protocol, runtime_checkable

from ..remote.ssh import SSHConnection


ContainerSummary = Dict[str, Any]
ContainerDetails = Dict[str, Any]
ContainerStats = Dict[str, Any]


@runtime_checkable
class Provider(Protocol):
    name: str

    async def list_containers(self) -> List[ContainerSummary]:
        ...

    async def inspect(self, container_id: str) -> ContainerDetails:
        ...

    async def stats(self, container_id: str) -> AsyncIterator[ContainerStats]:
        ...

    async def logs(
        self, container_id: str, tail: int = 100, follow: bool = False
    ) -> AsyncIterator[str]:
        ...

    async def get_env(self, container_id: str) -> Dict[str, str]:
        ...

    async def start(self, container_id: str) -> None:
        ...

    async def stop(self, container_id: str) -> None:
        ...

    async def restart(self, container_id: str) -> None:
        ...

    async def remove(self, container_id: str, force: bool = False) -> None:
        ...

    async def is_available(self) -> bool:
        ...

    async def close(self) -> None:
        ...


class SSHAwareProvider:
    _ssh: Optional[SSHConnection] = None
