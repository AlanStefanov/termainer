from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from termainer.app import build_server_manager


@pytest.mark.asyncio
async def test_build_server_manager_local_auto_builds_multiple_servers() -> None:
    with patch("termainer.app.DockerProvider.is_available", new=AsyncMock(return_value=True)), patch(
        "termainer.app.SwarmProvider.is_available", new=AsyncMock(return_value=True)
    ), patch(
        "termainer.app.KubernetesProvider.is_available", new=AsyncMock(return_value=True)
    ), patch("termainer.app.PodmanProvider.is_available", new=AsyncMock(return_value=False)), patch(
        "termainer.app.OpenShiftProvider.is_available", new=AsyncMock(return_value=True)
    ):
        mgr = await build_server_manager([], ssh=None, cli_provider="auto")

    assert mgr.server_count == 4
    assert mgr.server_labels == ["Local Docker", "Local Swarm", "Local Kubernetes", "Local Openshift"]


@pytest.mark.asyncio
async def test_build_server_manager_local_auto_raises_when_none_available() -> None:
    with patch("termainer.app.DockerProvider.is_available", new=AsyncMock(return_value=False)), patch(
        "termainer.app.SwarmProvider.is_available", new=AsyncMock(return_value=False)
    ), patch(
        "termainer.app.KubernetesProvider.is_available", new=AsyncMock(return_value=False)
    ), patch("termainer.app.PodmanProvider.is_available", new=AsyncMock(return_value=False)), patch(
        "termainer.app.OpenShiftProvider.is_available", new=AsyncMock(return_value=False)
    ):
        with pytest.raises(RuntimeError, match="No container runtime detected"):
            await build_server_manager([], ssh=None, cli_provider="auto")


@pytest.mark.asyncio
async def test_build_server_manager_local_explicit_provider_stays_single() -> None:
    with patch("termainer.app.DockerProvider.is_available", new=AsyncMock(return_value=True)):
        mgr = await build_server_manager([], ssh=None, cli_provider="docker")

    assert mgr.server_count == 1
    assert mgr.server_labels == ["Local Docker"]
