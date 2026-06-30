from __future__ import annotations

import asyncio
import argparse
import os
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from typing import List, Optional, Type

from textual.app import App

from .config import build_ssh_from_env, load_env_file
from .config_manager import ServerConfig, load_config
from .locale import _
from .providers.base import Provider
from .providers.docker import DockerProvider
from .providers.kubernetes import KubernetesProvider
from .providers.openshift import OpenShiftProvider
from .providers.podman import PodmanProvider
from .providers.swarm import SwarmProvider
from .remote.ssh import SSHConnection
from .server_manager import ServerConnection, ServerManager, provider_class_for
from .ui.splash import BootScreen
from .version import VERSION_DISPLAY


def _check_command(command: list[str]) -> bool:
    try:
        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _print_doctor_line(ok: bool, label: str, detail: str = "") -> None:
    mark = "✓" if ok else "✗"
    suffix = f" {detail}" if detail else ""
    print(f"{mark} {label}{suffix}")


def run_doctor() -> int:
    print("Termainer Doctor")
    print("────────────────────────────────────")
    print()

    checks: list[bool] = []
    core_checks: list[bool] = []

    python_ok = sys.version_info >= (3, 10)
    checks.append(python_ok)
    core_checks.append(python_ok)
    _print_doctor_line(python_ok, f"Python {sys.version_info.major}.{sys.version_info.minor}")

    docker_cli = shutil.which("docker") is not None
    checks.append(docker_cli)
    _print_doctor_line(docker_cli, "Docker CLI detected")

    docker_api = docker_cli and _check_command(["docker", "info"])
    checks.append(docker_api)
    _print_doctor_line(docker_api, "Docker API available")

    ssh_ok = shutil.which("ssh") is not None
    checks.append(ssh_ok)
    _print_doctor_line(ssh_ok, "SSH support enabled")

    try:
        import textual  # noqa: F401

        textual_ok = True
    except ImportError:
        textual_ok = False
    checks.append(textual_ok)
    core_checks.append(textual_ok)
    _print_doctor_line(textual_ok, "Textual installed")

    try:
        import rich  # noqa: F401

        rich_ok = True
    except ImportError:
        rich_ok = False
    checks.append(rich_ok)
    core_checks.append(rich_ok)
    _print_doctor_line(rich_ok, "Rich installed")

    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "termainer"
    config_ok = config_dir.exists() or os.access(config_dir.parent, os.W_OK)
    checks.append(config_ok)
    core_checks.append(config_ok)
    _print_doctor_line(config_ok, "Configuration directory", str(config_dir))

    checks.append(True)
    core_checks.append(True)
    _print_doctor_line(True, "Version", VERSION_DISPLAY)

    print()
    if all(checks):
        print("Everything looks good.")
        return 0

    if all(core_checks):
        print("Core checks passed. Some optional runtime checks failed.")
        return 0

    print("Some checks failed.")
    return 1


class TermainerApp(App):
    TITLE = "Termainer"
    CSS_PATH = files("termainer.ui").joinpath("styles.tcss")

    def __init__(self, server_manager: ServerManager) -> None:
        super().__init__()
        self.server_manager = server_manager
        self.sub_title = _("app.subtitle")

    def on_mount(self) -> None:
        self.push_screen(BootScreen(self.server_manager))


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
    raise RuntimeError(_("app.error.no_runtime"))


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
        raise RuntimeError(_("app.error.unknown_provider", provider=provider_name, available=available))

    instance = cls(ssh=ssh) if ssh else cls()
    if not await instance.is_available():
        raise RuntimeError(_("app.error.provider_not_available", provider=provider_name))
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
        # Local auto-detect mode: solo proveedores locales, sin conexiones SSH al startup
        available = await detect_available_providers(ssh=None)
        if not available:
            return ServerManager([])
        for provider in available:
            label = _("app.server.local_label", provider=provider.name.capitalize())
            connections.append(ServerConnection(label=label, provider=provider, ssh=None))

        return ServerManager(connections)

    provider = await create_provider(provider_name, ssh)
    label = _("app.server.remote_label", provider=provider.name.capitalize(), host=ssh.host) if ssh else _("app.server.local_label", provider=provider.name.capitalize())
    connections.append(ServerConnection(label=label, provider=provider, ssh=ssh))
    return ServerManager(connections)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Termainer — Container observability and operations from your terminal"
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("doctor",),
        help="Run a non-interactive environment diagnostic",
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
        version=f"%(prog)s {VERSION_DISPLAY}",
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
    from .locale import init as locale_init

    # Initialize locale from env var first, then override with .env
    locale_init()
    args = parse_args()

    if args.command == "doctor":
        raise SystemExit(run_doctor())

    env_file = args.env_file
    env = load_env_file(env_file) if os.path.isfile(env_file) else {}
    locale_init(env)

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
