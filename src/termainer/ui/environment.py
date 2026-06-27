from __future__ import annotations

from dataclasses import dataclass
import shutil
from typing import List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.screen import Screen
from textual.widgets import Button, Static

from ..locale import _
from ..config import has_ssh_servers_configured
from ..server_manager import ServerManager
from ..version import VERSION
from .dashboard import Dashboard


_SERVER_ICONS = {
    "docker": "[bold #4ade80]◇[/]",
    "podman": "[bold #22d3ee]◇[/]",
    "kubernetes": "[bold #22d3ee]◈[/]",
    "openshift": "[bold #f87171]◈[/]",
    "swarm": "[bold #fbbf24]⬢[/]",
}


def _server_icon(provider_name: str) -> str:
    return _SERVER_ICONS.get(provider_name.lower(), "[bold white]◇[/]")


@dataclass(frozen=True)
class TechnologyCard:
    provider: str
    title: str
    subtitle: str


TECHNOLOGY_CARDS: List[TechnologyCard] = [
    TechnologyCard("docker", "Docker", _("environment.subtitle.docker")),
    TechnologyCard("kubernetes", "Kubernetes", _("environment.subtitle.kubernetes")),
    TechnologyCard("podman", "Podman", _("environment.subtitle.podman")),
    TechnologyCard("openshift", "OpenShift", _("environment.subtitle.openshift")),
    TechnologyCard("swarm", "Docker Swarm", _("environment.subtitle.swarm")),
]


PROVIDER_CLI_COMMAND = {
    "docker": "docker",
    "kubernetes": "kubectl",
    "podman": "podman",
    "openshift": "oc",
    "swarm": "docker",
}


