from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import Screen
from textual.widgets import Static

from ..locale import _
from ..server_manager import ServerManager
from ..version import VERSION


_BRAND = f"[bold #66FF33]  [ >_ ]  T · E · R · M · A · I · N · E · R   v{VERSION}  [/]"

_BOOT_STEP_KEYS: list[tuple[str, str]] = [
    ("splash.boot.init",     "#66FF33"),
    ("splash.boot.docker",   "#3399FF"),
    ("splash.boot.k8s",      "#3399FF"),
    ("splash.boot.openshift","#FF3B30"),
    ("splash.boot.discover", "#00E5FF"),
    ("splash.boot.sync",     "#66FF33"),
]


class BootScreen(Screen):
    """Animated boot sequence. Auto-transitions to HomeScreen when done."""

    BINDINGS = [
        ("enter", "skip", _("home.bind.continue")),
        ("space", "skip", _("home.bind.continue")),
    ]

    def __init__(self, server_manager: ServerManager) -> None:
        super().__init__()
        self._server_manager = server_manager
        self._done = False

    def compose(self) -> ComposeResult:
        yield Center(
            Vertical(
                Static(_BRAND, id="boot-brand"),
                Static(
                    "[dim]─────────────────────────────────────────────[/]",
                    id="boot-sep",
                ),
                Static("", id="boot-messages"),
                id="boot-panel",
            ),
            id="boot-root",
        )

    async def on_mount(self) -> None:
        asyncio.create_task(self._run_sequence())

    async def _run_sequence(self) -> None:
        widget = self.query_one("#boot-messages", Static)
        lines: list[str] = []
        for key, color in _BOOT_STEP_KEYS:
            if self._done:
                break
            text = _(key)
            lines.append(f"  [{color}]▶[/]  {text}[dim]...[/]")
            widget.update("\n".join(lines))
            await asyncio.sleep(0.11)
            lines[-1] = f"  [{color}]✓[/]  {text}"
            widget.update("\n".join(lines))
            await asyncio.sleep(0.07)
        if not self._done:
            await asyncio.sleep(0.25)
        self._go_home()

    def _go_home(self) -> None:
        if self._done:
            return
        self._done = True
        from .home import HomeScreen
        self.app.switch_screen(HomeScreen(self._server_manager))

    def action_skip(self) -> None:
        self._go_home()

    def on_click(self) -> None:
        self.action_skip()


# Backward-compat alias
SplashScreen = BootScreen
