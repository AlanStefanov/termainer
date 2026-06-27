from __future__ import annotations

import re
from collections import deque
from typing import Dict, List

from rich.markup import escape
from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Label, ListItem, Static
from textual.widgets._rich_log import RichLog

from ..locale import _
from ..providers.base import ContainerSummary


DEFAULT_CHART_WIDTH = 62


def _status_color(status: str) -> str:
    normalized = status.lower()
    if "restart" in normalized:
        return "#fbbf24"
    if "exited" in normalized or "dead" in normalized or "error" in normalized:
        return "#f87171"
    if "created" in normalized or "stopped" in normalized or "paused" in normalized:
        return "#6b5b8a"
    if "up" in normalized or "running" in normalized:
        return "#4ade80"
    return "#6b5b8a"


class ContainerItem(ListItem):
    def __init__(self, container: ContainerSummary) -> None:
        self.container = container
        self.server_label: str = container.get("_server", "")
        super().__init__()

    def compose(self) -> ComposeResult:
        name = (
            self.container.get("names")
            or self.container.get("name")
            or self.container.get("id", "unknown")
        )
        if isinstance(name, list):
            name = name[0]
        status = self.container.get("status", "")
        namespace = self.container.get("namespace", "")
        ready = self.container.get("ready", "")
        status_text = str(status)
        status_color = _status_color(status_text)

        dot = f"[{status_color}]●[/]"
        meta = f"{namespace} · {ready}" if namespace else ""
        yield Label(f"{dot}  [bold white]{escape(str(name))}[/]")
        if meta:
            yield Label(f"    [dim]{escape(meta)}[/]")
        else:
            yield Label("")


class DetailsWidget(Static):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.can_focus = True
        self.can_focus_children = False

    def show_details(self, container: ContainerSummary, env: Dict[str, str]) -> None:
        name = (
            container.get("names")
            or container.get("name")
            or container.get("id", "unknown")
        )
        if isinstance(name, list):
            name = name[0]
        cid = container.get("id", "")
        image = container.get("image", "")
        status = container.get("status", "")
        created = container.get("createdat", container.get("created", ""))
        ports = container.get("ports", "")
        networks = container.get("networks", "")
        restart = container.get("restartpolicy", container.get("restart", ""))
        namespace = container.get("namespace", "")
        ready = container.get("ready", "")
        node = container.get("node", "")

        status_color = _status_color(str(status))

        lines = [
            f"[dim]◉[/]  [bold #4ade80]{escape(str(name))}[/]  [dim]{escape(str(cid)[:12])}[/]",
            f"  [bold white]{_('widgets.details.image')}[/]     [white]{escape(str(image))}[/]",
            f"  [bold white]{_('widgets.details.status')}[/]     [{status_color}]{escape(str(status))}[/]",
            f"  [bold white]{_('widgets.details.id')}[/]         [white]{escape(str(cid))}[/]",
            f"  [bold white]{_('widgets.details.created')}[/]     [white]{escape(str(created))}[/]",
            f"  [bold white]{_('widgets.details.ports')}[/]  [#22d3ee]{escape(str(ports))}[/]",
            f"  [bold white]{_('widgets.details.networks')}[/]    [#22d3ee]{escape(str(networks))}[/]",
            f"  [bold white]{_('widgets.details.restart')}[/]   [white]{escape(str(restart))}[/]",
            f"  [bold white]{_('widgets.details.namespace')}[/]    [#22d3ee]{escape(str(namespace))}[/]" if namespace else "",
            f"  [bold white]{_('widgets.details.ready')}[/]      [white]{escape(str(ready))}[/]" if ready else "",
            f"  [bold white]{_('widgets.details.node')}[/]       [white]{escape(str(node))}[/]" if node else "",
            "",
        ]

        env_count = len(env)
        lines.append(f"  [bold #22d3ee]{_('widgets.details.env_title', count=str(env_count))}[/]")
        if env:
            for k, v in env.items():
                display_val = "********" if "SECRET" in k.upper() or "PASSWORD" in k.upper() else v
                lines.append(f"  [#4ade80]{escape(str(k))}[/]=[white]{escape(str(display_val))}[/]")
        else:
            lines.append(_("widgets.details.env_empty"))

        self.update("\n".join(lines))


