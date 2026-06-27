from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from termainer.providers.base import ContainerSummary, Provider
from termainer.providers.docker import DockerProvider
from termainer.providers.podman import PodmanProvider
from termainer.providers.kubernetes import KubernetesProvider
from termainer.providers.openshift import OpenShiftProvider
from termainer.providers.swarm import SwarmProvider


# ── Protocol / Interface ──────────────────────────────────────

def test_provider_protocol() -> None:
    assert isinstance(DockerProvider(), Provider)
    assert isinstance(PodmanProvider(), Provider)
    assert isinstance(KubernetesProvider(), Provider)
    assert isinstance(OpenShiftProvider(), Provider)
    assert isinstance(SwarmProvider(), Provider)


# ── DockerProvider ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_docker_is_available_false() -> None:
    provider = DockerProvider()
    with patch("shutil.which", return_value=None):
        assert await provider.is_available() is False


@pytest.mark.asyncio
async def test_docker_list_containers() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    mock_run = AsyncMock(side_effect=[
        "abc123\n",  # ps -a -q
        json.dumps([{  # inspect
            "Id": "abc123",
            "Name": "/test",
            "Config": {"Image": "nginx"},
            "State": {"Status": "running"},
            "Created": "2024-01-01T00:00:00Z",
            "NetworkSettings": {"Ports": {"80/tcp": [{"HostPort": "8080"}]}, "Networks": {"bridge": {}}},
            "HostConfig": {"RestartPolicy": {"Name": "always"}},
        }]),
    ])
    provider._run = mock_run
    result = await provider.list_containers()
    assert len(result) == 1
    assert result[0]["id"] == "abc123"
    assert result[0]["names"] == "test"
    assert result[0]["status"] == "running"


@pytest.mark.asyncio
async def test_docker_list_containers_empty() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    provider._run = AsyncMock(return_value="\n")
    result = await provider.list_containers()
    assert result == []


@pytest.mark.asyncio
async def test_docker_list_containers_multiple() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    mock_run = AsyncMock(side_effect=[
        "c1\nc2\n",  # ps -a -q
        json.dumps([  # inspect
            {
                "Id": "c1",
                "Name": "/first",
                "Config": {"Image": "img1"},
                "State": {"Status": "running"},
                "Created": "2024-01-01T00:00:00Z",
                "NetworkSettings": {"Ports": {"80/tcp": [{"HostPort": "8080"}]}, "Networks": {"bridge": {}}},
                "HostConfig": {"RestartPolicy": {"Name": ""}},
            },
            {
                "Id": "c2",
                "Name": "/second",
                "Config": {"Image": "img2"},
                "State": {"Status": "exited"},
                "Created": "2024-01-02T00:00:00Z",
                "NetworkSettings": {"Ports": {}, "Networks": {}},
                "HostConfig": {"RestartPolicy": {"Name": ""}},
            },
        ]),
    ])
    provider._run = mock_run
    result = await provider.list_containers()
    assert len(result) == 2
    assert result[0]["id"] == "c1"
    assert result[1]["names"] == "second"
    assert result[0]["status"] == "running"
    assert result[1]["status"] == "exited"


@pytest.mark.asyncio
async def test_docker_inspect() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    provider._run = AsyncMock(return_value=json.dumps([{"Id": "abc", "Config": {"Env": ["FOO=bar"]}}]))
    result = await provider.inspect("abc")
    assert result["Id"] == "abc"


@pytest.mark.asyncio
async def test_docker_inspect_single_object() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    provider._run = AsyncMock(return_value=json.dumps({"Id": "abc"}))
    result = await provider.inspect("abc")
    assert result["Id"] == "abc"


@pytest.mark.asyncio
async def test_docker_inspect_empty() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    provider._run = AsyncMock(return_value=json.dumps([]))
    result = await provider.inspect("abc")
    assert result == {}


@pytest.mark.asyncio
async def test_docker_get_env() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    inspect_data = {"Config": {"Env": ["PATH=/usr/bin", "HOME=/root", "FOO=bar"]}}
    provider.inspect = AsyncMock(return_value=inspect_data)
    env = await provider.get_env("abc")
    assert env["PATH"] == "/usr/bin"
    assert env["HOME"] == "/root"
    assert env["FOO"] == "bar"


@pytest.mark.asyncio
async def test_docker_get_env_empty() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    provider.inspect = AsyncMock(return_value={})
    env = await provider.get_env("abc")
    assert env == {}


@pytest.mark.asyncio
async def test_docker_start() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    provider._run = AsyncMock(return_value="")
    await provider.start("abc")
    provider._run.assert_awaited_once_with("start", "abc")


@pytest.mark.asyncio
async def test_docker_stop() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    provider._run = AsyncMock(return_value="")
    await provider.stop("abc")
    provider._run.assert_awaited_once_with("stop", "abc")


@pytest.mark.asyncio
async def test_docker_restart() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    provider._run = AsyncMock(return_value="")
    await provider.restart("abc")
    provider._run.assert_awaited_once_with("restart", "abc")


@pytest.mark.asyncio
async def test_docker_remove() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    provider._run = AsyncMock(return_value="")
    await provider.remove("abc")
    provider._run.assert_awaited_once_with("rm", "abc")


