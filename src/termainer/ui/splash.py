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
[bold green] _______ ______ _____  __  __          _____ _   _ ______ _____  [/]
[bold green]|__   __|  ____|  __ \\|  \\/  |   /\\   |_   _| \\ | |  ____|  __ \\ [/]
[bold green]   | |  | |__  | |__) | \\  / |  /  \\    | | |  \\| | |__  | |__) |[/]
[bold green]   | |  |  __| |  _  /| |\\/| | / /\\ \\   | | | . ` |  __| |  _  / [/]
[bold green]   | |  | |____| | \\ \\| |  | |/ ____ \\ _| |_| |\\  | |____| | \\ \\ [/]
[bold green]   |_|  |______|_|  \\_\\_|  |_/_/    \\_\\_____|_| \\_|______|_|  \\_\\ [/]"""

LOGO_COMPACT = "[bold green]TERMAINER[/]"

CONTAINER_ICON = """\
[bold cyan]            ┌─────────────────┐[/]
[bold cyan]         ┌──┘                 └──┐[/]
[bold cyan]         │    │ │ │ │ │ │ │      │[/]
[bold cyan]         │    │ │ │ │ │ │ │      │[/]
[bold cyan]         └──┐                 ┌──┘[/]
[bold cyan]            └─────────────────┘[/]
[dim cyan]             observability core[/]"""


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
                    Static(f"[bold cyan]v{VERSION}[/]", classes="splash-version"),
                    id="splash-logo-block",
                )
            ),
            Static(
                "[cyan]▣[/] Todo lo que necesitas saber de [bold green]TODOS[/] tus contenedores en una sola terminal",
                classes="splash-tagline",
            ),
            Vertical(
                Horizontal(
                    Vertical(
                        Static("[bold cyan]¿QUÉ ES TERMAINER?[/]", classes="section-title"),
                        Static(
                            "[bold green]Termainer[/] es una TUI multiplataforma para inspección, monitoreo y depuración de\n"
                            "contenedores [bold yellow]Docker[/], [bold cyan]Podman[/], [bold magenta]Kubernetes[/], [bold red]OpenShift[/] y [bold white]Swarm[/].\n\n"
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
                Static("[bold magenta]CARACTERÍSTICAS PRINCIPALES[/]", classes="section-title-center"),
                Horizontal(
                    Vertical(
                        Static("[bold green]▥ Stats en Tiempo Real[/]", classes="feat-title"),
                        Static("[dim]Monitorea CPU, memoria\ny red al instante.[/]", classes="feat-desc"),
                        classes="feat-card",
                    ),
                    Vertical(
                        Static("[bold yellow]▤ Logs en Vivo[/]", classes="feat-title"),
                        Static("[dim]Visualiza y navega logs\ncon scroll suave.[/]", classes="feat-desc"),
                        classes="feat-card",
                    ),
                    Vertical(
                        Static("[bold cyan]⌕ Inspección Detallada[/]", classes="feat-title"),
                        Static("[dim]Variables, redes,\nvolúmenes y más.[/]", classes="feat-desc"),
                        classes="feat-card",
                    ),
                    Vertical(
                        Static("[bold magenta]⇶ Multi-Tech + SSH[/]", classes="feat-title"),
                        Static("[dim]Docker, Podman, K8s,\nOpenShift, Swarm y multi-servidor.[/]", classes="feat-desc"),
                        classes="feat-card",
                    ),
                    id="splash-features",
                ),
                id="splash-main-card",
            ),
            Horizontal(
                Vertical(
                    Static("[bold cyan]INICIO RÁPIDO[/]", classes="section-title"),
                    Static(
                        "[cyan]0.[/] Elige tu tecnología\n"
                        "   [dim]Docker, Kubernetes, Podman, OpenShift o Swarm; luego filtra por servidor.[/]\n\n"
                        "[cyan]1.[/] Selecciona un contenedor\n"
                        "   [dim]Usa ↑/↓ para navegar y Enter para seleccionar.[/]\n\n"
                        "[cyan]2.[/] Explora la información\n"
                        "   [dim]Detalles, stats y logs se cargan automáticamente.[/]\n\n"
                        "[cyan]3.[/] Depura y exporta\n"
                        "   [dim]Revisa logs en vivo y expórtalos cuando lo necesites.[/]",
                        classes="splash-quickstart",
                    ),
                    Static(
                        "[dim cyan]      ┌─────────┐      ┌────────────┐      ┌────────────┐[/]\n"
                        "[dim cyan]      │  STATS  │  ->  │  DETALLES  │  ->  │    LOGS    │[/]\n"
                        "[dim cyan]      └─────────┘      └────────────┘      └────────────┘[/]",
                        id="splash-flow-diagram",
                    ),
                    id="splash-quickstart-section",
                ),
                Vertical(
                    Static("[bold yellow]ATAJOS DE TECLADO[/]", classes="section-title"),
                    Static(
                        "[bold yellow]↑ / ↓[/]   Navegar contenedores\n"
                        "[bold yellow]Enter[/]   Seleccionar contenedor\n"
                        "[bold yellow]r[/]       Refrescar información\n"
                        "[bold yellow]e[/]       Exportar logs\n"
                        "[bold yellow]p[/]       Pausar / Reanudar logs\n"
                        "[bold yellow]n[/]       Siguiente panel\n"
                        "[bold yellow]← / →[/]   Cambiar panel\n"
                        "[bold yellow]b[/]       Volver a tecnologías\n"
                        "[bold yellow]a/t/R[/]   Start / Stop / Restart\n"
                        "[bold yellow]Del[/]     Eliminar contenedor\n"
                        "[bold yellow]q[/]       Salir de Termainer\n"
                        "[bold yellow]?[/]       Mostrar ayuda",
                        classes="splash-shortcuts",
                    ),
                    id="splash-shortcuts-section",
                ),
                id="splash-bottom-row",
            ),
            Static("[bold cyan]Presiona [white]Enter[/] para continuar[/]", id="splash-enter-hint"),
            Center(
                Static(
                    f"[green]▻[/] [bold green]TERMAINER[/] [cyan]v{VERSION}[/]    [dim]|[/]    [dim]Desarrollado con[/] [red]♥[/] [dim]usando Python, Textual y Rich[/]    [dim]|[/]    [dim]Hecho por[/] [green]Alan Stefanov[/]",
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
