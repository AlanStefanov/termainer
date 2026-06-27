from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical
from textual.events import Click, Resize
from textual.screen import Screen
from textual.widgets import Static

from ..server_manager import ServerManager
from ..version import VERSION


LOGO = """\
[bold #22d3ee] _______ ______ _____  __  __          _____ _   _ ______ _____  [/]
[bold #22d3ee]|__   __|  ____|  __ \\|  \\/  |   /\\   |_   _| \\ | |  ____|  __ \\ [/]
[bold #22d3ee]   | |  | |__  | |__) | \\  / |  /  \\    | | |  \\| | |__  | |__) |[/]
[bold #22d3ee]   | |  |  __| |  _  /| |\\/| | / /\\ \\   | | | . ` |  __| |  _  / [/]
[bold #22d3ee]   | |  | |____| | \\ \\| |  | |/ ____ \\ _| |_| |\\  | |____| | \\ \\ [/]
[bold #22d3ee]   |_|  |______|_|  \\_\\_|  |_/_/    \\_\\_____|_| \\_|______|_|  \\_\\ [/]"""

LOGO_COMPACT = "[bold #22d3ee]TERMAINER[/]"

CONTAINER_ICON = """\
[bold #22d3ee]        .─────────────.        [/]
[bold #22d3ee]       /   ┌─┐ ┌─┐ ┌─┐ \\       [/]
[bold #22d3ee]      /    │ │ │ │ │ │  \\      [/]
[bold #22d3ee]     │     │ │ │ │ │ │   │     [/]
[bold #22d3ee]      \\    └─┘ └─┘ └─┘  /      [/]
[bold #22d3ee]       \\               /       [/]
[bold #22d3ee]        '─────────────'        [/]
[dim #22d3ee]        observability core[/]"""


