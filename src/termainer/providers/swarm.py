from __future__ import annotations

import asyncio
import json
import shutil
from typing import AsyncIterator, Dict, List, Optional

from ..remote.ssh import SSHConnection
from .base import ContainerDetails, ContainerStats, ContainerSummary


class SwarmProvider:
    name = "swarm"

    def __init__(self, ssh: Optional[SSHConnection] = None) -> None:
        self._docker_path: Optional[str] = None
        self._ssh = ssh

    async def is_available(self) -> bool:
        if self._ssh:
            try:
                state = (await self._ssh.run(["docker", "info", "--format", "{{.Swarm.LocalNodeState}}"])).strip().lower()
                self._docker_path = "docker"
                return state == "active"
            except RuntimeError:
                return False

        self._docker_path = shutil.which("docker")
        if not self._docker_path:
            return False

        proc = await asyncio.create_subprocess_exec(
            self._docker_path,
            "info",
            "--format",
            "{{.Swarm.LocalNodeState}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return False
        state = stdout.decode("utf-8", errors="replace").strip().lower()
        return state == "active"

    async def list_containers(self) -> List[ContainerSummary]:
        raw = await self._run("service", "ls", "--format", "{{json .}}")
        services: List[ContainerSummary] = []
        for line in raw.strip().split("\n"):
            if not line.strip():
                continue
            item = json.loads(line)
            sid = item.get("ID", "")
            name = item.get("Name", "")
            mode = item.get("Mode", "")
            replicas = item.get("Replicas", "")
            image = item.get("Image", "")
            ports = item.get("Ports", "")
            status = f"{mode} {replicas}".strip()
            services.append(
                {
                    "id": sid,
                    "name": name,
                    "image": image,
                    "status": status,
                    "ports": ports,
                    "mode": mode,
                    "replicas": replicas,
                }
            )
        return services

    async def inspect(self, container_id: str) -> ContainerDetails:
        raw = await self._run("service", "inspect", container_id)
        data = json.loads(raw)
        if isinstance(data, list):
            return data[0] if data else {}
        return data

    async def stats(self, container_id: str) -> AsyncIterator[ContainerStats]:
        while True:
            yield {
                "cpu": "N/A",
                "memory": "N/A",
                "net_io": "N/A",
                "pids": "N/A",
            }
            await asyncio.sleep(2)

    async def logs(
        self, container_id: str, tail: int = 100, follow: bool = False
    ) -> AsyncIterator[str]:
        cmd = ["service", "logs", "--raw", "--tail", str(tail)]
        if follow:
            cmd.append("-f")
        cmd.append(container_id)

        if self._ssh:
            stream = await self._ssh.stream(["docker"] + cmd)
        else:
            proc = await asyncio.create_subprocess_exec(
                self._docker_path,
                *cmd,
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
            details.get("Spec", {})
            .get("TaskTemplate", {})
            .get("ContainerSpec", {})
            .get("Env", [])
        )
        env_dict: Dict[str, str] = {}
        for entry in env_list:
            if "=" in entry:
                key, _, val = entry.partition("=")
                env_dict[key] = val
        return env_dict

    async def start(self, container_id: str) -> None:
        await self._run("service", "scale", f"{container_id}=1")

    async def stop(self, container_id: str) -> None:
        await self._run("service", "scale", f"{container_id}=0")

    async def restart(self, container_id: str) -> None:
        await self._run("service", "update", "--force", container_id)

    async def remove(self, container_id: str, force: bool = False) -> None:
        await self._run("service", "rm", container_id)

    async def close(self) -> None:
        pass

    async def _run(self, *args: str) -> str:
        if self._ssh:
            return await self._ssh.run(["docker"] + list(args))
        proc = await asyncio.create_subprocess_exec(
            self._docker_path,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"docker {' '.join(args)} failed: {stderr.decode()}")
        return stdout.decode("utf-8", errors="replace")
