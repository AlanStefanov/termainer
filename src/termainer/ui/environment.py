from __future__ import annotations

import asyncio
from dataclasses import dataclass
import shutil
from typing import Dict, List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.events import Resize
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, Static

from ..config import build_ssh_from_ssh_server
from ..locale import _
from ..server_manager import ServerConnection, ServerManager, provider_class_for
from ..ssh_config import SSHServer
from ..storage import (
    get_all_ssh_servers,
    get_cached_aliases,
    has_any_ssh_servers,
    load_user_servers,
    remove_user_server,
    save_provider_servers_cache,
    save_user_server,
)
from ..version import VERSION_DISPLAY
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

HEALTH_CHECKS = {
    "docker": ["docker", "info"],
    "swarm": ["docker", "info"],
    "kubernetes": ["kubectl", "cluster-info"],
    "podman": ["podman", "info"],
    "openshift": ["oc", "whoami"],
}


class ConfirmQuitModal(ModalScreen[bool]):
    """Modal asking the user to confirm they want to quit the app."""

    BINDINGS = [
        Binding("escape", "no", _("environment.modal.no"), priority=True),
        Binding("left", "focus_previous", "", priority=True),
        Binding("right", "focus_next", "", priority=True),
        Binding("enter", "press_focused", _("dashboard.bind.select"), priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Vertical(
                Static(_("environment.modal.quit_title"), id="confirm-quit-title"),
                Horizontal(
                    Button(_("environment.modal.no"), id="btn-quit-no", variant="primary"),
                    Button(_("environment.modal.yes"), id="btn-quit-yes", variant="error"),
                    id="confirm-quit-actions",
                ),
                id="confirm-quit-modal",
            ),
            id="confirm-quit-root",
        )

    def on_mount(self) -> None:
        self.query_one("#btn-quit-no", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-quit-yes")

    def action_no(self) -> None:
        self.dismiss(False)

    def action_press_focused(self) -> None:
        btn = self.focused
        if isinstance(btn, Button) and btn.id:
            self.dismiss(btn.id == "btn-quit-yes")


class ConnectingModal(ModalScreen[None]):
    """Loading screen with ▶→✓ animation while probing SSH servers."""

    BINDINGS = []

    def __init__(self, provider: str) -> None:
        super().__init__()
        self._provider = provider

    def compose(self) -> ComposeResult:
        yield Center(
            Vertical(
                Static(
                    _("environment.modal.connecting_brand"),
                    id="conn-brand",
                ),
                Static("", id="conn-messages"),
                id="conn-panel",
            ),
            id="conn-root",
        )

    def on_mount(self) -> None:
        self._done = False
        self._lines: list[str] = []
        self._n = 0
        self._text = _("environment.modal.connecting_text", provider=self._provider)
        self.set_interval(0.15, self._tick)

    def _tick(self) -> None:
        if self._done:
            return
        self._n = (self._n % 4) + 1
        dots = "." * self._n
        line = f"  [#22d3ee]▶[/]  {self._text}[dim]{dots}[/]"
        if not self._lines:
            self._lines.append(line)
        else:
            self._lines[-1] = line
        try:
            self.query_one("#conn-messages", Static).update("\n".join(self._lines))
        except Exception:
            pass

    def on_unmount(self) -> None:
        self._done = True

    def dismiss(self, result: None = None) -> None:
        self._done = True
        super().dismiss(result)


class ServerSelectionModal(ModalScreen[Optional[List[str]]]):
    """Modal with server toggle rows to select which SSH servers to probe."""

    BINDINGS = [
        Binding("up", "previous_toggle", _("environment.bind.up"), priority=True),
        Binding("down", "next_toggle", _("environment.bind.down"), priority=True),
        Binding("space", "toggle_focused", _("environment.modal.toggle"), priority=True),
        Binding("enter", "confirm", _("environment.modal.connect_label"), priority=True),
        Binding("escape", "dismiss_none", _("environment.bind.back"), priority=True),
        Binding("q", "show_quit_confirm", _("environment.bind.quit"), priority=True),
    ]

    def __init__(self, provider_name: str, servers: Dict[str, SSHServer]) -> None:
        super().__init__()
        self._provider = provider_name
        self._toggles = {alias: alias in get_cached_aliases(provider_name) for alias in servers}
        self._labels = {
            alias: f"{srv.display_name}  [dim]({'SSH config' if srv.source == 'ssh_config' else 'App config'})[/]"
            for alias, srv in servers.items()
        }

    def compose(self) -> ComposeResult:
        servers = list(self._toggles.keys())

        rows = [
            Button(
                f"[{'✓' if self._toggles[alias] else ' '}] {self._labels[alias]}",
                id=f"tog-{alias}",
                classes="server-toggle",
            )
            for alias in servers
        ] or [Static(_("environment.modal.no_servers"), id="sel-empty")]

        yield Vertical(
            Static(_("environment.modal.prompt", provider=self._provider.capitalize()), id="sel-title"),
            Horizontal(
                Vertical(
                    Vertical(*rows, id="sel-list"),
                    id="sel-body-left",
                ),
                Vertical(
                    Static("[bold]📋 " + _("environment.modal.info_legend") + "[/]", id="info-legend-title"),
                    Static(_("environment.modal.info_ssh_config"), id="info-ssh-config"),
                    Static(_("environment.modal.info_app_config"), id="info-app-config"),
                    Static("[bold]➕ " + _("environment.modal.info_howto_title") + "[/]", id="info-howto-title"),
                    Static(_("environment.modal.info_howto"), id="info-howto"),
                    Static(_("environment.modal.info_thanks", version=VERSION_DISPLAY), id="info-thanks"),
                    Static("[dim]" + _("environment.modal.info_feedback") + "[/]", id="info-feedback"),
                    id="sel-body-right",
                ),
                id="sel-body",
            ),
            Horizontal(
                Button(_("environment.modal.manage"), id="btn-manage-servers"),
                Button(_("environment.modal.connect", count="0"), id="btn-connect", variant="primary", disabled=True),
                id="sel-actions",
            ),
            Footer(),
            id="selection-modal",
        )

    def on_mount(self) -> None:
        self._update_connect_button()
        try:
            first = self.query_one(".server-toggle", Button)
            self.set_focus(first)
        except Exception:
            pass
        self._apply_responsive()

    def on_resize(self, event: Resize) -> None:
        self._apply_responsive()

    def _apply_responsive(self) -> None:
        width = self.size.width
        term = self.query_one("#selection-modal", Vertical)
        if width < 100:
            term.add_class("-compact")
        else:
            term.remove_class("-compact")

    def _update_connect_button(self) -> None:
        count = sum(1 for c in self._toggles.values() if c)
        btn = self.query_one("#btn-connect", Button)
        btn.label = _("environment.modal.connect", count=str(count))
        btn.disabled = count == 0

    def _toggle_alias(self, alias: str) -> None:
        self._toggles[alias] = not self._toggles[alias]
        prefix = "✓" if self._toggles[alias] else " "
        btn = self.query_one(f"#tog-{alias}", Button)
        btn.label = f"[{prefix}] {self._labels[alias]}"
        self._update_connect_button()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("tog-"):
            self._toggle_alias(btn_id.replace("tog-", ""))
        elif btn_id == "btn-connect":
            selected = [a for a, c in self._toggles.items() if c]
            self.dismiss(selected)
        elif btn_id == "btn-manage-servers":
            self.app.push_screen(ManageServersModal())

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def action_toggle_focused(self) -> None:
        focused = self.focused
        if not focused:
            return
        btn_id = getattr(focused, "id", None) or ""
        if btn_id.startswith("tog-"):
            self._toggle_alias(btn_id.replace("tog-", ""))
            self.set_focus(focused)
        elif btn_id == "btn-connect":
            selected = [a for a, c in self._toggles.items() if c]
            self.dismiss(selected)
        elif btn_id == "btn-manage-servers":
            self.app.push_screen(ManageServersModal())

    def action_confirm(self) -> None:
        focused = self.focused
        if focused and getattr(focused, "id", None) == "btn-manage-servers":
            self.app.push_screen(ManageServersModal())
            return
        selected = [a for a, c in self._toggles.items() if c]
        if selected:
            self.dismiss(selected)

    def action_previous_toggle(self) -> None:
        toggles = list(self.query(".server-toggle"))
        if not toggles:
            return
        focused = self.focused
        if focused in toggles:
            idx = toggles.index(focused)
            self.set_focus(toggles[idx - 1])  # wraps with negative index
        else:
            self.set_focus(toggles[-1])

    def action_next_toggle(self) -> None:
        toggles = list(self.query(".server-toggle"))
        if not toggles:
            return
        focused = self.focused
        if focused in toggles:
            idx = toggles.index(focused)
            self.set_focus(toggles[(idx + 1) % len(toggles)])
        else:
            self.set_focus(toggles[0])

    def action_show_quit_confirm(self) -> None:
        self.app.push_screen(ConfirmQuitModal(), self._on_quit_result)

    def _on_quit_result(self, confirmed: bool) -> None:
        if confirmed:
            self.app.exit()


class ManageServersModal(ModalScreen[None]):
    """Modal to view, add, and remove user-configured SSH servers."""

    BINDINGS = [
        Binding("escape", "_close", _("environment.bind.back"), priority=True),
        Binding("q", "show_quit_confirm", _("environment.bind.quit"), priority=True),
    ]

    def compose(self) -> ComposeResult:
        from_ssh = get_all_ssh_servers()
        user_servers = load_user_servers()

        yield Vertical(
            Static(_("environment.manage.title"), id="manage-title"),
            Vertical(
                *[
                    Horizontal(
                        Static(
                            f"{alias}  [dim]({srv.hostname})  ({_('environment.manage.from_ssh' if srv.source == 'ssh_config' else 'environment.manage.from_app')})[/]"
                        ),
                        id=f"mng-row-{alias}",
                    )
                    for alias, srv in from_ssh.items()
                    if srv.source == "ssh_config"
                ],
                *[
                    Horizontal(
                        Static(f"{alias}  [dim]({srv.hostname})  ({_('environment.manage.from_app')})[/]"),
                        Button(_("environment.manage.remove"), id=f"mng-rm-{alias}", variant="error"),
                        id=f"mng-row-{alias}",
                    )
                    for alias, srv in user_servers.items()
                ]
                or [Static(_("environment.modal.no_servers"))],
                id="manage-list",
            ),
            Horizontal(
                Button(_("environment.manage.add"), id="btn-add-server"),
                Button(_("environment.manage.close"), id="btn-close-manage", variant="primary"),
                id="manage-actions",
            ),
            Footer(),
            id="manage-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-add-server":
            self.app.push_screen(AddServerModal(), lambda r: self._on_add(r))
        elif event.button.id == "btn-close-manage":
            self.dismiss()
        elif event.button.id and event.button.id.startswith("mng-rm-"):
            alias = event.button.id.replace("mng-rm-", "")
            remove_user_server(alias)
            self.notify(_("environment.notify.server_removed", alias=alias))
            self.recompose()

    def _on_add(self, result: Optional[str]) -> None:
        if result:
            self.notify(_("environment.notify.server_added", alias=result))
            self.recompose()

    def action_close(self) -> None:
        self.dismiss()

    def action_show_quit_confirm(self) -> None:
        self.app.push_screen(ConfirmQuitModal(), self._on_quit_result)

    def _on_quit_result(self, confirmed: bool) -> None:
        if confirmed:
            self.app.exit()


class AddServerModal(ModalScreen[Optional[str]]):
    """Form to add a new SSH server."""

    BINDINGS = [
        Binding("escape", "dismiss_none", _("environment.bind.back"), priority=True),
        Binding("q", "show_quit_confirm", _("environment.bind.quit"), priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(_("environment.manage.add_title"), id="add-title"),
            Label(_("environment.manage.add_alias")),
            Input(placeholder="ej: my-server", id="add-alias"),
            Label(_("environment.manage.add_host")),
            Input(placeholder="192.168.1.100", id="add-host"),
            Label(_("environment.manage.add_user")),
            Input(placeholder="root", id="add-user"),
            Label(_("environment.manage.add_port")),
            Input(placeholder="22", id="add-port"),
            Label(_("environment.manage.add_key")),
            Input(placeholder="/path/to/id_rsa", id="add-key"),
            Horizontal(
                Button(_("environment.manage.add_cancel"), id="btn-cancel-add"),
                Button(_("environment.manage.add_save"), id="btn-save-add", variant="primary"),
                id="add-actions",
            ),
            Footer(),
            id="add-modal",
        )

    def on_mount(self) -> None:
        self.query_one("#add-alias", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-add":
            alias = self.query_one("#add-alias", Input).value.strip()
            hostname = self.query_one("#add-host", Input).value.strip()
            if not alias or not hostname:
                return
            user = self.query_one("#add-user", Input).value.strip() or None
            port_str = self.query_one("#add-port", Input).value.strip()
            port = int(port_str) if port_str else 22
            key_path = self.query_one("#add-key", Input).value.strip() or None
            save_user_server(alias, hostname, user, port, key_path)
            self.dismiss(alias)
        elif event.button.id == "btn-cancel-add":
            self.dismiss(None)

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def action_show_quit_confirm(self) -> None:
        self.app.push_screen(ConfirmQuitModal(), self._on_quit_result)

    def _on_quit_result(self, confirmed: bool) -> None:
        if confirmed:
            self.app.exit()


class EnvironmentScreen(Screen):
    BINDINGS = [
        Binding("up", "focus_up", _("environment.bind.up"), priority=True),
        Binding("down", "focus_down", _("environment.bind.down"), priority=True),
        Binding("left", "focus_left", _("environment.bind.left"), priority=True),
        Binding("right", "focus_right", _("environment.bind.right"), priority=True),
        Binding("enter", "select_focused", _("environment.bind.select"), priority=True),
        Binding("?", "show_welcome_help", _("environment.bind.help"), priority=True),
        Binding("h", "show_welcome_help", _("environment.bind.help"), priority=True),
        Binding("q", "show_quit_confirm", _("environment.bind.quit"), priority=True),
    ]

    def action_show_quit_confirm(self) -> None:
        self.app.push_screen(ConfirmQuitModal(), self._on_quit_result)

    def _on_quit_result(self, confirmed: bool) -> None:
        if confirmed:
            self.app.exit()

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
            Static(f"[bold #22d3ee]TERMAINER[/] [#808080]v{VERSION_DISPLAY}[/]", id="env-brand"),
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
        
        if not has_any_ssh_servers():
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
            servers = get_all_ssh_servers()
            if servers:
                self.app.push_screen(
                    ServerSelectionModal(provider_name, servers),
                    lambda aliases: self._on_server_selected(aliases, provider_name)
                )
                return
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

    def _on_server_selected(self, aliases: Optional[List[str]], provider_name: str) -> None:
        if not aliases:
            return
        self.app.push_screen(ConnectingModal(provider_name))
        self.run_worker(self._probe_servers(aliases, provider_name))

    async def _probe_servers(self, aliases: List[str], provider_name: str) -> None:
        health_check = HEALTH_CHECKS.get(provider_name, [provider_name])
        servers = get_all_ssh_servers()
        successful: List[ServerConnection] = []

        async def probe_one(alias: str) -> Optional[ServerConnection]:
            srv = servers.get(alias)
            if not srv:
                return None
            ssh = build_ssh_from_ssh_server(srv)
            try:
                await ssh.run(health_check)
                provider_cls = provider_class_for(provider_name)
                provider_inst = provider_cls(ssh=ssh)
                return ServerConnection(label=alias, provider=provider_inst, ssh=ssh)
            except RuntimeError:
                return None

        results = await asyncio.gather(*[probe_one(a) for a in aliases])

        for alias, conn in zip(aliases, results):
            if conn is not None:
                successful.append(conn)
                self.notify(
                    _("environment.modal.success", provider=provider_name.capitalize(), server=alias),
                    timeout=3,
                )
            else:
                self.notify(
                    _("environment.modal.fail", server=alias, provider=provider_name.capitalize()),
                    severity="warning",
                    timeout=3,
                )

        save_provider_servers_cache(provider_name, [c.label for c in successful])

        if not successful:
            self.notify(
                _("environment.notify.ssh_probe_not_found", provider=provider_name.capitalize()),
                severity="warning",
            )
            self.app.pop_screen()
            return

        self.app.switch_screen(
            Dashboard(
                ServerManager(successful),
                server_label=successful[0].label,
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

    def action_show_welcome_help(self) -> None:
        from .home import HomeScreen

        self.app.switch_screen(HomeScreen(self._server_manager))
