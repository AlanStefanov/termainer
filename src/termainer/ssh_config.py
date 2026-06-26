"""Parser for ~/.ssh/config and SSH server discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional


class SSHServer:
    """Represents a server entry from ~/.ssh/config."""

    def __init__(
        self,
        host: str,
        hostname: Optional[str] = None,
        user: Optional[str] = None,
        port: int = 22,
        identity_file: Optional[str] = None,
    ) -> None:
        self.host = host  # The "Host" identifier (connection alias)
        self.hostname = hostname or host  # Actual hostname to connect to
        self.user = user  # None = let SSH use its default (local user)
        self.port = port
        self.identity_file = identity_file

    @property
    def display_name(self) -> str:
        """User-friendly display name."""
        if self.hostname != self.host:
            return f"{self.host} ({self.hostname})"
        return self.host

    def __repr__(self) -> str:
        return f"SSHServer(host={self.host}, hostname={self.hostname}, user={self.user}, port={self.port})"


def parse_ssh_config(config_path: Optional[str] = None) -> Dict[str, SSHServer]:
    """
    Parse ~/.ssh/config file and return a dict of SSHServer objects.

    Args:
        config_path: Optional path to SSH config file. Defaults to ~/.ssh/config

    Returns:
        Dict mapping connection aliases to SSHServer objects
    """
    if config_path is None:
        config_path = str(Path.home() / ".ssh" / "config")

    ssh_servers: Dict[str, SSHServer] = {}

    config_file = Path(config_path)
    if not config_file.exists():
        return ssh_servers

    current_host: Optional[str] = None
    current_config: Dict[str, str] = {}

    try:
        with open(config_file) as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Split key-value pairs (SSH config uses space-separated)
                parts = line.split(None, 1)
                if len(parts) != 2:
                    continue

                key, value = parts[0].lower(), parts[1].strip()

                # New host definition
                if key == "host":
                    # Save previous host if it exists
                    if current_host:
                        ssh_servers[current_host] = _build_ssh_server(current_host, current_config)
                    current_host = value
                    current_config = {}
                else:
                    # Collect config directives
                    if current_host:  # Only collect if we're in a Host block
                        current_config[key] = value

        # Don't forget the last host
        if current_host:
            ssh_servers[current_host] = _build_ssh_server(current_host, current_config)

    except (IOError, OSError):
        pass  # Return empty dict if file can't be read

    return ssh_servers


def _build_ssh_server(host: str, config: Dict[str, str]) -> SSHServer:
    """Build an SSHServer object from parsed config dict."""
    hostname = config.get("hostname", host)
    user = config.get("user")  # None if not specified → let SSH use local user
    port = int(config.get("port", "22"))
    identity_file = config.get("identityfile")

    return SSHServer(
        host=host,
        hostname=hostname,
        user=user,
        port=port,
        identity_file=identity_file,
    )


def get_ssh_servers() -> Dict[str, SSHServer]:
    """
    Convenience function to get all SSH servers from ~/.ssh/config.

    Returns:
        Dict mapping connection aliases to SSHServer objects
    """
    return parse_ssh_config()


def filter_ssh_servers_for_container_mgmt(servers: Dict[str, SSHServer]) -> Dict[str, SSHServer]:
    """
    Filter SSH servers that likely have container runtimes.
    Simple heuristic: exclude localhost and 127.0.0.1.

    Args:
        servers: Dict of SSHServer objects

    Returns:
        Filtered dict excluding local servers
    """
    return {
        alias: server
        for alias, server in servers.items()
        if server.hostname not in ("localhost", "127.0.0.1")
    }
