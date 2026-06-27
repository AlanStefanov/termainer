from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from termainer.server_manager import ServerConnection, ServerManager
from termainer.providers.docker import DockerProvider


@pytest.fixture
def mock_app() -> MagicMock:
    app = MagicMock()
    app.push_screen = MagicMock()
    app.switch_screen = MagicMock()
    return app


@pytest.fixture
def single_server_mgr() -> ServerManager:
    return ServerManager([
        ServerConnection(label="Local Docker", provider=DockerProvider()),
    ])


@pytest.fixture
def multi_server_mgr() -> ServerManager:
    return ServerManager([
        ServerConnection(label="Local Docker", provider=DockerProvider()),
        ServerConnection(label="Remote K8s", provider=DockerProvider()),
    ])


# ── BootScreen / SplashScreen ─────────────────────────────────

def test_splash_skip_goes_to_home(mock_app, single_server_mgr) -> None:
    """SplashScreen.action_skip should call _go_home and switch to HomeScreen."""
    from unittest.mock import PropertyMock
    from termainer.ui.splash import SplashScreen
    screen = SplashScreen(single_server_mgr)
    with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
        screen.action_skip()
    assert mock_app.switch_screen.called


def test_splash_skip_called_only_once(mock_app, single_server_mgr) -> None:
    """_go_home should set _done flag and only execute once."""
    from unittest.mock import PropertyMock
    from termainer.ui.splash import SplashScreen
    screen = SplashScreen(single_server_mgr)
    with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
        screen._go_home()
        assert screen._done is True
        screen._go_home()  # second call should be no-op
    assert mock_app.switch_screen.call_count == 1


def test_splash_uses_switch_screen_not_push(mock_app, multi_server_mgr) -> None:
    """Splash should use switch_screen (not push_screen) to remove itself from stack."""
    from unittest.mock import PropertyMock
    from termainer.ui.splash import SplashScreen
    screen = SplashScreen(multi_server_mgr)
    with patch.object(type(screen), "app", new_callable=PropertyMock, return_value=mock_app):
        screen.action_skip()
    assert mock_app.switch_screen.called
    assert not mock_app.push_screen.called


# ── EnvironmentScreen ─────────────────────────────────────────

def test_environment_creates_cards_for_servers(mock_app, multi_server_mgr) -> None:
    """EnvironmentScreen composes technology cards (one per provider type, not per server)."""
    from termainer.ui.environment import EnvironmentScreen, TECHNOLOGY_CARDS
    screen = EnvironmentScreen(multi_server_mgr)
    # Cards are created during compose(); force iteration to populate _card_ids
    list(screen.compose())
    assert len(screen._card_ids) == len(TECHNOLOGY_CARDS)
    assert len(screen._card_actions) == len(TECHNOLOGY_CARDS)


def test_environment_single_server_no_all_card(mock_app, single_server_mgr) -> None:
    """EnvironmentScreen always uses technology-first cards regardless of server count."""
    from termainer.ui.environment import EnvironmentScreen, TECHNOLOGY_CARDS
    screen = EnvironmentScreen(single_server_mgr)
    list(screen.compose())
    assert len(screen._card_ids) == len(TECHNOLOGY_CARDS)


def test_environment_card_count_matches_servers(mock_app, multi_server_mgr) -> None:
    """Card count should match the number of technology cards defined."""
    from termainer.ui.environment import EnvironmentScreen, TECHNOLOGY_CARDS
    screen = EnvironmentScreen(multi_server_mgr)
    list(screen.compose())
    assert len(screen._card_ids) == len(TECHNOLOGY_CARDS)


# ── ServerManager ─────────────────────────────────────────────

def test_server_manager_label_prop(multi_server_mgr) -> None:
    assert "Local Docker" in multi_server_mgr.server_labels
    assert "Remote K8s" in multi_server_mgr.server_labels
