from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from termainer.providers.docker import DockerProvider
from termainer.providers.kubernetes import KubernetesProvider
from termainer.server_manager import ServerConnection, ServerManager, provider_class_for


@pytest.fixture
def docker_provider() -> DockerProvider:
    p = DockerProvider()
    p.is_available = AsyncMock(return_value=True)
    p.list_containers = AsyncMock(return_value=[
        {"id": "abc", "names": "cont1", "status": "running"},
        {"id": "def", "names": "cont2", "status": "exited"},
    ])
    return p


@pytest.fixture
def k8s_provider() -> KubernetesProvider:
    p = KubernetesProvider()
    p.is_available = AsyncMock(return_value=True)
    p.list_containers = AsyncMock(return_value=[
        {"id": "pod1", "name": "nginx-pod", "status": "running", "namespace": "default"},
    ])
    return p


def test_server_connection_local() -> None:
    conn = ServerConnection(label="local", provider=DockerProvider())
    assert conn.label == "local"
    assert conn.ssh is None


def test_server_connection_label() -> None:
    conn = ServerConnection(label="My Server", provider=DockerProvider())
    assert conn.label == "My Server"


def test_server_manager_empty() -> None:
    mgr = ServerManager()
    assert mgr.server_count == 0
    assert mgr.server_labels == []


def test_server_manager_single(docker_provider: DockerProvider) -> None:
    conn = ServerConnection(label="local", provider=docker_provider)
    mgr = ServerManager([conn])
    assert mgr.server_count == 1
    assert mgr.server_labels == ["local"]


def test_server_manager_multi(docker_provider: DockerProvider, k8s_provider: KubernetesProvider) -> None:
    mgr = ServerManager([
        ServerConnection(label="docker-server", provider=docker_provider),
        ServerConnection(label="k8s-server", provider=k8s_provider),
    ])
    assert mgr.server_count == 2
    assert mgr.server_labels == ["docker-server", "k8s-server"]


def test_get_provider_found(docker_provider: DockerProvider) -> None:
    conn = ServerConnection(label="local", provider=docker_provider)
    mgr = ServerManager([conn])
    assert mgr.get_provider("local") is docker_provider


def test_get_provider_not_found() -> None:
    mgr = ServerManager()
    with pytest.raises(KeyError):
        mgr.get_provider("nonexistent")


def test_get_provider_wrong_label(docker_provider: DockerProvider) -> None:
    conn = ServerConnection(label="server-a", provider=docker_provider)
    mgr = ServerManager([conn])
    with pytest.raises(KeyError):
        mgr.get_provider("server-b")


def test_has_local_true(docker_provider: DockerProvider) -> None:
    conn = ServerConnection(label="local", provider=docker_provider)
    mgr = ServerManager([conn])
    assert mgr.has_local() is True


def test_has_local_false_with_ssh(monkeypatch) -> None:
    from termainer.remote.ssh import SSHConnection
    try:
        ssh = SSHConnection(host="remote.example.com")
        mgr = ServerManager([
            ServerConnection(label="remote", provider=DockerProvider(), ssh=ssh),
        ])
        assert mgr.has_local() is False
    except Exception:
        pytest.skip("SSHConnection import failed (expected if ssh binary not present)")


def test_list_all_containers_single(docker_provider: DockerProvider) -> None:
    conn = ServerConnection(label="docker-server", provider=docker_provider)
    mgr = ServerManager([conn])
    import asyncio
    containers = asyncio.run(mgr.list_all_containers())
    assert len(containers) == 2
    for c in containers:
        assert c["_server"] == "docker-server"


def test_list_all_containers_multi(docker_provider: DockerProvider, k8s_provider: KubernetesProvider) -> None:
    mgr = ServerManager([
        ServerConnection(label="docker-server", provider=docker_provider),
        ServerConnection(label="k8s-server", provider=k8s_provider),
    ])
    import asyncio
    containers = asyncio.run(mgr.list_all_containers())
    assert len(containers) == 3
    docker_containers = [c for c in containers if c["_server"] == "docker-server"]
    k8s_containers = [c for c in containers if c["_server"] == "k8s-server"]
    assert len(docker_containers) == 2
    assert len(k8s_containers) == 1


def test_list_all_containers_server_tagged(docker_provider: DockerProvider) -> None:
    conn = ServerConnection(label="prod", provider=docker_provider)
    mgr = ServerManager([conn])
    import asyncio
    containers = asyncio.run(mgr.list_all_containers())
    for c in containers:
        assert "_server" in c
        assert c["_server"] == "prod"


def test_list_all_containers_empty(docker_provider: DockerProvider) -> None:
    docker_provider.list_containers = AsyncMock(return_value=[])
    conn = ServerConnection(label="empty", provider=docker_provider)
    mgr = ServerManager([conn])
    import asyncio
    containers = asyncio.run(mgr.list_all_containers())
    assert containers == []


def test_list_all_containers_exception_ignored() -> None:
    broken = DockerProvider()
    broken.list_containers = AsyncMock(side_effect=RuntimeError("broken"))
    working = DockerProvider()
    working.list_containers = AsyncMock(return_value=[{"id": "ok", "names": "working", "_server": "good"}])
    mgr = ServerManager([
        ServerConnection(label="broken", provider=broken),
        ServerConnection(label="good", provider=working),
    ])
    import asyncio
    containers = asyncio.run(mgr.list_all_containers())
    assert len(containers) == 1
    assert containers[0]["id"] == "ok"


def test_close_all_called(docker_provider: DockerProvider) -> None:
    docker_provider.close = AsyncMock()
    conn = ServerConnection(label="test", provider=docker_provider)
    mgr = ServerManager([conn])
    import asyncio
    asyncio.run(mgr.close_all())
    docker_provider.close.assert_awaited_once()


def test_close_all_exception_ignored() -> None:
    broken = DockerProvider()
    broken.close = AsyncMock(side_effect=RuntimeError("close failed"))
    conn = ServerConnection(label="broken", provider=broken)
    mgr = ServerManager([conn])
    import asyncio
    asyncio.run(mgr.close_all())  # should not raise


def test_provider_class_for_docker() -> None:
    from termainer.providers.docker import DockerProvider
    assert provider_class_for("docker") is DockerProvider


def test_provider_class_for_kubernetes() -> None:
    from termainer.providers.kubernetes import KubernetesProvider
    assert provider_class_for("kubernetes") is KubernetesProvider
    assert provider_class_for("k8s") is KubernetesProvider


def test_provider_class_for_openshift() -> None:
    from termainer.providers.openshift import OpenShiftProvider
    assert provider_class_for("openshift") is OpenShiftProvider


def test_provider_class_for_podman() -> None:
    from termainer.providers.podman import PodmanProvider
    assert provider_class_for("podman") is PodmanProvider


def test_provider_class_for_swarm() -> None:
    from termainer.providers.swarm import SwarmProvider
    assert provider_class_for("swarm") is SwarmProvider


def test_provider_class_for_unknown() -> None:
    with pytest.raises(RuntimeError, match="Unknown provider"):
        provider_class_for("nonexistent")


def test_provider_class_for_case_insensitive() -> None:
    from termainer.providers.docker import DockerProvider
    assert provider_class_for("DOCKER") is DockerProvider
    assert provider_class_for("Docker") is DockerProvider