class StatsWidget(Static):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._cpu_history: deque[float] = deque(maxlen=60)
        self._mem_history: deque[float] = deque(maxlen=60)
        self._net_history: deque[float] = deque(maxlen=60)
        self._history_seeded = False

    def update_stats(self, stats: dict) -> None:
        cpu_raw = stats.get("cpu", stats.get("CPUPerc", "0%"))
        mem_raw = stats.get("memory", stats.get("MemUsage", "0MiB / 0MiB"))
        net_raw = stats.get("net_io", stats.get("NetIO", "0MB / 0MB"))
        pids = stats.get("pids", stats.get("PIDs", "0"))

        cpu_val = self._parse_percent(str(cpu_raw))
        mem_val = self._parse_mem_pct(str(mem_raw))
        net_val = self._parse_net(str(net_raw))

        if not self._history_seeded:
            self._seed_history(cpu_val, mem_val, net_val)
        else:
            self._cpu_history.append(cpu_val)
            self._mem_history.append(mem_val)
            self._net_history.append(net_val)

        widget_width = max(50, int(getattr(self.size, "width", DEFAULT_CHART_WIDTH + 12) or (DEFAULT_CHART_WIDTH + 12)))
        chart_width = max(34, min(DEFAULT_CHART_WIDTH, widget_width - 10))

        cpu_chart = self._chart(self._cpu_history, 100, "100%", " 50%", "  0%", "green", chart_width)
        mem_chart = self._chart(self._mem_history, 100, "100%", " 50%", "  0%", "cyan", chart_width)
        net_max = max(max(self._net_history, default=0), 1)
        net_chart = self._chart(self._net_history, net_max, self._format_bytes(net_max), self._format_bytes(net_max / 2), "0B", "magenta", chart_width)

        cpu_card_w = 12 if widget_width >= 70 else 10
        pids_card_w = 12 if widget_width >= 70 else 10
        wide_card_w = 22 if widget_width >= 90 else 18

        cpu_card = self._kpi_card(_("widgets.stats.cpu"), str(cpu_raw), "green", cpu_card_w)
        mem_card = self._kpi_card(_("widgets.stats.memory"), str(mem_raw), "cyan", wide_card_w)
        net_card = self._kpi_card(_("widgets.stats.net"), str(net_raw), "magenta", wide_card_w)
        pids_card = self._kpi_card(_("widgets.stats.pids"), str(pids), "yellow", pids_card_w)

        lines = [
            *self._join_cards([cpu_card, mem_card, net_card, pids_card]),
            "",
            f"[bold white]{_('widgets.stats.cpu_chart')}[/]",
            *cpu_chart,
            "",
            f"[bold white]{_('widgets.stats.mem_chart')}[/]",
            *mem_chart,
            "",
            f"[bold white]{_('widgets.stats.net_chart')}[/]",
            *net_chart,
        ]
        self.update("\n".join(lines))

    def reset_history(self) -> None:
        self._cpu_history.clear()
        self._mem_history.clear()
        self._net_history.clear()
        self._history_seeded = False

    def _seed_history(self, cpu: float, memory: float, network: float) -> None:
        self._cpu_history.append(cpu)
        self._mem_history.append(memory)
        self._net_history.append(network)
        self._history_seeded = True

    @staticmethod
    def _kpi_card(title: str, value: str, color: str, width: int) -> List[str]:
        inner_width = width - 2
        safe_title = escape(title[:inner_width]).center(inner_width)
        safe_value = escape(value[:inner_width]).center(inner_width)
        return [
            f"[dim]╭{'─' * inner_width}╮[/]",
            f"[dim]│[/][bold white]{safe_title}[/][dim]│[/]",
            f"[dim]│[/][bold {color}]{safe_value}[/][dim]│[/]",
            f"[dim]╰{'─' * inner_width}╯[/]",
        ]

    @staticmethod
    def _join_cards(cards: List[List[str]]) -> List[str]:
        return ["  ".join(card[row] for card in cards) for row in range(len(cards[0]))]

    @staticmethod
    def _chart(data: deque, max_val: float, top_label: str, mid_label: str, bottom_label: str, color: str, chart_width: int) -> List[str]:
        samples = list(data)[-chart_width:]
        sparkline = StatsWidget._sparkline(samples, max_val).rjust(chart_width)
        return [
            f"[dim]{top_label:>5} ┌{'─' * chart_width}┐[/]",
            f"[dim]{mid_label:>5} │[/][{color}]{sparkline}[/][dim]│[/]",
            f"[dim]{bottom_label:>5} └{'─' * chart_width}┘[/]",
        ]

    @staticmethod
    def _sparkline(samples: List[float], max_val: float) -> str:
        if not samples:
            return ""
        chars = "▁▂▃▄▅▆▇█"
        safe_max = max(max_val, max(samples), 1)
        result = []
        previous_index = 0
        for index, value in enumerate(samples):
            ratio = max(0.0, min(float(value) / safe_max, 1.0))
            char_index = int(round(ratio * (len(chars) - 1)))
            if value <= 0:
                char_index = 0
            if index and char_index == previous_index and value != samples[index - 1]:
                char_index = min(len(chars) - 1, max(0, char_index + (1 if value > samples[index - 1] else -1)))
            previous_index = char_index
            result.append(chars[char_index])
        return "".join(result)

    @staticmethod
    def _format_bytes(value: float) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        amount = float(value)
        unit_index = 0
        while amount >= 1000 and unit_index < len(units) - 1:
            amount /= 1000
            unit_index += 1
        if amount >= 10 or unit_index == 0:
            return f"{amount:.0f}{units[unit_index]}"
        return f"{amount:.1f}{units[unit_index]}"

    @staticmethod
    def _parse_percent(raw: str) -> float:
        try:
            return float(raw.strip().rstrip("%"))
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def _parse_mem_pct(raw: str) -> float:
        try:
            parts = raw.split("/")
            if len(parts) == 2:
                used = parts[0].strip()
                total = parts[1].strip()
                return (StatsWidget._mem_to_bytes(used) / StatsWidget._mem_to_bytes(total)) * 100
            return 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _mem_to_bytes(raw: str) -> float:
        raw = raw.strip()
        try:
            if "GiB" in raw:
                return float(raw.replace("GiB", "").strip()) * 1024 ** 3
            if "MiB" in raw:
                return float(raw.replace("MiB", "").strip()) * 1024 ** 2
            if "KiB" in raw:
                return float(raw.replace("KiB", "").strip()) * 1024
            if "GB" in raw:
                return float(raw.replace("GB", "").strip()) * 10 ** 9
            if "MB" in raw:
                return float(raw.replace("MB", "").strip()) * 10 ** 6
            if "KB" in raw:
                return float(raw.replace("KB", "").strip()) * 10 ** 3
            return float(raw)
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def _parse_net(raw: str) -> float:
        try:
            parts = raw.split("/")
            if len(parts) == 1:
                return StatsWidget._mem_to_bytes(parts[0])
            return StatsWidget._mem_to_bytes(parts[0])
        except Exception:
            return 0.0


class LogWidget(RichLog):
    def __init__(self, **kwargs) -> None:
        super().__init__(max_lines=500, highlight=True, wrap=True, **kwargs)
        self._buffer: List[str] = []
        self._paused = False

    @property
    def paused(self) -> bool:
        return self._paused

    def toggle_pause(self) -> None:
        self._paused = not self._paused

    def append_line(self, line: str) -> None:
        if not self._paused:
            self._buffer.append(line)
            self.write(Text.from_markup(self._format_line(line)))

    def get_content(self) -> str:
        return "\n".join(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()
        super().clear()

    @staticmethod
    def _format_line(line: str) -> str:
        text = escape(line.rstrip())
        text = re.sub(
            r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:?\d{2})?)",
            r"[dim]\1[/]",
            text,
        )
        replacements = {
            "ERROR": "red",
            "WARN": "yellow",
            "WARNING": "yellow",
            "INFO": "green",
            "DEBUG": "cyan",
            "HTTP": "blue",
        }
        for word, color in replacements.items():
            text = re.sub(rf"\b{word}\b", rf"[{color}]{word}[/]", text)
        text = re.sub(r"\[(API|DB|Redis|HTTP|CRON)\]", r"[#22d3ee][\1][/]", text)
        return text