class EnvironmentScreen(Screen):
    BINDINGS = [
        Binding("up", "focus_up", _("environment.bind.up"), priority=True),
        Binding("down", "focus_down", _("environment.bind.down"), priority=True),
        Binding("left", "focus_left", _("environment.bind.left"), priority=True),
        Binding("right", "focus_right", _("environment.bind.right"), priority=True),
        Binding("enter", "select_focused", _("environment.bind.select"), priority=True),
        Binding("?", "show_welcome_help", _("environment.bind.help"), priority=True),
        Binding("h", "show_welcome_help", _("environment.bind.help"), priority=True),
        Binding("q", "quit", _("environment.bind.quit"), priority=True),
    ]

    def __init__(self, server_manager: ServerManager) -> None:
        super().__init__()
        self._server_manager = server_manager
        self._card_ids: List[str] = []
        self._card_actions: List[str] = []

    def compose(self) -> ComposeResult:
        rows: List[Horizontal] = []
        row_cards: List[Vertical] = []
        cols_per_row = 2

        for i, tech in enumerate(TECHNOLOGY_CARDS):
            row_cards.append(self._technology_card(tech, i))
            if len(row_cards) == cols_per_row:
                rows.append(Horizontal(*row_cards, id=f"env-row-{len(rows)}"))
                row_cards = []

        if row_cards:
            rows.append(Horizontal(*row_cards, id=f"env-row-{len(rows)}"))

        yield Vertical(
            Static(f"[bold #22d3ee]TERMAINER[/] [#808080]v{VERSION}[/]", id="env-brand"),
            Static(_("environment.title"), id="env-title"),
            Static(
                f"[dim]{_('environment.copy')}[/]",
                id="env-copy",
            ),
            *rows,
            Horizontal(
                Static(
                    _("environment.footer.full"),
                    id="env-footer-full",
                    classes="env-footer-text",
                ),
                Static(
                    _("environment.footer.compact"),
                    id="env-footer-compact",
                    classes="env-footer-text",
                ),
                id="env-footer",
            ),
            id="env-root",
        )

    @property
    def _has_remote_servers(self) -> bool:
        return any(s.ssh is not None for s in self._server_manager.servers)

    def _servers_for_provider(self, provider_name: str):
        return [s for s in self._server_manager.servers if s.provider.name.lower() == provider_name.lower()]

    def _provider_cli_available(self, provider_name: str) -> bool:
        cli = PROVIDER_CLI_COMMAND.get(provider_name)
        if not cli:
            return False
        return shutil.which(cli) is not None

    def _provider_status_text(self, provider_name: str) -> str:
        count = len(self._servers_for_provider(provider_name))
        if count > 0:
            return _("environment.status.connections", count=str(count))
        if self._provider_cli_available(provider_name):
            if provider_name in {"kubernetes", "openshift"}:
                if self._has_remote_servers:
                    return _("environment.status.cli_no_context", provider=provider_name.capitalize())
                return _("environment.status.cli_no_cluster", provider=provider_name.capitalize())
            return _("environment.status.cli_no_servers", provider=provider_name.capitalize())
        return _("environment.status.not_available", provider=provider_name.capitalize())

    def _technology_card(self, tech: TechnologyCard, idx: int) -> Vertical:
        icon = _server_icon(tech.provider)
        card_id = f"env-card-{idx}"
        self._card_ids.append(card_id)
        self._card_actions.append(f"open_provider_{tech.provider}")

        card = Vertical(
            Static(f"{icon} [bold white]{tech.title}[/]", classes="env-card-title"),
            Static(f"[dim]{tech.subtitle}[/]", classes="env-card-provider"),
            Static(self._provider_status_text(tech.provider), classes="env-card-copy"),
            Button(_("environment.button.open"), id=f"env-btn-{idx}", classes="env-card-button"),
            classes="env-card",
            id=card_id,
        )
        card.can_focus = True
        return card

    def on_mount(self) -> None:
        self._apply_responsive_mode(self.size.width, self.size.height)
        if self._card_ids:
            self.query_one(f"#{self._card_ids[0]}").focus()
        
        if not has_ssh_servers_configured():
            self.notify(
                _("environment.notify.ssh_hint"),
                severity="information",
                timeout=5,
            )

    def on_resize(self, event: Resize) -> None:
        self._apply_responsive_mode(event.size.width, event.size.height)

    def _apply_responsive_mode(self, width: int, height: int) -> None:
        compact = width < 120 or height < 34
        ultra_compact = width < 95 or height < 28
        try:
            root = self.query_one("#env-root", Vertical)
        except Exception:
            return
        if compact:
            root.add_class("compact")
        else:
            root.remove_class("compact")
        if ultra_compact:
            root.add_class("ultra-compact")
        else:
            root.remove_class("ultra-compact")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        try:
            idx = int(btn_id.replace("env-btn-", ""))
            action_name = self._card_actions[idx]
            self._execute_action(action_name)
        except (ValueError, IndexError):
            pass

    def _execute_action(self, action_name: str) -> None:
        if not action_name.startswith("open_provider_"):
            return
        provider_name = action_name.replace("open_provider_", "")

        matches = self._servers_for_provider(provider_name)
        if not matches:
            if self._provider_cli_available(provider_name):
                if provider_name in {"kubernetes", "openshift"}:
                    if self._has_remote_servers:
                        self.notify(
                            _("environment.notify.no_context", provider=provider_name.capitalize()),
                            severity="warning",
                        )
                    else:
                        self.notify(
                            _("environment.notify.no_cluster", provider=provider_name.capitalize()),
                            severity="warning",
                        )
                    return
                self.notify(
                    _("environment.notify.no_servers", provider=provider_name.capitalize()),
                    severity="warning",
                )
                return
            self.notify(
                _("environment.notify.not_installed", provider=provider_name.capitalize()),
                severity="warning",
            )
            return

        provider_server_manager = ServerManager(matches)
        self.app.switch_screen(
            Dashboard(
                provider_server_manager,
                server_label=None,
                root_server_manager=self._server_manager,
            )
        )

    # Navigation
    def action_focus_up(self) -> None:
        self._move_focus(-self._cols())

    def action_focus_down(self) -> None:
        self._move_focus(self._cols())

    def action_focus_left(self) -> None:
        self._move_focus(-1)

    def action_focus_right(self) -> None:
        self._move_focus(1)

    def _cols(self) -> int:
        return min(2, max(1, len(self._card_ids)))

    def _move_focus(self, delta: int) -> None:
        if not self._card_ids:
            return
        focused = self.focused
        if focused is None:
            self.query_one(f"#{self._card_ids[0]}").focus()
            return
        focused_id = focused.id or ""
        if focused_id not in self._card_ids:
            parent = focused.parent
            if parent and parent.id in self._card_ids:
                focused_id = parent.id
            else:
                return
        try:
            idx = self._card_ids.index(focused_id)
        except ValueError:
            return
        new_idx = (idx + delta) % len(self._card_ids)
        self.query_one(f"#{self._card_ids[new_idx]}").focus()

    def action_select_focused(self) -> None:
        if not self._card_ids:
            return
        focused = self.focused
        if focused is None:
            return
        focused_id = focused.id or ""
        if focused_id not in self._card_ids:
            parent = focused.parent
            if parent and parent.id in self._card_ids:
                focused_id = parent.id
            else:
                return
        try:
            idx = self._card_ids.index(focused_id)
        except ValueError:
            return
        action_name = self._card_actions[idx]
        self._execute_action(action_name)

    def action_quit(self) -> None:
        self.app.exit()

    def action_show_welcome_help(self) -> None:
        from .home import HomeScreen

        self.app.switch_screen(HomeScreen(self._server_manager))
