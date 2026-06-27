from __future__ import annotations

import asyncio
import os
import socket
from importlib.resources import files
from pathlib import Path
from typing import Optional

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, ListView, Static, Select

from ..locale import _
from ..config import build_ssh_from_ssh_server, get_configured_ssh_servers
from ..providers.base import ContainerSummary, Provider
from ..providers.docker import DockerProvider
from ..remote.ssh import SSHConnection
from ..server_manager import ServerConnection, ServerManager
from ..utils.helpers import build_report_header, format_timestamp
from ..version import VERSION
from .widgets import ContainerItem, DetailsWidget, LogWidget, StatsWidget


REPORTS_DIR = Path("reports")


class Dashboard(Screen):
    CSS_PATH = files("termainer.ui").joinpath("styles.tcss")

    BINDINGS = [
        Binding("up", "focus_up", _("dashboard.bind.up"), show=True),
        Binding("down", "focus_down", _("dashboard.bind.down"), show=True),
        Binding("enter", "select_container", _("dashboard.bind.select"), show=True),
        Binding("f5", "refresh_list", _("dashboard.bind.refresh"), show=True, priority=True),
        Binding("p", "toggle_pause", _("dashboard.bind.pause_logs"), show=True, priority=True),
        Binding("e", "export_logs", _("dashboard.bind.export"), show=True, priority=True),
        Binding("a", "start_container", _("dashboard.bind.start"), show=True, priority=True),
        Binding("t", "stop_container", _("dashboard.bind.stop"), show=True, priority=True),
        Binding("r", "restart_container", _("dashboard.bind.restart"), show=True, priority=True),
        Binding("delete", "confirm_remove", _("dashboard.bind.delete"), show=True, priority=True),
        Binding("o", "restart_policy", _("dashboard.bind.restart_policy"), show=True, priority=True),
        Binding("c", "exec_cmd", _("dashboard.bind.exec"), show=True, priority=True),
        Binding("escape", "back_to_environment", _("dashboard.bind.back"), show=True, priority=True),
        Binding("q", "quit", _("dashboard.bind.quit"), show=True, priority=True),
    ]

    def __init__(
        self,
        server_manager: ServerManager,
        server_label: Optional[str] = None,
        root_server_manager: Optional[ServerManager] = None,
    ) -> None:
        super().__init__()
        self._server_manager = server_manager
        self._root_server_manager = root_server_manager or server_manager
        self._active_server = server_label
        self._selected_container: Optional[str] = None
        self._selected_info: ContainerSummary = {}
        self._selected_server: Optional[str] = None
        self._log_task: Optional[asyncio.Task] = None
        self._stats_task: Optional[asyncio.Task] = None
        self._compact_mode = False
        self._ultra_compact_mode = False
        self._active_ssh_conn: Optional[SSHConnection] = None  # current SSH connection
        self._saved_docker_host: Optional[str] = None
        self._refresh_request_id = 0

    @property
    def _active_provider(self) -> Optional[Provider]:
        if self._active_server:
            try:
                return self._server_manager.get_provider(self._active_server)
            except KeyError:
                pass
        return self._server_manager.servers[0].provider if self._server_manager.servers else None

    @property
    def _is_kubernetes(self) -> bool:
        prov = self._active_provider
        return prov.name in {"kubernetes", "openshift"} if prov else False

    @property
    def _is_single_server(self) -> bool:
        return self._active_server is not None

    def compose(self) -> ComposeResult:
        resource_label = _("dashboard.resource.pods") if self._is_kubernetes else _("dashboard.resource.containers")

        # Build server selector options if multi-server setup
        server_selector = self._build_server_selector()

        sidebar_children: list = [
            Static(f"[bold white]› {resource_label}[/]    [dim]0[/]", classes="panel-header", id="sidebar-count"),
        ]
        
        if server_selector is not None:
            sidebar_children.append(server_selector)

        server_info = self._build_server_info_label()
        if server_info is not None:
            sidebar_children.append(server_info)
        
        sidebar_children.extend([
            Input(placeholder=_("dashboard.search.placeholder", resource=resource_label.lower()), id="search-input"),
            ListView(id="container-list"),
        ])

        yield Vertical(
            self._top_bar(),
            Horizontal(
                Vertical(*sidebar_children, id="sidebar"),
                Vertical(
                    self._top_panels(),
                    self._logs_panel(),
                    id="workspace",
                ),
                id="dashboard-body",
            ),
            id="dashboard-root",
        )
        yield Footer()

    def _top_bar(self) -> Vertical:
        provider_name = self._active_provider.name.capitalize() if self._active_provider else ""
        mode_suffix = " [dim](ultra)[/]" if self._ultra_compact_mode else (" [dim](compact)[/]" if self._compact_mode else "")
        connection_status = (
            _("dashboard.status.connected", provider=provider_name) + mode_suffix
            if self._active_provider
            else _("dashboard.status.disconnected") + mode_suffix
        )

        brand_row = Horizontal(
            Static(f"[bold #22d3ee][ ][/] [bold #22d3ee]TERMAINER[/] [#5c5c5c]v{VERSION}[/]", id="top-brand"),
            Static(_("dashboard.tagline"), id="top-tagline"),
            Static(connection_status, id="top-status"),
            id="top-bar-row",
        )

        return Vertical(brand_row, id="top-bar")

    def _build_server_selector(self) -> Optional[Select]:
        """Build a Select widget with local servers + SSH aliases from ~/.ssh/config.
        No SSH connections are made here — just reads the config file."""
        ssh_servers = get_configured_ssh_servers()
        total = self._server_manager.server_count + len(ssh_servers)
        if total <= 1 and not ssh_servers:
            return None

        options: list[tuple[str, str]] = []

        # Local servers (already connected)
        for label in self._server_manager.server_labels:
            options.append((f"⬡ {label}", f"local:{label}"))

        # SSH servers from ~/.ssh/config (no connection yet)
        for alias, srv in ssh_servers.items():
            options.append((f"⬢ {srv.display_name}", f"ssh:{alias}"))

        if not options:
            return None

        return Select(options, id="server-selector", classes="server-selector",
                      value=f"local:{self._server_manager.server_labels[0]}" if self._server_manager.server_labels else Select.BLANK)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle server selector changes."""
        if event.control.id != "server-selector" or event.value is Select.BLANK:
            return
        self.run_worker(self._switch_server(str(event.value)))

    def _build_server_info_label(self) -> Optional[Static]:
        """Build a green label showing server hostname and IP/DNS."""
        server = self._active_server or ""
        if not server:
            return None

        if self._active_ssh_conn:
            host = self._active_ssh_conn.host
            return Static(_("dashboard.server_info.ssh", server=escape(server), host=escape(host)), id="server-info")

        hostname = socket.gethostname()
        ip = self._get_local_ip()
        return Static(_("dashboard.server_info.local", hostname=escape(hostname), ip=escape(ip)), id="server-info")

    @staticmethod
    def _get_local_ip() -> str:
        """Get the local IP address that can reach the network."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    async def _switch_server(self, value: str) -> None:
        """Switch active server. For SSH servers, open an SSH tunnel to forward
        the remote Docker socket locally so all docker commands run locally."""
        self._cancel_tasks()
        self._selected_container = None
        self._selected_info = {}
        self._selected_server = None

        # Close previous tunnel if any
        if self._active_ssh_conn:
            await self._active_ssh_conn.close_tunnel()
            self._active_ssh_conn = None
        self._restore_docker_host()

        if value.startswith("local:"):
            label = value[len("local:"):]
            self._active_server = label

        elif value.startswith("ssh:"):
            alias = value[len("ssh:"):]
            ssh_servers = get_configured_ssh_servers()
            if alias not in ssh_servers:
                self.notify(_("dashboard.notify.server_not_found", alias=alias), severity="error")
                return

            ssh_server = ssh_servers[alias]
            ssh_conn = build_ssh_from_ssh_server(ssh_server)

            try:
                tunnel_socket = await ssh_conn.create_tunnel()
            except RuntimeError as e:
                self.notify(_("dashboard.notify.ssh_error", alias=alias, e=str(e)), severity="error")
                return

            self._active_ssh_conn = ssh_conn
            self._saved_docker_host = os.environ.get("DOCKER_HOST")
            os.environ["DOCKER_HOST"] = f"unix://{tunnel_socket}"
            provider = DockerProvider()

            existing = [s for s in self._server_manager.servers if s.label == alias]
            if existing:
                self._server_manager.servers.remove(existing[0])
            self._server_manager.servers.append(
                ServerConnection(label=alias, provider=provider, ssh=ssh_conn)
            )
            self._active_server = alias

        await self._refresh_containers()
        self._update_server_info()

    def _update_server_info(self) -> None:
        """Update the server info label after switching servers."""
        try:
            info_label = self.query_one("#server-info", Static)
            new_label = self._build_server_info_label()
            if new_label:
                info_label.update(new_label.renderable)
        except Exception:
            pass

    def _top_panels(self) -> Horizontal:
        resource_singular = _("dashboard.resource.pod") if self._is_kubernetes else _("dashboard.resource.container")
        details_label = _("dashboard.details.header_pod") if self._is_kubernetes else _("dashboard.details.header_container")
        return Horizontal(
            Vertical(
                Static(f"[bold white]› {details_label}[/]", classes="panel-header", id="details-header"),
                DetailsWidget(_("dashboard.details.placeholder", resource=resource_singular), id="details-content"),
                id="details-panel",
            ),
            Vertical(
                Static(f"[bold white]› {_('dashboard.stats.header')}[/]", classes="panel-header"),
                StatsWidget(id="stats-content"),
                id="stats-panel",
            ),
            id="top-panels",
        )

    def _logs_panel(self) -> Vertical:
        return Vertical(
            Horizontal(
                Static(f"[bold white]› {_('dashboard.logs.header')}[/]", id="logs-title"),
                Static(f"[bold #4ade80]{_('dashboard.logs.live')}[/]", id="logs-live"),
                id="logs-header-row",
            ),
            LogWidget(id="log-content"),
            id="logs-panel",
        )


    def on_mount(self) -> None:
        self._apply_responsive_mode(self.size.width, self.size.height)
        self.run_worker(self._refresh_containers())

    def on_resize(self, event: Resize) -> None:
        self._apply_responsive_mode(event.size.width, event.size.height)

    def _apply_responsive_mode(self, width: int, height: int) -> None:
        compact = width < 180 or height < 48
        ultra_compact = width < 125 or height < 36
        self._compact_mode = compact
        self._ultra_compact_mode = ultra_compact

        root = self.query_one("#dashboard-root", Vertical)
        if compact:
            root.add_class("compact")
        else:
            root.remove_class("compact")

        if ultra_compact:
            root.add_class("ultra-compact")
        else:
            root.remove_class("ultra-compact")

        status = self.query_one("#top-status", Static)
        provider_name = self._active_provider.name.capitalize() if self._active_provider else ""
        mode_suffix = " [dim](ultra)[/]" if ultra_compact else (" [dim](compact)[/]" if compact else "")
        if self._active_provider:
            status.update(_("dashboard.status.connected", provider=provider_name) + mode_suffix)
        else:
            status.update(_("dashboard.status.disconnected") + mode_suffix)

    async def _refresh_containers(self) -> None:
        self._refresh_request_id += 1
        request_id = self._refresh_request_id
        list_view = self.query_one("#container-list", ListView)
        try:
            if self._is_single_server:
                provider = self._server_manager.get_provider(self._active_server)
                containers = await provider.list_containers()
                for c in containers:
                    c["_server"] = self._active_server
            else:
                containers = await self._server_manager.list_all_containers()

            # If another refresh started while this one was awaiting I/O, ignore stale results.
            if request_id != self._refresh_request_id:
                return

            list_view.clear()

            for c in containers:
                list_view.append(ContainerItem(c))
            if containers:
                list_view.index = 0
                list_view.focus()
                first = list_view.highlighted_child
                if isinstance(first, ContainerItem):
                    await self._select_container(first)
            count_label = self.query_one("#sidebar-count", Static)
            resource_label = _("dashboard.resource.pods") if self._is_kubernetes else _("dashboard.resource.containers")
            server_count = self._server_manager.server_count
            suffix = _("dashboard.sidebar.multi_server", count=str(server_count)) if not self._is_single_server and server_count > 1 else ""
            count_label.update(f"[bold white]› {resource_label}[/] [dim]{len(containers)}{suffix}[/]")
        except Exception as e:
            self.notify(_("dashboard.notify.list_error", e=str(e)), severity="error")

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        list_view = self.query_one("#container-list", ListView)
        for item in list_view.children:
            if isinstance(item, ContainerItem):
                name = item.container.get("names") or item.container.get("name") or item.container.get("id", "")
                if isinstance(name, list):
                    name = name[0]
                item.display = query in str(name).lower()

    async def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        item = event.item
        if isinstance(item, ContainerItem):
            await self._select_container(item)

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if not isinstance(item, ContainerItem):
            return
        await self._select_container(item)

    async def _select_container(self, item: ContainerItem) -> None:
        cid = item.container.get("id", "")
        if cid and cid == self._selected_container:
            return
        self._selected_container = cid
        self._selected_info = item.container
        self._selected_server = item.server_label
        await self._update_panels(cid, item.container)

    async def _update_panels(self, container_id: str, container_info: ContainerSummary) -> None:
        provider = self._provider_for(container_info)
        if provider is None:
            return

        details = self.query_one("#details-content", DetailsWidget)
        log_widget = self.query_one("#log-content", LogWidget)
        logs_title = self.query_one("#logs-title", Static)

        name = container_info.get("names") or container_info.get("name") or container_id
        if isinstance(name, list):
            name = name[0]
        logs_title.update(_("dashboard.logs.title", name=escape(str(name))))

        log_widget.clear()
        stats_widget = self.query_one("#stats-content", StatsWidget)
        stats_widget.reset_history()
        self._cancel_tasks()

        try:
            env = await provider.get_env(container_id)
            details.show_details(container_info, env)
        except Exception:
            details.update(f"[red]{_('dashboard.notify.details_error')}[/]")

        self._stats_task = asyncio.create_task(self._stream_stats(container_id))
        self._log_task = asyncio.create_task(self._stream_logs(container_id))

    def _provider_for(self, container: ContainerSummary) -> Optional[Provider]:
        server_label = container.get("_server") or self._active_server
        if server_label:
            try:
                return self._server_manager.get_provider(server_label)
            except KeyError:
                pass
        if self._server_manager.servers:
            return self._server_manager.servers[0].provider
        return None

    async def _stream_stats(self, container_id: str) -> None:
        provider = self._provider_for(self._selected_info)
        if provider is None:
            return
        stats_widget = self.query_one("#stats-content", StatsWidget)
        try:
            async for stat in provider.stats(container_id):
                stats_widget.update_stats(stat)
        except Exception:
            pass

    async def _stream_logs(self, container_id: str) -> None:
        provider = self._provider_for(self._selected_info)
        if provider is None:
            return
        log_widget = self.query_one("#log-content", LogWidget)
        try:
            async for line in provider.logs(container_id, tail=100, follow=True):
                log_widget.append_line(line)
        except Exception:
            log_widget.append_line(f"[dim]{_('dashboard.notify.log_stream_ended')}[/]")

    def _cancel_tasks(self) -> None:
        for task in (self._log_task, self._stats_task):
            if task and not task.done():
                task.cancel()
        self._log_task = None
        self._stats_task = None

    def action_focus_up(self) -> None:
        self._move_list_selection(-1)

    def action_focus_down(self) -> None:
        self._move_list_selection(1)

    def _move_list_selection(self, delta: int) -> None:
        list_view = self.query_one("#container-list", ListView)
        visible_items: list[tuple[int, ContainerItem]] = []
        for idx, child in enumerate(list_view.children):
            if isinstance(child, ContainerItem) and child.display:
                visible_items.append((idx, child))

        if not visible_items:
            return

        highlighted = list_view.highlighted_child
        current_pos = 0
        if isinstance(highlighted, ContainerItem):
            for pos, (_, item) in enumerate(visible_items):
                if item is highlighted:
                    current_pos = pos
                    break

        new_pos = (current_pos + delta) % len(visible_items)
        new_index, _ = visible_items[new_pos]
        list_view.index = new_index

    def action_select_container(self) -> None:
        list_view = self.query_one("#container-list", ListView)
        if list_view.highlighted_child and isinstance(list_view.highlighted_child, ContainerItem):
            self.run_worker(self._select_container(list_view.highlighted_child))

    async def action_refresh_list(self) -> None:
        await self._refresh_containers()

    async def _run_container_action(self, action: str, success_message: str, **kwargs: object) -> None:
        target_container, target_info, target_server = self._current_container_target()
        if not target_container or not target_server:
            self.notify(_("dashboard.notify.select_container"), severity="warning", timeout=3)
            return
        try:
            provider = self._server_manager.get_provider(target_server)
            await getattr(provider, action)(target_container, **kwargs)
            self._selected_container = target_container
            self._selected_info = target_info
            self._selected_server = target_server
            self.notify(success_message, timeout=3)
            await self._refresh_containers()
        except Exception as e:
            self.notify(_("dashboard.notify.action_error", action=action, e=str(e)), severity="error", timeout=5)
        except Exception as e:
            self.notify(_("dashboard.notify.action_error", action=action, e=str(e)), severity="error", timeout=5)

    async def action_start_container(self) -> None:
        await self._run_container_action("start", _("dashboard.action.start_success"))

    async def action_stop_container(self) -> None:
        await self._run_container_action("stop", _("dashboard.action.stop_success"))

    async def action_restart_container(self) -> None:
        await self._run_container_action("restart", _("dashboard.action.restart_success"))

    def action_confirm_remove(self) -> None:
        target_container, target_info, target_server = self._current_container_target()
        if not target_container:
            self.notify(_("dashboard.notify.select_container_remove"), severity="warning", timeout=3)
            return
        self._selected_container = target_container
        self._selected_info = target_info
        self._selected_server = target_server
        container_name = self._container_name(target_info, target_container)
        resource_name = _("dashboard.resource.pod") if self._is_kubernetes else _("dashboard.resource.container")
        self.app.push_screen(
            RemoveContainerModal(container_name=container_name, container_id=target_container, resource_name=resource_name),
            self._remove_container,
        )

    async def _remove_container(self, confirmed: bool) -> None:
        if not confirmed or not self._selected_container:
            return
        await self._run_container_action("remove", _("dashboard.action.remove_success"), force=True)
        self._selected_container = None
        self._selected_info = {}
        self._selected_server = None
        resource_singular = _("dashboard.resource.pod") if self._is_kubernetes else _("dashboard.resource.container")
        self.query_one("#details-content", DetailsWidget).update(_("dashboard.details.placeholder", resource=resource_singular))
        self.query_one("#log-content", LogWidget).clear()

    def action_toggle_pause(self) -> None:
        log_widget = self.query_one("#log-content", LogWidget)
        log_widget.toggle_pause()
        live = self.query_one("#logs-live", Static)
        if log_widget.paused:
            live.update(f"[bold #fbbf24]{_('dashboard.logs.paused')}[/]")
        else:
            live.update(f"[bold #4ade80]{_('dashboard.logs.live')}[/]")
        status = _("dashboard.logs.status_paused") if log_widget.paused else _("dashboard.logs.status_resumed")
        self.notify(_("dashboard.logs.toggle_notify", status=status), timeout=2)

    def action_export_logs(self) -> None:
        log_widget = self.query_one("#log-content", LogWidget)
        content = log_widget.get_content()
        if not content.strip():
            self.notify(_("dashboard.notify.no_logs"), severity="warning", timeout=3)
            return

        cid = self._selected_container or "unknown"
        container_name = self._selected_info.get("names") or self._selected_info.get("name") or cid
        if isinstance(container_name, list):
            container_name = container_name[0]
        image = self._selected_info.get("image", "unknown")

        header = build_report_header(
            container_name=str(container_name),
            image=str(image),
            provider=self._active_provider.name if self._active_provider else "?",
        )
        report = header + content

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"reporte_bug_{format_timestamp()}.txt"
        filepath = REPORTS_DIR / filename

        filepath.write_text(report, encoding="utf-8")
        self.notify(_("dashboard.notify.logs_exported", filepath=str(filepath)), timeout=5)

    def action_quit(self) -> None:
        self._cancel_tasks()
        self._close_active_tunnel()
        self.app.exit()

    def action_restart_policy(self) -> None:
        target_container, target_info, target_server = self._current_container_target()
        if not target_container:
            self.notify(_("dashboard.notify.select_container_policy"), severity="warning", timeout=3)
            return
        self._selected_container = target_container
        self._selected_info = target_info
        self._selected_server = target_server
        try:
            provider = self._server_manager.get_provider(target_server)
        except (KeyError, TypeError):
            provider = self._active_provider
        container_name = self._container_name(target_info, target_container)
        current_policy = str(target_info.get("restartpolicy", target_info.get("restart", "")))
        self.app.push_screen(
            RestartPolicyModal(target_container, container_name, current_policy, provider.name),
            self._apply_restart_policy,
        )

    async def _apply_restart_policy(self, policy: Optional[str]) -> None:
        if not policy or not self._selected_container:
            return
        try:
            provider = self._server_manager.get_provider(self._selected_server)
            await provider.set_restart_policy(self._selected_container, policy)
            self.notify(_("dashboard.notify.policy_changed", policy=policy), timeout=3)
            await self._refresh_containers()
        except Exception as e:
            self.notify(_("dashboard.notify.generic_error", e=str(e)), severity="error", timeout=8)

    def action_exec_cmd(self) -> None:
        target_container, target_info, target_server = self._current_container_target()
        if not target_container:
            self.notify(_("dashboard.notify.select_container_exec"), severity="warning", timeout=3)
            return
        try:
            provider = self._server_manager.get_provider(target_server)
        except (KeyError, TypeError):
            provider = self._active_provider
        container_name = self._container_name(target_info, target_container)
        self.app.push_screen(ExecModal(target_container, container_name, provider))

    def action_back_to_environment(self) -> None:
        self._cancel_tasks()
        self._close_active_tunnel()
        from .environment import EnvironmentScreen
        self.app.switch_screen(EnvironmentScreen(self._root_server_manager))

    def _close_active_tunnel(self) -> None:
        """Close the active SSH tunnel and restore DOCKER_HOST."""
        if self._active_ssh_conn:
            try:
                asyncio.create_task(self._active_ssh_conn.close_tunnel())
            except Exception:
                pass
            self._active_ssh_conn = None
        self._restore_docker_host()

    def _restore_docker_host(self) -> None:
        """Restore the original DOCKER_HOST value before the tunnel was created."""
        if self._saved_docker_host is not None:
            os.environ["DOCKER_HOST"] = self._saved_docker_host
            self._saved_docker_host = None
        else:
            os.environ.pop("DOCKER_HOST", None)

    @staticmethod
    def _container_name(container: ContainerSummary, fallback: str) -> str:
        name = container.get("names") or container.get("name") or fallback
        if isinstance(name, list):
            name = name[0]
        return str(name)

    def _current_container_target(self) -> tuple[Optional[str], ContainerSummary, Optional[str]]:
        if self._selected_container:
            return self._selected_container, self._selected_info, self._selected_server
        list_view = self.query_one("#container-list", ListView)
        item = list_view.highlighted_child
        if isinstance(item, ContainerItem):
            return str(item.container.get("id", "")), item.container, item.server_label
        return None, {}, None