class HomeScreen(Screen):
    BINDINGS = [
        Binding("enter", "continue", "Continue", priority=True),
        Binding("escape", "continue", "Continue", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    def __init__(self, server_manager: ServerManager) -> None:
        super().__init__()
        self._server_manager = server_manager
        self._dismissed = False

    def compose(self) -> ComposeResult:
        yield Vertical(
            self._header(),
            Center(
                Vertical(
                    Static(LOGO, classes="home-logo", id="home-logo-text"),
                    Static(f"[dim]v{VERSION}[/]", classes="home-version"),
                    id="home-logo-block",
                )
            ),
            Static(
                "Un [bold]unico[/] centro de operaciones para cualquier plataforma de contenedores, "
                "local o remota, sin abandonar la terminal.",
                classes="home-tagline",
            ),
            self._tech_icons_row(),
            Vertical(
                self._about_section(),
                self._features_section(),
                id="home-content",
            ),
            self._platforms_row(),
            Static(
                "[bold #22d3ee]Presiona Enter para continuar[/]",
                id="home-enter-hint",
            ),
            self._footer(),
            id="home-root",
        )

    def _header(self) -> Horizontal:
        return Horizontal(
            Static(f"[dim]>[/] [bold]TERMAINER[/] [dim]v{VERSION}[/]", id="home-header-left"),
            Static("B I E N V E N I D O  A", id="home-header-center"),
            Static("[bold #4ade80]●[/]", id="home-header-right"),
            id="home-header",
        )

    def _tech_icons_row(self) -> Horizontal:
        icons = [
            ("🐳", "#4ade80", "Docker"),
            ("⎈", "#22d3ee", "Kubernetes"),
            ("⬡", "#fbbf24", "Swarm"),
            ("◇", "#22d3ee", "Podman"),
            ("◈", "#f87171", "OpenShift"),
            ("▸_", "#808080", "Remote (SSH)"),
        ]
        children = []
        for emoji, color, label in icons:
            children.append(Static(f"[{color}]{emoji}[/] [{color}]{label}[/]", classes="home-tech-icon"))
        return Horizontal(*children, id="home-tech-icons")

    def _about_section(self) -> Vertical:
        return Vertical(
            Static("[bold]QUE ES TERMAINER?[/]", classes="home-section-title"),
            Horizontal(
                Vertical(
                    Static(
                        "[bold #22d3ee]Termainer[/] es una plataforma de observabilidad y operaciones nativa "
                        "de terminal que proporciona una interfaz unificada para ecosistemas de contenedores modernos.\n\n"
                        "Conectate a entornos locales o remotos por SSH y gestiona [bold #4ade80]Docker[/], "
                        "[bold #22d3ee]Kubernetes[/], [bold #fbbf24]Swarm[/], [bold #22d3ee]Podman[/] y "
                        "[bold #f87171]OpenShift[/] desde un unico dashboard interactivo.",
                        classes="home-about-text",
                    ),
                ),
                Center(Static(CONTAINER_ICON, classes="home-icon"), id="home-icon-wrap"),
                id="home-about-row",
            ),
            id="home-about",
        )

    def _features_section(self) -> Vertical:
        return Vertical(
            Static("[bold]CARACTERISTICAS PRINCIPALES[/]", classes="home-section-title"),
            Horizontal(
                Vertical(
                    Static("[bold #4ade80]Observabilidad[/]", classes="home-feat-title"),
                    Static(
                        "  [dim]● Metricas en tiempo real[/]\n"
                        "  [dim]● Logs en vivo[/]\n"
                        "  [dim]● Estados de recursos[/]\n"
                        "  [dim]● Eventos y alertas[/]",
                        classes="home-feat-desc",
                    ),
                    classes="home-feat-card",
                ),
                Vertical(
                    Static("[bold #22d3ee]Inspeccion[/]", classes="home-feat-title"),
                    Static(
                        "  [dim]● Contenedores / Pods[/]\n"
                        "  [dim]● Imagenes[/]\n"
                        "  [dim]● Volúmenes[/]\n"
                        "  [dim]● Redes[/]\n"
                        "  [dim]● Variables de entorno[/]",
                        classes="home-feat-desc",
                    ),
                    classes="home-feat-card",
                ),
                Vertical(
                    Static("[bold #fbbf24]Operaciones[/]", classes="home-feat-title"),
                    Static(
                        "  [dim]● Iniciar / Detener[/]\n"
                        "  [dim]● Reiniciar[/]\n"
                        "  [dim]● Ejecutar comandos[/]\n"
                        "  [dim]● Acceso a shell[/]\n"
                        "  [dim]● Port forward[/]",
                        classes="home-feat-desc",
                    ),
                    classes="home-feat-card",
                ),
                Vertical(
                    Static("[bold #f87171]Exportacion[/]", classes="home-feat-title"),
                    Static(
                        "  [dim]● Exportar logs[/]\n"
                        "  [dim]● Reportes[/]\n"
                        "  [dim]● Debug bundles[/]\n"
                        "  [dim]● Estado del sistema[/]",
                        classes="home-feat-desc",
                    ),
                    classes="home-feat-card",
                ),
                id="home-features-row",
            ),
            id="home-features",
        )

    def _platforms_row(self) -> Horizontal:
        platforms = [
            ("🐳", "#4ade80", "Docker Standalone"),
            ("⬡", "#fbbf24", "Docker Swarm"),
            ("⎈", "#22d3ee", "Kubernetes"),
            ("◈", "#f87171", "OpenShift"),
            ("◇", "#22d3ee", "Podman"),
            ("▸_", "#808080", "Remote (SSH)"),
        ]
        cards = []
        for emoji, color, label in platforms:
            cards.append(
                Vertical(
                    Static(f"[{color}]{emoji}[/] [{color}]{label}[/]", classes="home-plat-icon"),
                    Static("[dim]Soportado[/]", classes="home-plat-status"),
                    classes="home-plat-card",
                )
            )
        return Horizontal(*cards, id="home-platforms")

    def _footer(self) -> Horizontal:
        return Horizontal(
            Static(
                "[dim]Enter[/] Continuar  [dim]q[/] Salir",
                id="home-footer-left",
            ),
            Static(
                "[dim]Enter[/] Continuar",
                id="home-footer-compact",
            ),
            Static(
                f"[dim]desarrollada por[/] [bold #4ade80]Alan Stefanov[/] [dim]|[/] [dim]v{VERSION}[/]",
                id="home-footer-right",
            ),
            id="home-footer",
        )

    # --- Lifecycle ---

    def on_mount(self) -> None:
        self._apply_responsive_mode(self.size.width, self.size.height)

    def on_resize(self, event: Resize) -> None:
        self._apply_responsive_mode(event.size.width, event.size.height)

    def _apply_responsive_mode(self, width: int, height: int) -> None:
        compact = width < 120 or height < 38
        ultra_compact = width < 95 or height < 28
        root = self.query_one("#home-root", Vertical)
        logo = self.query_one("#home-logo-text", Static)
        if compact:
            root.add_class("compact")
            logo.update(LOGO_COMPACT)
        else:
            root.remove_class("compact")
            logo.update(LOGO)
        if ultra_compact:
            root.add_class("ultra-compact")
        else:
            root.remove_class("ultra-compact")

    # --- Events ---

    def on_key(self, event) -> None:
        if event.key in ("enter", "escape"):
            event.stop()
            self._dismiss()

    def on_click(self, event: Click) -> None:
        event.stop()
        self._dismiss()

    def action_continue(self) -> None:
        self._dismiss()

    def action_quit(self) -> None:
        self.app.exit()

    def _dismiss(self) -> None:
        if self._dismissed:
            return
        self._dismissed = True
        from .environment import EnvironmentScreen
        self.app.switch_screen(EnvironmentScreen(self._server_manager))
