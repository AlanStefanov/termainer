from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional


def format_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def build_report_header(
    container_name: str,
    image: str,
    provider: str,
    extra: Optional[Dict[str, str]] = None,
) -> str:
    lines = [
        "=" * 60,
        " Termainer Bug Report",
        "=" * 60,
        f" Generated:  {format_timestamp()}",
        f" Provider:   {provider}",
        f" Container:  {container_name}",
        f" Image:      {image}",
        "-" * 60,
    ]
    if extra:
        for k, v in extra.items():
            lines.append(f" {k}: {v}")
        lines.append("-" * 60)
    return "\n".join(lines) + "\n"


def truncate_id(full_id: str, length: int = 12) -> str:
    return full_id[:length] if len(full_id) > length else full_id


def parse_cpu_percent(raw: str) -> float:
    try:
        return float(raw.strip().rstrip("%"))
    except (ValueError, AttributeError):
        return 0.0


def parse_memory_bytes(raw: str) -> float:
    raw = raw.strip()
    try:
        if raw.endswith("GiB"):
            return float(raw.replace("GiB", "").strip()) * 1024 ** 3
        if raw.endswith("MiB"):
            return float(raw.replace("MiB", "").strip()) * 1024 ** 2
        if raw.endswith("KiB"):
            return float(raw.replace("KiB", "").strip()) * 1024
        return float(raw)
    except (ValueError, AttributeError):
        return 0.0
