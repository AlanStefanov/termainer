from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Input, Label, ListView, Static

from ..providers.base import ContainerSummary, Provider
from ..server_manager import ServerManager
from ..utils.helpers import build_report_header, format_timestamp
from ..version import VERSION
from .widgets import ContainerItem, DetailsWidget, LogWidget, StatsWidget


REPORTS_DIR = Path("reports")


class Dashboard(Screen):
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("up", "focus_up", "↑"),
        ("down", "focus_down", "↓"),
        ("enter", "select_container", "Select"),
        Binding("r", "refresh_list", "Refresh", priority=True),
        Binding("p", "toggle_pause", "Pause Logs", priority=True),
        Binding("e", "export_logs", "Export", priority=True),
        Binding("x", "export_logs", "Export", priority=True),
        Binding("a", "start_container", "Start", priority=True),
        Binding("t", "stop_container", "Stop", priority=True),
        Binding("R", "restart_container", "Restart", priority=True),
        Binding("delete", "confirm_remove", "Remove", priority=True),
        Binding("b", "back_to_environment", "Back", priority=True),
        Binding("escape", "back_to_environment", "Back", priority=True),
        Binding("?", "show_help", "Help", priority=True),
        Binding("q", "quit", "Quit", priority=True),
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

    @property
    def _active_provider(self) -> Provider:
        if self._active_server:
            return self._server_manager.get_provider(self._active_server)
        return self._server_manager.servers[0].provider if self._server_manager.servers else None

    @property
    def _is_kubernetes(self) -> bool:
        prov = self._active_provider
        return prov.name in {"kubernetes", "openshift"} if prov else False

    @property
    def _is_single_server(self) -> bool:
        return self._active_server is not None

    def compose(self) -> ComposeResult:
        resource_label = "PODS" if self._is_kubernetes else "CONTENEDORES"

        yield Vertical(
            self._top_bar(),
            Horizontal(
                Vertical(
                    Static(f"[bold white]› {resource_label}[/]    [dim]0[/]", classes="panel-header", id="sidebar-count"),
                    Input(placeholder=f"Buscar {resource_label.lower()}...", id="search-input"),
                    ListView(id="container-list"),
                    Static(
                        "[bold cyan]↑/↓[/] Navegar     [bold cyan]Enter[/] Seleccionar\n"
                        "[bold cyan]r[/] Refrescar     [bold cyan]b[/] Atrás     [bold cyan]q[/] Salir",
                        id="sidebar-help",
                    ),
                    id="sidebar",
                ),
                Vertical(
                    self._top_panels(),
                    self._logs_panel(),
                    id="workspace",
                ),
                id="dashboard-body",
            ),
            self._footer(),
            id="dashboard-root",
        )

    def _top_bar(self) -> Vertical:
        provider_name = self._active_provider.name.capitalize() if self._active_provider else "Provider"
        connection_status = (
            f"[bold green]● {provider_name}: connected[/]"
            if self._active_provider
            else "[bold yellow]● Sin conexión[/]"
        )

        brand_row = Horizontal(
            Static("[bold green][ ][/] [bold green]TERMAINER[/] [cyan]v0.1.0[/]", id="top-brand"),
            Static("Todo lo que necesitas saber de TODOS tus contenedores en una sola terminal", id="top-tagline"),
            Static(connection_status, id="top-status"),
            id="top-bar-row",
        )

        children: list[Horizontal] = [brand_row]

        if self._server_manager.server_count > 1:
            server_tabs: list[Button] = []
            server_tabs.append(Button("▣ Todos" if self._active_server is None else "□ Todos", id="tab-all", classes="server-tab"))
            for label in self._server_manager.server_labels:
                active_label = f"▣ {label}" if label == self._active_server else f"□ {label}"
                server_tabs.append(Button(active_label, id=f"tab-{label}", classes="server-tab"))
            children.append(Horizontal(*server_tabs, id="server-tabs"))

        return Vertical(*children, id="top-bar")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not event.button.id:
            return
        if event.button.id == "tab-all":
            self._switch_server(None)
        elif event.button.id.startswith("tab-"):
            label = event.button.id[4:]
            if label in self._server_manager.server_labels:
                self._switch_server(label)

    def _switch_server(self, label: Optional[str]) -> None:
        if label == self._active_server:
            return
        self._cancel_tasks()
        self._active_server = label
        self._selected_container = None
        self._selected_info = {}
        self._selected_server = None
        server_tabs = self.query_one("#server-tabs", Horizontal)
        server_tabs.remove()
        new_tabs = self._build_server_tabs()
        self.query_one("#top-bar", Vertical).mount(new_tabs, before=1)
        self.run_worker(self._refresh_containers())

    def _build_server_tabs(self) -> Horizontal:
        server_tabs: list[Button] = []
        server_tabs.append(Button("▣ Todos" if self._active_server is None else "□ Todos", id="tab-all", classes="server-tab"))
        for label in self._server_manager.server_labels:
            active_label = f"▣ {label}" if label == self._active_server else f"□ {label}"
            server_tabs.append(Button(active_label, id=f"tab-{label}", classes="server-tab"))
        return Horizontal(*server_tabs, id="server-tabs")

    def _top_panels(self) -> Horizontal:
        resource_singular = "pod" if self._is_kubernetes else "contenedor"
        details_label = "DETALLES DEL POD" if self._is_kubernetes else "DETALLES DEL CONTENEDOR"
        return Horizontal(
            Vertical(
                Static(f"[bold white]› {details_label}[/]", classes="panel-header", id="details-header"),
                DetailsWidget(f"(Selecciona un {resource_singular})", id="details-content"),
                id="details-panel",
            ),
            Vertical(
                Static("[bold white]› ESTADÍSTICAS EN TIEMPO REAL[/]", classes="panel-header"),
                StatsWidget(id="stats-content"),
                id="stats-panel",
            ),
            id="top-panels",
        )

    def _logs_panel(self) -> Vertical:
        return Vertical(
            Horizontal(
                Static("[bold white]› LOGS[/] [dim](Selecciona un contenedor)[/]", id="logs-title"),
                Static("[bold green]● LIVE[/]", id="logs-live"),
                id="logs-header-row",
            ),
            LogWidget(id="log-content"),
            id="logs-panel",
        )

    def _footer(self) -> Horizontal:
        delete_label = "Delete" if self._is_kubernetes else "Remove"
        controls = [
            Static("[reverse] p [/reverse] [bold white]Pausar Logs[/]", classes="footer-key"),
            Static("[reverse] e [/reverse] [bold white]Exportar Logs[/]", classes="footer-key"),
            Static("[reverse] d [/reverse] [bold white]Detalles[/]", classes="footer-key footer-extended"),
            Static("[reverse] s [/reverse] [bold white]Stats[/]", classes="footer-key footer-extended"),
            Static("[reverse] n [/reverse] [bold white]Siguiente Panel[/]", classes="footer-key footer-extended"),
            Static("[reverse] ←/→ [/reverse] [bold white]Cambiar Panel[/]", classes="footer-key footer-extended"),
        ]
        if not self._is_kubernetes:
            controls.extend([
                Static("[reverse] a [/reverse] [bold white]Start[/]", classes="footer-key"),
                Static("[reverse] t [/reverse] [bold white]Stop[/]", classes="footer-key"),
                Static("[reverse] R [/reverse] [bold white]Restart[/]", classes="footer-key"),
            ])
        controls.extend([
            Static(f"[red reverse] Del [/reverse] [bold red]{delete_label}[/]", classes="footer-key danger-key"),
            Static("[reverse] r [/reverse] [bold white]Refrescar[/]", classes="footer-key"),
            Static("[reverse] b [/reverse] [bold white]Atrás[/]", classes="footer-key"),
            Static("[reverse] q [/reverse] [bold white]Salir[/]", classes="footer-key"),
            Static(VERSION, id="footer-version"),
        ])
        return Horizontal(*controls, id="bottom-bar")

    def on_mount(self) -> None:
        self._apply_responsive_mode(self.size.width, self.size.height)
        self.run_worker(self._refresh_containers())

    def on_resize(self, event: Resize) -> None:
        self._apply_responsive_mode(event.size.width, event.size.height)

    def _apply_responsive_mode(self, width: int, height: int) -> None:
        compact = width < 150 or height < 42
        ultra_compact = width < 110 or height < 32
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

    async def _refresh_containers(self) -> None:
        list_view = self.query_one("#container-list", ListView)
        list_view.clear()
        try:
            if self._is_single_server:
                provider = self._server_manager.get_provider(self._active_server)
                containers = await provider.list_containers()
                for c in containers:
                    c["_server"] = self._active_server
            else:
                containers = await self._server_manager.list_all_containers()

            for c in containers:
                list_view.append(ContainerItem(c))
            if containers:
                list_view.index = 0
                list_view.focus()
                first = list_view.highlighted_child
                if isinstance(first, ContainerItem):
                    await self._select_container(first)
            count_label = self.query_one("#sidebar-count", Static)
            resource_label = "PODS" if self._is_kubernetes else "CONTENEDORES"
            server_count = self._server_manager.server_count
            suffix = f" (de {server_count} servidores)" if not self._is_single_server and server_count > 1 else ""
            count_label.update(f"[bold white]› {resource_label}[/] [dim]{len(containers)}{suffix}[/]")
        except Exception as e:
            self.notify(f"Error listing containers: {e}", severity="error")

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
        logs_title.update(
            f"[bold white]› LOGS[/] [dim]({escape(str(name))}) - Presiona 'p' para pausar, 'e' para exportar[/]"
        )

        log_widget.clear()
        stats_widget = self.query_one("#stats-content", StatsWidget)
        stats_widget.reset_history()
        self._cancel_tasks()

        try:
            env = await provider.get_env(container_id)
            details.show_details(container_info, env)
        except Exception:
            details.update("[red]Error loading details[/]")

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
            log_widget.append_line("[dim][error: log stream ended][/]")

    def _cancel_tasks(self) -> None:
        for task in (self._log_task, self._stats_task):
            if task and not task.done():
                task.cancel()
        self._log_task = None
        self._stats_task = None

    def action_focus_up(self) -> None:
        list_view = self.query_one("#container-list", ListView)
        list_view.action_previous()

    def action_focus_down(self) -> None:
        list_view = self.query_one("#container-list", ListView)
        list_view.action_next()

    def action_select_container(self) -> None:
        list_view = self.query_one("#container-list", ListView)
        if list_view.highlighted_child and isinstance(list_view.highlighted_child, ContainerItem):
            self.run_worker(self._select_container(list_view.highlighted_child))

    async def action_refresh_list(self) -> None:
        await self._refresh_containers()

    async def _run_container_action(self, action: str, success_message: str, **kwargs: object) -> None:
        target_container, target_info, target_server = self._current_container_target()
        if not target_container or not target_server:
            self.notify("Selecciona un contenedor primero", severity="warning", timeout=3)
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
            self.notify(f"Error ejecutando {action}: {e}", severity="error", timeout=5)

    async def action_start_container(self) -> None:
        await self._run_container_action("start", "Contenedor iniciado")

    async def action_stop_container(self) -> None:
        await self._run_container_action("stop", "Contenedor detenido")

    async def action_restart_container(self) -> None:
        await self._run_container_action("restart", "Contenedor reiniciado")

    def action_confirm_remove(self) -> None:
        target_container, target_info, target_server = self._current_container_target()
        if not target_container:
            self.notify("Selecciona un contenedor primero", severity="warning", timeout=3)
            return
        self._selected_container = target_container
        self._selected_info = target_info
        self._selected_server = target_server
        container_name = self._container_name(target_info, target_container)
        resource_name = "pod" if self._is_kubernetes else "contenedor"
        self.app.push_screen(
            RemoveContainerModal(container_name=container_name, container_id=target_container, resource_name=resource_name),
            self._remove_container,
        )

    async def _remove_container(self, confirmed: bool) -> None:
        if not confirmed or not self._selected_container:
            return
        await self._run_container_action("remove", "Contenedor eliminado", force=True)
        self._selected_container = None
        self._selected_info = {}
        self._selected_server = None
        self.query_one("#details-content", DetailsWidget).update("(Selecciona un pod)" if self._is_kubernetes else "(Selecciona un contenedor)")
        self.query_one("#log-content", LogWidget).clear()

    def action_toggle_pause(self) -> None:
        log_widget = self.query_one("#log-content", LogWidget)
        log_widget.toggle_pause()
        live = self.query_one("#logs-live", Static)
        if log_widget.paused:
            live.update("[bold yellow]⏸ PAUSED[/]")
        else:
            live.update("[bold green]● LIVE[/]")
        status = "paused" if log_widget.paused else "resumed"
        self.notify(f"Logs {status}", timeout=2)

    def action_export_logs(self) -> None:
        log_widget = self.query_one("#log-content", LogWidget)
        content = log_widget.get_content()
        if not content.strip():
            self.notify("No logs to export", severity="warning", timeout=3)
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
        self.notify(f"Logs exported to {filepath}", timeout=5)

    def action_quit(self) -> None:
        self._cancel_tasks()
        self.app.exit()

    def action_show_help(self) -> None:
        self.push_screen(HelpModal())

    def action_back_to_environment(self) -> None:
        self._cancel_tasks()
        from .environment import EnvironmentScreen
        self.app.switch_screen(EnvironmentScreen(self._root_server_manager))

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
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, container_name: str, container_id: str, resource_name: str = "contenedor") -> None:
        super().__init__()
        self.container_name = container_name
        self.container_id = container_id
        self.resource_name = resource_name

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(f"[bold red]Eliminar {escape(self.resource_name)}[/]", id="remove-title"),
            Label(f"Vas a eliminar [bold white]{escape(self.container_name)}[/]"),
            Label(f"[dim]{escape(self.container_id)}[/]"),
            Static("Esta acción no se puede deshacer.", id="remove-warning"),
            Horizontal(
                Button("Cancelar", id="cancel-remove"),
                Button("Eliminar", variant="error", id="confirm-remove"),
                id="remove-actions",
            ),
            id="remove-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-remove":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        self.dismiss(False)


