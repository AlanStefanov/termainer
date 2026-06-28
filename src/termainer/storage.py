from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .ssh_config import SSHServer


def get_config_dir() -> Path:
    path = Path.home() / ".config" / "termainer"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_path() -> Path:
    return get_config_dir() / "provider_servers.json"


def _servers_path() -> Path:
    return get_config_dir() / "servers.json"


def load_provider_servers_cache() -> Dict[str, List[str]]:
    try:
        return json.loads(_cache_path().read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_provider_servers_cache(provider: str, aliases: List[str]) -> None:
    cache = load_provider_servers_cache()
    cache[provider] = aliases
    _cache_path().write_text(json.dumps(cache, indent=2))


def get_cached_aliases(provider: str) -> List[str]:
    return load_provider_servers_cache().get(provider, [])


def load_user_servers() -> Dict[str, SSHServer]:
    try:
        data = json.loads(_servers_path().read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    servers: Dict[str, SSHServer] = {}
    for entry in data.get("servers", []):
        alias = entry.get("alias", "")
        if alias:
            servers[alias] = SSHServer(
                host=alias,
                hostname=entry.get("hostname", alias),
                user=entry.get("user"),
                port=entry.get("port", 22),
                identity_file=entry.get("identity_file"),
                source="app_config",
            )
    return servers


def save_user_server(alias: str, hostname: str, user: Optional[str] = None,
                     port: int = 22, identity_file: Optional[str] = None) -> None:
    servers = load_user_servers()
    servers[alias] = SSHServer(
        host=alias,
        hostname=hostname,
        user=user,
        port=port,
        identity_file=identity_file,
        source="app_config",
    )
    _write_user_servers(servers)


def remove_user_server(alias: str) -> bool:
    servers = load_user_servers()
    if alias not in servers:
        return False
    del servers[alias]
    _write_user_servers(servers)
    return True


def _write_user_servers(servers: Dict[str, SSHServer]) -> None:
    entries = []
    for alias, srv in servers.items():
        entry: dict = {"alias": alias, "hostname": srv.hostname}
        if srv.user:
            entry["user"] = srv.user
        if srv.port != 22:
            entry["port"] = srv.port
        if srv.identity_file:
            entry["identity_file"] = srv.identity_file
        entries.append(entry)
    _servers_path().write_text(json.dumps({"servers": entries}, indent=2))


def get_all_ssh_servers() -> Dict[str, SSHServer]:
    from .ssh_config import get_ssh_servers, filter_ssh_servers_for_container_mgmt
    all_servers = get_ssh_servers()
    filtered = filter_ssh_servers_for_container_mgmt(all_servers)
    user_servers = load_user_servers()
    for alias, srv in user_servers.items():
        if alias not in filtered:
            filtered[alias] = srv
    return filtered


def has_any_ssh_servers() -> bool:
    return bool(get_all_ssh_servers())
