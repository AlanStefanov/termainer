from __future__ import annotations

import asyncio

from textual.app import ComposeResult
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
[bold #22d3ee]            ┌─────────────────┐[/]
[bold #22d3ee]         ┌──┘                 └──┐[/]
[bold #22d3ee]         │    │ │ │ │ │ │ │      │[/]
[bold #22d3ee]         │    │ │ │ │ │ │ │      │[/]
[bold #22d3ee]         └──┐                 ┌──┘[/]
[bold #22d3ee]            └─────────────────┘[/]
[dim #22d3ee]             observability core[/]"""


class SplashScreen(Screen):
    def __init__(self, server_manager: ServerManager, auto_dismiss: bool = True) -> None:
        super().__init__()
        self._server_manager = server_manager
        self._dismissed = False
        self._auto_dismiss_enabled = auto_dismiss

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("[dim]────────────────────────────────────────────[/]  B I E N V E N I D O  A", id="splash-top-line"),
            Center(
                Vertical(
                    Static(LOGO, classes="splash-logo", id="splash-logo-text"),
                    Static(f"[bold #22d3ee]v{VERSION}[/]", classes="splash-version"),
                    id="splash-logo-block",
                )
            ),
            Static(
                "[#22d3ee]▣[/] Todo lo que necesitas saber de [bold #4ade80]TODOS[/] tus contenedores en una sola terminal",
                classes="splash-tagline",
            ),
            Vertical(
                Horizontal(
                    Vertical(
                        Static("[bold #22d3ee]¿QUÉ ES TERMAINER?[/]", classes="section-title"),
                        Static(
                            "[bold #22d3ee]Termainer[/] es una TUI multiplataforma para inspección, monitoreo y depuración de\n"
                            "contenedores [bold #4ade80]Docker[/], [bold #22d3ee]Podman[/], [bold #22d3ee]Kubernetes[/], [bold #f87171]OpenShift[/] y [bold #fbbf24]Swarm[/].\n\n"
                            "Diseñada para desarrolladores y equipos DevOps que prefieren la velocidad y el control\n"
                            "de la terminal, Termainer centraliza la información clave de tus contenedores en una\n"
                            "interfaz interactiva, rápida y poderosa.",
                            classes="splash-desc",
                        ),
                        id="splash-about",
                    ),
                    Center(Static(CONTAINER_ICON, classes="splash-icon"), id="splash-icon-wrap"),
                    id="splash-about-row",
                ),
                Static("[bold #22d3ee]CARACTERÍSTICAS PRINCIPALES[/]", classes="section-title-center"),
                Horizontal(
                    Vertical(
                        Static("[bold #4ade80]▥ Stats en Tiempo Real[/]", classes="feat-title"),
                        Static("[dim]Monitorea CPU, memoria\ny red al instante.[/]", classes="feat-desc"),
                        classes="feat-card",
                    ),
                    Vertical(
                        Static("[bold #fbbf24]▤ Logs en Vivo[/]", classes="feat-title"),
                        Static("[dim]Visualiza y navega logs\ncon scroll suave.[/]", classes="feat-desc"),
                        classes="feat-card",
                    ),
                    Vertical(
                        Static("[bold #22d3ee]⌕ Inspección Detallada[/]", classes="feat-title"),
                        Static("[dim]Variables, redes,\nvolúmenes y más.[/]", classes="feat-desc"),
                        classes="feat-card",
                    ),
                    Vertical(
                        Static("[bold #22d3ee]⇶ Multi-Tech + SSH[/]", classes="feat-title"),
                        Static("[dim]Docker, Podman, K8s,\nOpenShift, Swarm y multi-servidor.[/]", classes="feat-desc"),
                        classes="feat-card",
                    ),
                    id="splash-features",
                ),
                id="splash-main-card",
            ),
            Horizontal(
                Vertical(
                    Static("[bold #22d3ee]INICIO RÁPIDO[/]", classes="section-title"),
                    Static(
                        "[#22d3ee]0.[/] Elige tu tecnología\n"
                        "   [dim]Docker, Kubernetes, Podman, OpenShift o Swarm; luego filtra por servidor.[/]\n\n"
                        "[#22d3ee]1.[/] Selecciona un contenedor\n"
                        "   [dim]Usa ↑/↓ para navegar y Enter para seleccionar.[/]\n\n"
                        "[#22d3ee]2.[/] Explora la información\n"
                        "   [dim]Detalles, stats y logs se cargan automáticamente.[/]\n\n"
                        "[#22d3ee]3.[/] Depura y exporta\n"
                        "   [dim]Revisa logs en vivo y expórtalos cuando lo necesites.[/]",
                        classes="splash-quickstart",
                    ),
                    Static(
                        "[dim #22d3ee]      ┌─────────┐      ┌────────────┐      ┌────────────┐[/]\n"
                        "[dim #22d3ee]      │  STATS  │  ->  │  DETALLES  │  ->  │    LOGS    │[/]\n"
                        "[dim #22d3ee]      └─────────┘      └────────────┘      └────────────┘[/]",
                        id="splash-flow-diagram",
                    ),
                    id="splash-quickstart-section",
                ),
                Vertical(
                    Static("[bold #fbbf24]ATAJOS DE TECLADO[/]", classes="section-title"),
                    Static(
                        "[bold #fbbf24]↑ / ↓[/]   Navegar contenedores\n"
                        "[bold #fbbf24]Enter[/]   Seleccionar contenedor\n"
                        "[bold #fbbf24]F5[/]      Refrescar información\n"
                        "[bold #fbbf24]e[/]       Exportar logs\n"
                        "[bold #fbbf24]p[/]       Pausar / Reanudar logs\n"
                        "[bold #fbbf24]n[/]       Siguiente panel\n"
                        "[bold #fbbf24]← / →[/]   Cambiar panel\n"
                        "[bold #fbbf24]b[/]       Volver a tecnologías\n"
                        "[bold #fbbf24]a/t/R[/]   Start / Stop / Restart\n"
                        "[bold #fbbf24]Del[/]     Eliminar contenedor\n"
                        "[bold #fbbf24]q[/]       Salir de Termainer\n"
                        "[bold #fbbf24]?[/]       Mostrar ayuda",
                        classes="splash-shortcuts",
                    ),
                    id="splash-shortcuts-section",
                ),
                id="splash-bottom-row",
            ),
            Static("[bold #22d3ee]Presiona [white]Enter[/] para continuar[/]", id="splash-enter-hint"),
            Center(
                Static(
                    f"[dim]desarrollada por[/] [bold #4ade80]Alan Stefanov[/] [dim]|[/] [#5c5c5c]v{VERSION}[/]",
                    classes="splash-footer",
                )
            ),
            id="splash-root",
        )

    async def on_mount(self) -> None:
        self._apply_responsive_mode(self.size.width, self.size.height)
        if self._auto_dismiss_enabled:
            asyncio.create_task(self._auto_dismiss())

    def on_resize(self, event: Resize) -> None:
        self._apply_responsive_mode(event.size.width, event.size.height)

    def _apply_responsive_mode(self, width: int, height: int) -> None:
        compact = width < 105 or height < 30
        ultra_compact = width < 85 or height < 24
        root = self.query_one("#splash-root", Vertical)
        logo = self.query_one("#splash-logo-text", Static)
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

    def on_key(self, event) -> None:
        if event.key == "enter":
            event.stop()
            self._dismiss()

    def on_click(self, event: Click) -> None:
        event.stop()
        self._dismiss()

    async def _auto_dismiss(self) -> None:
        await asyncio.sleep(10)
        self._dismiss()

    def _dismiss(self) -> None:
        if self._dismissed:
            return
        self._dismissed = True

        from .environment import EnvironmentScreen
        self.app.switch_screen(EnvironmentScreen(self._server_manager))
