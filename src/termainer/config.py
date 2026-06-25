from __future__ import annotations

from typing import Dict, Optional

from .remote.ssh import SSHConnection


def load_env_file(path: str = ".env") -> Dict[str, str]:
    env: Dict[str, str] = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip().strip("'\"")
    except FileNotFoundError:
        pass
    return env


def build_ssh_from_env(
    env: Dict[str, str],
    cli_host: Optional[str] = None,
    cli_user: Optional[str] = None,
    cli_key: Optional[str] = None,
    cli_password: Optional[str] = None,
    cli_port: Optional[int] = None,
) -> Optional[SSHConnection]:
    host = cli_host or env.get("TERMAINER_REMOTE_HOST")
    if not host:
        return None

    return SSHConnection(
        host=host,
        user=cli_user or env.get("TERMAINER_REMOTE_USER", "root"),
        key_path=cli_key or env.get("TERMAINER_REMOTE_KEY_PATH"),
        password=cli_password or env.get("TERMAINER_REMOTE_PASSWORD"),
        port=cli_port or int(env.get("TERMAINER_REMOTE_PORT", "22")),
    )


def get_provider_from_env(env: Dict[str, str]) -> Optional[str]:
    return env.get("TERMAINER_REMOTE_PROVIDER") or None
