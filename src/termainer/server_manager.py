from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .providers.base import ContainerSummary, Provider
from .providers.docker import DockerProvider
from .providers.kubernetes import KubernetesProvider
from .providers.openshift import OpenShiftProvider
from .providers.podman import PodmanProvider
from .providers.swarm import SwarmProvider
from .remote.ssh import SSHConnection


PROVIDER_MAP: dict[str, type] = {
    "docker": DockerProvider,
    "podman": PodmanProvider,
    "kubernetes": KubernetesProvider,
    "k8s": KubernetesProvider,
    "openshift": OpenShiftProvider,
    "swarm": SwarmProvider,
}


@dataclass
class ServerConnection:
    label: str
    provider: Provider
    ssh: Optional[SSHConnection] = None


class ServerManager:
    def __init__(self, servers: Optional[List[ServerConnection]] = None) -> None:
        self.servers: List[ServerConnection] = servers or []

    @property
    def server_count(self) -> int:
        return len(self.servers)

    @property
    def server_labels(self) -> List[str]:
        return [s.label for s in self.servers]

    def get_provider(self, label: str) -> Provider:
        for s in self.servers:
            if s.label == label:
                return s.provider
        raise KeyError(f"Server '{label}' not found")

    def has_local(self) -> bool:
        return any(s.ssh is None for s in self.servers)

    def get_connection(self, label: str) -> Optional[SSHConnection]:
        for s in self.servers:
            if s.label == label:
                return s.ssh
        return None

    async def list_all_containers(self) -> List[ContainerSummary]:
        results: List[ContainerSummary] = []
        for server in self.servers:
            try:
                containers = await server.provider.list_containers()
                for c in containers:
                    c["_server"] = server.label
                results.extend(containers)
            except Exception:
                pass
        return results

    async def close_all(self) -> None:
        for server in self.servers:
            try:
                await server.provider.close()
            except Exception:
                pass


def provider_class_for(name: str) -> type:
    cls = PROVIDER_MAP.get(name.lower())
    if cls is None:
        available = ", ".join(sorted(PROVIDER_MAP))
        raise RuntimeError(f"Unknown provider '{name}'. Available: {available}")
    return cls