class RemoveContainerModal(ModalScreen[bool]):
    BINDINGS = [
        ("escape", "cancel", _("dashboard.remove_modal.cancel")),
        ("n", "cancel", _("dashboard.remove_modal.cancel")),
        ("enter", "confirm", _("dashboard.remove_modal.confirm")),
        ("y", "confirm", _("dashboard.remove_modal.confirm")),
        ("left", "focus_prev", _("dashboard.bind.up")),
        ("right", "focus_next", _("dashboard.bind.down")),
        ("tab", "focus_next", _("dashboard.bind.down")),
        ("shift+tab", "focus_prev", _("dashboard.bind.up")),
    ]

    def __init__(self, container_name: str, container_id: str, resource_name: str = "") -> None:
        super().__init__()
        self.container_name = container_name
        self.container_id = container_id
        self.resource_name = resource_name

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(_("dashboard.remove_modal.title", resource=escape(self.resource_name)), id="remove-title"),
            Label(_("dashboard.remove_modal.body", name=escape(self.container_name))),
            Label(f"[dim]{escape(self.container_id)}[/]"),
            Static(_("dashboard.remove_modal.warning"), id="remove-warning"),
            Horizontal(
                Button(_("dashboard.remove_modal.cancel"), id="cancel-remove"),
                Button(_("dashboard.remove_modal.confirm"), variant="error", id="confirm-remove"),
                id="remove-actions",
            ),
            id="remove-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-remove":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def on_mount(self) -> None:
        self.query_one("#cancel-remove", Button).focus()

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_focus_next(self) -> None:
        focused = self.focused
        if focused and focused.id == "cancel-remove":
            self.query_one("#confirm-remove", Button).focus()
        else:
            self.query_one("#cancel-remove", Button).focus()

    def action_focus_prev(self) -> None:
        self.action_focus_next()


class RestartPolicyModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", _("dashboard.policy_modal.cancel")),
    ]

    _POLICIES: dict = {
        "docker":     ["no", "always", "on-failure", "unless-stopped"],
        "podman":     ["no", "always", "on-failure", "unless-stopped"],
        "kubernetes": ["Always", "OnFailure", "Never"],
        "openshift":  ["Always", "OnFailure", "Never"],
        "swarm":      ["none", "on-failure", "any"],
    }

    def __init__(self, container_id: str, container_name: str, current_policy: str, provider_name: str) -> None:
        super().__init__()
        self._container_id = container_id
        self._container_name = container_name
        self._current_policy = current_policy
        self._provider_name = provider_name
        self._policies = self._POLICIES.get(provider_name, self._POLICIES["docker"])

    def compose(self) -> ComposeResult:
        options = [(p, p) for p in self._policies]
        current = self._current_policy if self._current_policy in self._policies else self._policies[0]
        yield Vertical(
            Static(f"[bold #22d3ee]{_('dashboard.policy_modal.title')}[/]", id="policy-title"),
            Static(_("dashboard.policy_modal.container", name=escape(self._container_name))),
            Static(_("dashboard.policy_modal.current", policy=escape(self._current_policy or _("dashboard.policy_modal.undefined")))),
            Select(options, value=current, id="policy-select"),
            Horizontal(
                Button(_("dashboard.policy_modal.cancel"), id="cancel-policy"),
                Button(_("dashboard.policy_modal.apply"), variant="success", id="apply-policy"),
                id="policy-actions",
            ),
            id="policy-modal",
        )

    def on_mount(self) -> None:
        self.query_one("#policy-select", Select).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "apply-policy":
            select = self.query_one("#policy-select", Select)
            value = select.value
            self.dismiss(str(value) if value is not Select.BLANK else None)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class ExecModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "close_exec", _("dashboard.exec_modal.close")),
    ]

    def __init__(self, container_id: str, container_name: str, provider) -> None:
        super().__init__()
        self._container_id = container_id
        self._container_name = container_name
        self._provider = provider

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(
                _("dashboard.exec_modal.title", name=escape(self._container_name)),
                id="exec-title",
            ),
            Horizontal(
                Input(placeholder=_("dashboard.exec_modal.placeholder"), id="exec-input"),
                Button(_("dashboard.exec_modal.run"), id="run-exec", variant="success"),
                id="exec-input-row",
            ),
            LogWidget(id="exec-output"),
            Button(_("dashboard.exec_modal.close"), id="close-exec-btn"),
            id="exec-modal",
        )

    def on_mount(self) -> None:
        self.query_one("#exec-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "exec-input":
            self._launch(event.value.strip())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-exec":
            self._launch(self.query_one("#exec-input", Input).value.strip())
        elif event.button.id == "close-exec-btn":
            self.dismiss()

    def _launch(self, command: str) -> None:
        if not command:
            return
        self.run_worker(self._run_command(command))

    async def _run_command(self, command: str) -> None:
        output = self.query_one("#exec-output", LogWidget)
        output.clear()
        output.append_line(_("dashboard.exec_modal.prompt", command=escape(command)))
        try:
            async for line in self._provider.exec_command(self._container_id, command):
                output.append_line(escape(line) if line else "")
            output.append_line(f"[dim #5c5c5c]{_('dashboard.exec_modal.end')}[/]")
        except Exception as e:
            output.append_line(_("dashboard.exec_modal.error", error=escape(str(e))))

    def action_close_exec(self) -> None:
        self.dismiss()
