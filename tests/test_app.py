from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from termainer.app import build_server_manager, run_doctor


def test_run_doctor_reports_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_doctor() in {0, 1}

    output = capsys.readouterr().out
    assert "Termainer Doctor" in output
    assert "Version" in output


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
async def test_build_server_manager_local_auto_empty_when_none_available() -> None:
    with patch("termainer.app.DockerProvider.is_available", new=AsyncMock(return_value=False)), patch(
        "termainer.app.SwarmProvider.is_available", new=AsyncMock(return_value=False)
    ), patch(
        "termainer.app.KubernetesProvider.is_available", new=AsyncMock(return_value=False)
    ), patch("termainer.app.PodmanProvider.is_available", new=AsyncMock(return_value=False)), patch(
        "termainer.app.OpenShiftProvider.is_available", new=AsyncMock(return_value=False)
    ):
        mgr = await build_server_manager([], ssh=None, cli_provider="auto")

    assert mgr.server_count == 0


@pytest.mark.asyncio
async def test_build_server_manager_local_explicit_provider_stays_single() -> None:
    with patch("termainer.app.DockerProvider.is_available", new=AsyncMock(return_value=True)):
        mgr = await build_server_manager([], ssh=None, cli_provider="docker")

    assert mgr.server_count == 1
    assert mgr.server_labels == ["Local Docker"]
