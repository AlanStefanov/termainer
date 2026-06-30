from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Static

from ..locale import _
from ..server_manager import ServerManager
from ..version import VERSION_DISPLAY


# ── ASCII art ─────────────────────────────────────────────────────────────────

LOGO_BLOCK = """\
[bold #66FF33] _______ ______ _____  __  __          _____ _   _ ______ _____  [/]
[bold #66FF33]|__   __|  ____|  __ \\|  \\/  |   /\\   |_   _| \\ | |  ____|  __ \\ [/]
[bold #66FF33]   | |  | |__  | |__) | \\  / |  /  \\    | | |  \\| | |__  | |__) |[/]
[bold #66FF33]   | |  |  __| |  _  /| |\\/| | / /\\ \\   | | | . ` |  __| |  _  / [/]
[bold #66FF33]   | |  | |____| | \\ \\| |  | |/ ____ \\ _| |_| |\\  | |____| | \\ \\ [/]
[bold #66FF33]   |_|  |______|_|  \\_\\_|  |_/_/    \\_\\_____|_| \\_|______|_|  \\_\\ [/]"""

LOGO_COMPACT = "[bold #66FF33][ >_ ]  TERMAINER[/]"


# ── Widgets ───────────────────────────────────────────────────────────────────

class HeaderWidget(Horizontal):
    """Fixed header: brand (left) · welcome (center) · live status (right)."""

    _pulse: reactive[bool] = reactive(True)

    def __init__(self, server_manager: ServerManager) -> None:
        super().__init__(id="home-header")
        self._server_manager = server_manager

    def compose(self) -> ComposeResult:
        yield Static(
            f"[bold #66FF33][ >_ ][/]  [bold #66FF33]TERMAINER[/] [dim #66FF33]v{VERSION_DISPLAY}[/]",
            id="home-logo",
        )
        yield Static(f"─── {_('home.welcome')} ───", id="home-welcome")
        yield Static("", id="home-status")

    def on_mount(self) -> None:
        self._render_status()
        self.set_interval(0.9, self._toggle_pulse)

    def _toggle_pulse(self) -> None:
        self._pulse = not self._pulse

    def watch__pulse(self, _: bool) -> None:
        self._render_status()

    def _render_status(self) -> None:
        count = self._server_manager.server_count
        dot = "[bold #66FF33]●[/]" if self._pulse else "[dim #2a2a2a]●[/]"
        try:
            self.query_one("#home-status", Static).update(
                f"{dot} {_('home.header.status', connected=count, total=count)}"
            )
        except Exception:
            pass


class HeroWidget(Vertical):
    """Full-width hero section: big logo + tagline."""

    def compose(self) -> ComposeResult:
        yield Static(LOGO_BLOCK, id="hero-logo")
        yield Static(
            f"[bold #00E5FF]{_('home.hero.tagline')}[/]",
            id="hero-tagline",
        )

    def set_compact(self, compact: bool) -> None:
        try:
            self.query_one("#hero-logo", Static).update(
                LOGO_COMPACT if compact else LOGO_BLOCK
            )
        except Exception:
            pass


class PlatformsStripWidget(Horizontal):
    """Horizontal strip of 6 platform icons — no boxes, icon + name only."""

    _PLATFORMS = [
        ("🐳", "#3399FF", "home.platform.docker"),
        ("⎈",  "#3399FF", "home.platform.k8s"),
        ("⬡",  "#FFD400", "home.platform.swarm"),
        ("◇",  "#B366FF", "home.platform.podman"),
        ("◈",  "#FF3B30", "home.platform.openshift"),
        ("▸_", "#66FF33", "home.platform.ssh"),
    ]

    def compose(self) -> ComposeResult:
        for icon, color, key in self._PLATFORMS:
            yield Static(
                f"[bold {color}]{icon}[/]  [{color}]{_(key)}[/]",
                classes="platform-item",
            )


class AboutWidget(Vertical):
    """Compact description of what Termainer is."""

    def compose(self) -> ComposeResult:
        yield Static(f"[bold #00E5FF]{_('home.about.title')}[/]", classes="section-label")
        yield Static(
            _("home.about.description"),
            id="about-description",
        )


class FeaturesWidget(Horizontal):
    """Five-column feature breakdown with icons, titles and item lists."""

    _COLS = [
        ("#66FF33", "▥", "home.features.obs.title", "home.features.obs.items"),
        ("#00E5FF", "⌕", "home.features.inspection.title", "home.features.inspection.items"),
        ("#3399FF", "⚙", "home.features.ops.title", "home.features.ops.items"),
        ("#B366FF", "⬡", "home.features.export.title", "home.features.export.items"),
        ("#FFD400", "⇶", "home.features.unified.title", "home.features.unified.items"),
    ]

    def compose(self) -> ComposeResult:
        for color, icon, title_key, items_key in self._COLS:
            yield Vertical(
                Static(f"[bold {color}]{icon}  {_(title_key)}[/]", classes="feat-title"),
                Static(f"[dim]{_(items_key)}[/]", classes="feat-body"),
                classes="feat-col",
            )


