from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


CONFIG_DIR_NAME = "termainer"
CONFIG_FILE_NAME = "config.yaml"


@dataclass
class ServerConfig:
    label: str
    provider: str
    host: Optional[str] = None
    user: str = "root"
    key_path: Optional[str] = None
    password: Optional[str] = None
    port: int = 22


@dataclass
class AppConfig:
    lang: str = "en"
    servers: List[ServerConfig] = field(default_factory=list)


def _get_config_paths() -> List[Path]:
    paths = []
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        paths.append(Path(xdg) / CONFIG_DIR_NAME / CONFIG_FILE_NAME)
    paths.append(Path.home() / ".config" / CONFIG_DIR_NAME / CONFIG_FILE_NAME)
    paths.append(Path.cwd() / CONFIG_FILE_NAME)
    return paths


def load_config() -> AppConfig:
    config_paths = _get_config_paths()
    for path in config_paths:
        if path.exists():
            return _parse_yaml(path)
    return AppConfig()


def _parse_yaml(path: Path) -> AppConfig:
    try:
        import yaml
    except ImportError:
        raise RuntimeError(
            "PyYAML is required to load config.yaml. "
            "Install it with: pip install pyyaml"
        )

    with open(path) as f:
        data: Dict[str, Any] = yaml.safe_load(f) or {}

    lang = data.get("lang", "en")
    servers_raw: List[Dict[str, Any]] = data.get("servers", [])
    servers = []
    for s in servers_raw:
        servers.append(
            ServerConfig(
                label=s["label"],
                provider=s["provider"],
                host=s.get("host"),
                user=s.get("user", "root"),
                key_path=s.get("key") or s.get("key_path"),
                password=s.get("password"),
                port=s.get("port", 22),
            )
        )
    return AppConfig(lang=lang, servers=servers)