class HelpModal(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss_help", "Close", priority=True),
        Binding("q", "dismiss_help", "Close", priority=True),
        Binding("?", "dismiss_help", "Close", priority=True),
        Binding("enter", "dismiss_help", "Close", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("[bold yellow]Atajos de Teclado[/]", id="remove-title"),
            Static(
                "[bold]Entorno[/]\n"
                "  [reverse] ←/↑/↓/→ [/reverse] Navegar entre servidores\n"
                "  [reverse] Enter [/reverse] Seleccionar servidor\n\n"
                "[bold]Dashboard[/]\n"
                "  [reverse] ↑/↓ [/reverse] Navegar contenedores\n"
                "  [reverse] Enter [/reverse] Seleccionar contenedor\n"
                "  [reverse] b / Esc [/reverse] Volver a selección de servidor\n"
                "  [reverse] r [/reverse] Refrescar lista\n"
                "  [reverse] p [/reverse] Pausar / Reanudar logs\n"
                "  [reverse] e / x [/reverse] Exportar logs\n"
                "  [reverse] a [/reverse] Iniciar contenedor\n"
                "  [reverse] t [/reverse] Detener contenedor\n"
                "  [reverse] R [/reverse] Reiniciar contenedor\n"
                "  [reverse] Del [/reverse] Eliminar contenedor\n"
                "  [reverse] q [/reverse] Salir\n\n"
                "[dim]Presiona Enter, q, ? o Esc para cerrar.[/]",
                id="remove-warning",
            ),
            Button("Cerrar", id="cancel-remove"),
            id="remove-modal",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def action_dismiss_help(self) -> None:
        self.dismiss()