class SupportedPlatformsWidget(Horizontal):
    """Six platform cards, each with its brand-color border."""

    _CARDS = [
        ("🐳", "#3399FF", "home.platform.docker",  "plat-docker"),
        ("⎈",  "#3399FF", "home.platform.k8s",          "plat-k8s"),
        ("⬡",  "#FFD400", "home.platform.swarm",        "plat-swarm"),
        ("◇",  "#B366FF", "home.platform.podman",       "plat-podman"),
        ("◈",  "#FF3B30", "home.platform.openshift",    "plat-openshift"),
        ("▸_", "#66FF33", "home.platform.ssh",          "plat-ssh"),
    ]

    def compose(self) -> ComposeResult:
        for icon, color, key, css_class in self._CARDS:
            name = _(key)
            parts = name.split(" ", 1)
            display = f"{parts[0]}\n{parts[1]}" if len(parts) > 1 else name
            yield Vertical(
                Static(f"[bold {color}]{icon}[/]", classes="plat-icon"),
                Static(display,                        classes="plat-name"),
                Static(f"[bold #4ade80]{_('home.platforms.supported')}[/]", classes="plat-status"),
                classes=f"plat-card {css_class}",
            )


class FooterWidget(Vertical):
    """Centered footer: Enter hint + credits."""

    def compose(self) -> ComposeResult:
        hint = _("home.footer.enter_hint")
        styled = hint.replace("ENTER", "[bold #66FF33]ENTER[/]")
        yield Static(styled, id="footer-enter")
        yield Static(
            _("home.footer.credits"),
            id="footer-credits",
        )


# ── Screen ────────────────────────────────────────────────────────────────────

class HomeScreen(Screen):
    """
    Widget-based home/welcome screen.

    Hierarchy:
        HomeScreen
        ├── HeaderWidget              brand · welcome · live pulsing status
        ├── HeroWidget                big logo + tagline
        ├── PlatformsStripWidget      6 platform icons, no boxes
        ├── AboutWidget               description + ASCII connection diagram
        ├── FeaturesWidget            5-column feature breakdown
        ├── SupportedPlatformsWidget  6 colored-border platform cards
        └── FooterWidget              Enter hint + credits (no shortcuts)
    """

    BINDINGS = [
        ("enter",  "continue_to_env", _("home.bind.continue")),
        ("escape", "continue_to_env", _("home.bind.continue")),
        ("q",      "show_quit_confirm", _("home.bind.quit")),
    ]

    def __init__(self, server_manager: ServerManager) -> None:
        super().__init__()
        self._server_manager = server_manager
        self._dismissed = False
        self._hero: HeroWidget | None = None

    def compose(self) -> ComposeResult:
        hero = HeroWidget(id="home-hero")
        self._hero = hero
        yield Vertical(
            HeaderWidget(self._server_manager),
            hero,
            PlatformsStripWidget(id="home-platforms"),
            AboutWidget(id="home-about"),
            FeaturesWidget(id="home-features"),
            Static(
                f"[bold #00E5FF]{_('home.platforms.title')}[/]",
                id="home-supported-label",
            ),
            SupportedPlatformsWidget(id="home-supported"),
            id="home-root",
        )
        yield FooterWidget(id="home-footer")

    def on_mount(self) -> None:
        self._apply_responsive(self.size.width, self.size.height)

    def on_resize(self, event: Resize) -> None:
        self._apply_responsive(event.size.width, event.size.height)

    def _apply_responsive(self, width: int, height: int) -> None:
        compact = width < 100 or height < 34
        try:
            root = self.query_one("#home-root", Vertical)
        except Exception:
            return
        if compact:
            root.add_class("compact")
            if self._hero:
                self._hero.set_compact(True)
        else:
            root.remove_class("compact")
            if self._hero:
                self._hero.set_compact(False)

    def on_key(self, event) -> None:
        if event.key in ("enter", "escape"):
            event.stop()
            self._dismiss()

    def on_click(self) -> None:
        self._dismiss()

    def action_continue_to_env(self) -> None:
        self._dismiss()

    def action_show_quit_confirm(self) -> None:
        from .environment import ConfirmQuitModal
        self.app.push_screen(ConfirmQuitModal(), self._on_quit_result)

    def _on_quit_result(self, confirmed: bool) -> None:
        if confirmed:
            self.app.exit()

    def _dismiss(self) -> None:
        if self._dismissed:
            return
        self._dismissed = True
        from .environment import EnvironmentScreen
        self.app.switch_screen(EnvironmentScreen(self._server_manager))
