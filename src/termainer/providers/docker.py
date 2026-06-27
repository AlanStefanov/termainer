from __future__ import annotations

import asyncio
import json
import re
import shlex
import shutil
from typing import AsyncIterator, Dict, List, Optional

from ..remote.ssh import SSHConnection
from .base import ContainerDetails, ContainerStats, ContainerSummary


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


class DockerProvider:
    name = "docker"

    def __init__(self, ssh: Optional[SSHConnection] = None) -> None:
        self._docker_path: Optional[str] = None
        self._ssh = ssh

    async def is_available(self) -> bool:
        if self._ssh:
            try:
                await self._ssh.run(["docker", "info"])
                self._docker_path = "docker"
                return True
            except RuntimeError:
                return False
        self._docker_path = shutil.which("docker")
        if not self._docker_path:
            return False
        proc = await asyncio.create_subprocess_exec(
            self._docker_path, "info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        code = await proc.wait()
        return code == 0

    async def list_containers(self) -> List[ContainerSummary]:
        raw_ids = await self._run("ps", "-a", "-q", "--no-trunc")
        ids = [i.strip() for i in raw_ids.split("\n") if i.strip()]
        if not ids:
            return []

        raw_details = await self._run("inspect", *ids)
        data = json.loads(raw_details)
        if not isinstance(data, list):
            data = [data]

        containers = []
        for item in data:
            cid = item.get("Id", "")
            if cid.startswith("sha256:"):
                cid = cid[7:]
            config = item.get("Config", {}) or {}
            state = item.get("State", {}) or {}
            net_settings = item.get("NetworkSettings", {}) or {}
            host_config = item.get("HostConfig", {}) or {}

            ports_raw = net_settings.get("Ports", {}) or {}
            port_str = ", ".join(
                f"{b[0]['HostPort']}->{port}"
                if b and isinstance(b, list) and len(b) > 0 and "HostPort" in b[0]
                else port
                for port, b in ports_raw.items()
            )

            networks_raw = net_settings.get("Networks", {}) or {}
            net_str = ", ".join(networks_raw.keys())

            restart = (host_config.get("RestartPolicy", {}) or {}).get("Name", "")

            containers.append({
                "id": cid,
                "names": item.get("Name", "").lstrip("/"),
                "image": config.get("Image", ""),
                "status": state.get("Status", "unknown"),
                "createdat": item.get("Created", ""),
                "ports": port_str,
                "networks": net_str,
                "restartpolicy": restart,
            })
        return containers

    async def inspect(self, container_id: str) -> ContainerDetails:
        raw = await self._run("inspect", container_id)
        data = json.loads(raw)
        if isinstance(data, list):
            return data[0] if data else {}
        return data

    async def stats(self, container_id: str) -> AsyncIterator[ContainerStats]:
        if self._ssh:
            stream = await self._ssh.stream(
                ["docker", "stats", "--format", "{{json .}}", container_id]
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                self._docker_path, "stats", "--format", "{{json .}}", container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stream = proc.stdout
        while True:
            line = await stream.readline()
            if not line:
                break
            raw = _ANSI_RE.sub("", line.decode("utf-8", errors="replace")).strip()
            if raw:
                yield json.loads(raw)

    async def logs(
        self, container_id: str, tail: int = 100, follow: bool = False
    ) -> AsyncIterator[str]:
        cmd = ["logs", "--tail", str(tail)]
        if follow:
            cmd.append("-f")
        cmd.append(container_id)

        if self._ssh:
            stream = await self._ssh.stream(["docker"] + cmd)
        else:
            proc = await asyncio.create_subprocess_exec(
                self._docker_path, *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stream = proc.stdout
        while True:
            line = await stream.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="replace").rstrip("\n")
            if not follow:
                break

    async def get_env(self, container_id: str) -> Dict[str, str]:
        details = await self.inspect(container_id)
        env_list: List[str] = (
            details.get("Config", {}).get("Env", [])
        )
        env_dict: Dict[str, str] = {}
        for entry in env_list:
            if "=" in entry:
                key, _, val = entry.partition("=")
                env_dict[key] = val
        return env_dict

    async def start(self, container_id: str) -> None:
        await self._run("start", container_id)

    async def stop(self, container_id: str) -> None:
        await self._run("stop", container_id)

    async def restart(self, container_id: str) -> None:
        await self._run("restart", container_id)

    async def remove(self, container_id: str, force: bool = False) -> None:
        args = ["rm"]
        if force:
            args.append("-f")
        args.append(container_id)
        await self._run(*args)

    async def set_restart_policy(self, container_id: str, policy: str) -> None:
        await self._run("update", "--restart", policy, container_id)

    async def exec_command(self, container_id: str, command: str) -> AsyncIterator[str]:
        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()
        cmd = ["exec", container_id] + parts
        if self._ssh:
            stream = await self._ssh.stream(["docker"] + cmd)
        else:
            proc = await asyncio.create_subprocess_exec(
                self._docker_path, *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stream = proc.stdout
        while True:
            line = await stream.readline()
            if not line:
                break
            yield line.decode("utf-8", errors="replace").rstrip("\n")

    async def close(self) -> None:
        pass

    async def _run(self, *args: str) -> str:
        if self._ssh:
            return await self._ssh.run(["docker"] + list(args))
        if self._docker_path is None:
            self._docker_path = shutil.which("docker")
        if self._docker_path is None:
            raise RuntimeError("docker not found in PATH")
        proc = await asyncio.create_subprocess_exec(
            self._docker_path, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"docker {' '.join(args)} failed: {stderr.decode()}"
            )
        return stdout.decode("utf-8", errors="replace")
