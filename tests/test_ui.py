from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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


# ── SplashScreen._dismiss ─────────────────────────────────────

def test_splash_dismiss_single_server_goes_to_environment(mock_app, single_server_mgr) -> None:
    """Even with a single server, splash should go to EnvironmentScreen (not Dashboard)."""
    with patch("termainer.ui.splash.EnvironmentScreen") as MockEnv:
        with patch("termainer.ui.splash.Dashboard") as MockDash:
            from termainer.ui.splash import SplashScreen
            screen = SplashScreen(single_server_mgr)
            screen.app = mock_app
            screen._dismiss()
            # Should have called switch_screen with EnvironmentScreen
            assert mock_app.switch_screen.called
            args, _ = mock_app.switch_screen.call_args
            assert args[0].__class__.__name__ == "EnvironmentScreen"
            # Should NOT have called push_screen or gone to Dashboard directly
            assert not mock_app.push_screen.called


def test_splash_dismiss_multi_server_goes_to_environment(mock_app, multi_server_mgr) -> None:
    """With multiple servers, splash should go to EnvironmentScreen."""
    with patch("termainer.ui.splash.EnvironmentScreen") as MockEnv:
        from termainer.ui.splash import SplashScreen
        screen = SplashScreen(multi_server_mgr)
        screen.app = mock_app
        screen._dismiss()
        assert mock_app.switch_screen.called
        args, _ = mock_app.switch_screen.call_args
        assert args[0].__class__.__name__ == "EnvironmentScreen"


def test_splash_dismiss_called_only_once(mock_app, single_server_mgr) -> None:
    """_dismiss should set _dismissed flag and only execute once."""
    from termainer.ui.splash import SplashScreen
    screen = SplashScreen(single_server_mgr)
    screen.app = mock_app
    screen._dismiss()
    assert screen._dismissed is True
    screen._dismiss()  # second call should be no-op
    assert mock_app.switch_screen.call_count == 1


def test_splash_dismiss_uses_switch_screen_not_push(mock_app, multi_server_mgr) -> None:
    """Splash should use switch_screen (not push_screen) to remove itself from stack."""
    from termainer.ui.splash import SplashScreen
    screen = SplashScreen(multi_server_mgr)
    screen.app = mock_app
    screen._dismiss()
    assert mock_app.switch_screen.called
    assert not mock_app.push_screen.called


# ── EnvironmentScreen ─────────────────────────────────────────

def test_environment_creates_cards_for_servers(mock_app, multi_server_mgr) -> None:
    """EnvironmentScreen should create one card per server + optional 'All' card."""
    from termainer.ui.environment import EnvironmentScreen
    screen = EnvironmentScreen(multi_server_mgr)
    assert len(screen._card_ids) > 0
    assert len(screen._card_actions) > 0
    # Should have "open_all" action for multi-server
    assert "open_all" in screen._card_actions


def test_environment_single_server_no_all_card(mock_app, single_server_mgr) -> None:
    """With only one server, there should be no 'All Servers' card."""
    from termainer.ui.environment import EnvironmentScreen
    screen = EnvironmentScreen(single_server_mgr)
    assert "open_all" not in screen._card_actions


def test_environment_card_count_matches_servers(mock_app, multi_server_mgr) -> None:
    """Number of card IDs should match servers + all-card (for multi)."""
    from termainer.ui.environment import EnvironmentScreen
    screen = EnvironmentScreen(multi_server_mgr)
    # +1 for the "All Servers" card
    assert len(screen._card_ids) == multi_server_mgr.server_count + 1


# ── ServerManager ─────────────────────────────────────────────

def test_server_manager_label_prop(multi_server_mgr) -> None:
    assert "Local Docker" in multi_server_mgr.server_labels
    assert "Remote K8s" in multi_server_mgr.server_labels
