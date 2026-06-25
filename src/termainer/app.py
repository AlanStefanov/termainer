from __future__ import annotations

import asyncio
import argparse
import os
from typing import List, Optional, Type

from textual.app import App

from .config import build_ssh_from_env, load_env_file, build_ssh_from_ssh_server, get_configured_ssh_servers
from .config_manager import ServerConfig, load_config
from .providers.base import Provider
from .providers.docker import DockerProvider
from .providers.kubernetes import KubernetesProvider
from .providers.openshift import OpenShiftProvider
from .providers.podman import PodmanProvider
from .providers.swarm import SwarmProvider
from .remote.ssh import SSHConnection
from .server_manager import ServerConnection, ServerManager, provider_class_for
from .ui.splash import SplashScreen
from .version import VERSION


class TermainerApp(App):
    TITLE = "Termainer"
    SUB_TITLE = "Container observability from your terminal"
    CSS_PATH = "ui/styles.tcss"

    def __init__(self, server_manager: ServerManager) -> None:
        super().__init__()
        self.server_manager = server_manager

    def on_mount(self) -> None:
        self.push_screen(SplashScreen(self.server_manager))


async def detect_provider(ssh: Optional[SSHConnection] = None) -> Provider:
    providers: List[Type] = [
        DockerProvider,
        SwarmProvider,
        KubernetesProvider,
        PodmanProvider,
        OpenShiftProvider,
    ]
    for cls in providers:
        instance = cls(ssh=ssh) if ssh else cls()
        if await instance.is_available():
            return instance
    raise RuntimeError(
        "No container runtime detected. "
        "Please ensure Docker, Swarm, Podman, or kubectl/oc is available and running."
    )


async def detect_available_providers(ssh: Optional[SSHConnection] = None) -> List[Provider]:
    providers: List[Type] = [
        DockerProvider,
        SwarmProvider,
        KubernetesProvider,
        PodmanProvider,
        OpenShiftProvider,
    ]
    available: List[Provider] = []
    for cls in providers:
        instance = cls(ssh=ssh) if ssh else cls()
        if await instance.is_available():
            available.append(instance)
    return available


async def create_provider(
    provider_name: str | None = None,
    ssh: Optional[SSHConnection] = None,
) -> Provider:
    providers: dict[str, Type] = {
        "docker": DockerProvider,
        "swarm": SwarmProvider,
        "podman": PodmanProvider,
        "kubernetes": KubernetesProvider,
        "k8s": KubernetesProvider,
        "openshift": OpenShiftProvider,
    }
    if not provider_name or provider_name == "auto":
        return await detect_provider(ssh)

    cls = providers.get(provider_name.lower())
    if cls is None:
        available = ", ".join(sorted(providers))
        raise RuntimeError(f"Unknown provider '{provider_name}'. Available providers: {available}")

    instance = cls(ssh=ssh) if ssh else cls()
    if not await instance.is_available():
        raise RuntimeError(f"Provider '{provider_name}' is not available")
    return instance


async def build_server_manager(
    config_servers: List[ServerConfig],
    ssh: Optional[SSHConnection],
    cli_provider: str,
) -> ServerManager:
    connections: List[ServerConnection] = []

    if config_servers:
        for sc in config_servers:
            ssh_conn: Optional[SSHConnection] = None
            if sc.host:
                ssh_conn = SSHConnection(
                    host=sc.host,
                    user=sc.user,
                    key_path=sc.key_path,
                    password=sc.password,
                    port=sc.port,
                )
            provider_cls = provider_class_for(sc.provider)
            provider = provider_cls(ssh=ssh_conn) if ssh_conn else provider_cls()
            connections.append(ServerConnection(label=sc.label, provider=provider, ssh=ssh_conn))
        return ServerManager(connections)

    provider_name = cli_provider
    if provider_name == "auto" and ssh:
        from .config import get_provider_from_env

        env = load_env_file(".env")
        provider_name = get_provider_from_env(env) or "auto"

    if provider_name == "auto" and ssh is None:
        # Local auto-detect mode: get local providers + SSH servers from ~/.ssh/config
        available = await detect_available_providers(ssh=None)
        if not available:
            raise RuntimeError(
                "No container runtime detected. "
                "Please ensure Docker, Swarm, Podman, or kubectl/oc is available and running."
            )
        for provider in available:
            label = f"Local {provider.name.capitalize()}"
            connections.append(ServerConnection(label=label, provider=provider, ssh=None))

        # Add SSH-configured servers
        ssh_servers = get_configured_ssh_servers()
        for ssh_alias, ssh_server in ssh_servers.items():
            try:
                ssh_conn = build_ssh_from_ssh_server(ssh_server)
                ssh_provider = await detect_provider(ssh=ssh_conn)
                connections.append(
                    ServerConnection(label=ssh_alias, provider=ssh_provider, ssh=ssh_conn)
                )
            except Exception:
                # Skip servers where provider can't be detected
                pass

        return ServerManager(connections)

    provider = await create_provider(provider_name, ssh)
    label = f"{provider.name.capitalize()} ({ssh.host})" if ssh else f"Local {provider.name.capitalize()}"
    connections.append(ServerConnection(label=label, provider=provider, ssh=ssh))
    return ServerManager(connections)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Termainer — Container observability and operations from your terminal"
    )
    parser.add_argument(
        "--provider",
        choices=("auto", "docker", "swarm", "podman", "kubernetes", "k8s", "openshift"),
        default="auto",
        help="Container runtime provider to use",
    )
    parser.add_argument(
        "--host",
        help="Remote SSH host (IP or hostname). Overrides TERMAINER_REMOTE_HOST in .env",
    )
    parser.add_argument(
        "--ssh-user",
        default=None,
        help="SSH user (default: root, or TERMAINER_REMOTE_USER from .env)",
    )
    parser.add_argument(
        "--ssh-key",
        default=None,
        help="SSH private key path (.pem). Overrides TERMAINER_REMOTE_KEY_PATH in .env",
    )
    parser.add_argument(
        "--ssh-password",
        default=None,
        help="SSH password. Overrides TERMAINER_REMOTE_PASSWORD in .env",
    )
    parser.add_argument(
        "--ssh-port",
        type=int,
        default=None,
        help="SSH port (default: 22, or TERMAINER_REMOTE_PORT from .env)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
        help="Show version and exit",
    )
    parser.add_argument(
        "--env",
        default=".env",
        dest="env_file",
        help="Path to .env file for remote configuration (default: .env)",
    )
    parser.add_argument(
        "--config",
        default=None,
        dest="config_file",
        help="Path to config.yaml for multi-server setup (default: auto-detect XDG path)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    server_manager: Optional[ServerManager] = None

    if args.config_file:
        from .config_manager import _parse_yaml

        path = os.path.expanduser(args.config_file)
        app_cfg = _parse_yaml(path) if os.path.isfile(path) else load_config()
    else:
        app_cfg = load_config()

    if app_cfg.servers:
        server_manager = asyncio.run(
            build_server_manager(app_cfg.servers, ssh=None, cli_provider="auto")
        )
    else:
        env = load_env_file(args.env_file) if os.path.isfile(args.env_file) else {}

        ssh = build_ssh_from_env(
            env,
            cli_host=args.host,
            cli_user=args.ssh_user,
            cli_key=args.ssh_key,
            cli_password=args.ssh_password,
            cli_port=args.ssh_port,
        )

        server_manager = asyncio.run(
            build_server_manager([], ssh=ssh, cli_provider=args.provider)
        )

    app = TermainerApp(server_manager)
    app.run()


if __name__ == "__main__":
    main()