@pytest.mark.asyncio
async def test_docker_remove_force() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"
    provider._run = AsyncMock(return_value="")
    await provider.remove("abc", force=True)
    provider._run.assert_awaited_once_with("rm", "-f", "abc")


@pytest.mark.asyncio
async def test_docker_close_noop() -> None:
    provider = DockerProvider()
    await provider.close()  # should not raise


@pytest.mark.asyncio
async def test_docker_is_available_ssh_false() -> None:
    ssh = MagicMock()
    ssh.run = AsyncMock(side_effect=RuntimeError("SSH failed"))
    provider = DockerProvider(ssh=ssh)
    assert await provider.is_available() is False
    ssh.run.assert_awaited_once_with(["docker", "info"])


@pytest.mark.asyncio
async def test_docker_is_available_ssh_true() -> None:
    ssh = MagicMock()
    ssh.run = AsyncMock(return_value="")
    provider = DockerProvider(ssh=ssh)
    assert await provider.is_available() is True
    assert provider._docker_path == "docker"


@pytest.mark.asyncio
async def test_docker_run_local() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await provider._run("ps", "-a")
    assert result == "output"


@pytest.mark.asyncio
async def test_docker_run_local_error() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"

    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(b"", b"error msg"))
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(RuntimeError, match="docker ps failed"):
            await provider._run("ps")


@pytest.mark.asyncio
async def test_docker_stats_stream() -> None:
    provider = DockerProvider()
    provider._docker_path = "/usr/bin/docker"

    mock_stream = AsyncMock()
    mock_stream.readline = AsyncMock(side_effect=[
        b'{"CPUPerc": "12.5%", "MemUsage": "100MiB / 1GiB"}\n',
        b'',
    ])
    with patch("asyncio.create_subprocess_exec") as mock_spawn:
        mock_proc = MagicMock()
        mock_proc.stdout = mock_stream
        mock_spawn.return_value = mock_proc
        stats = []
        async for s in provider.stats("abc"):
            stats.append(s)
    assert len(stats) == 1
    assert stats[0]["CPUPerc"] == "12.5%"


# ── PodmanProvider ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_podman_is_available_false() -> None:
    provider = PodmanProvider()
    with patch("shutil.which", return_value=None):
        assert await provider.is_available() is False


@pytest.mark.asyncio
async def test_podman_list_containers() -> None:
    provider = PodmanProvider()
    provider._podman_path = "/usr/bin/podman"
    # Podman returns its own JSON format (list of objects)
    provider._run = AsyncMock(return_value=json.dumps([{"Id": "abc", "Names": ["test"]}]))
    result = await provider.list_containers()
    assert len(result) == 1
    assert result[0]["Id"] == "abc"


# ── KubernetesProvider ────────────────────────────────────────

@pytest.mark.asyncio
async def test_kubernetes_list_containers() -> None:
    provider = KubernetesProvider()
    provider._kubectl_path = "/usr/bin/kubectl"
    # kubectl get pods -o json returns {"items": [...]}
    provider._run = AsyncMock(return_value=json.dumps({
        "items": [{"metadata": {"name": "pod1", "namespace": "default"}, "status": {"phase": "Running"}, "spec": {"containers": []}}]
    }))
    result = await provider.list_containers()
    assert len(result) == 1
    assert result[0]["name"] == "pod1"


@pytest.mark.asyncio
async def test_kubernetes_is_available_false() -> None:
    provider = KubernetesProvider()
    with patch("shutil.which", return_value=None):
        assert await provider.is_available() is False


# ── OpenShiftProvider ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_openshift_is_available_false() -> None:
    provider = OpenShiftProvider()
    with patch("shutil.which", return_value=None):
        assert await provider.is_available() is False


@pytest.mark.asyncio
async def test_openshift_list_containers() -> None:
    provider = OpenShiftProvider()
    provider._oc_path = "/usr/bin/oc"
    # oc get pods -o json returns {"items": [...]}
    provider._run = AsyncMock(return_value=json.dumps({
        "items": [{"metadata": {"name": "pod1", "namespace": "default"}, "status": {"phase": "Running"}, "spec": {"containers": []}}]
    }))
    result = await provider.list_containers()
    assert len(result) == 1
    assert result[0]["name"] == "pod1"


# ── SwarmProvider ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_swarm_is_available_false() -> None:
    provider = SwarmProvider()
    with patch("shutil.which", return_value=None):
        assert await provider.is_available() is False


@pytest.mark.asyncio
async def test_swarm_list_containers() -> None:
    provider = SwarmProvider()
    provider._docker_path = "/usr/bin/docker"
    provider._run = AsyncMock(return_value='{"ID":"abc123","Name":"web","Mode":"replicated","Replicas":"2/2","Image":"nginx:latest","Ports":"*:80->80/tcp"}\n')
    result = await provider.list_containers()
    assert len(result) == 1
    assert result[0]["id"] == "abc123"
    assert result[0]["name"] == "web"
    assert "replicated" in result[0]["status"]


# ── Regression: ContainerSummary type ─────────────────────────

def test_container_summary_dict() -> None:
    c: ContainerSummary = {"id": "abc", "names": "test", "_server": "local"}
    assert c["id"] == "abc"
    assert c["_server"] == "local"
