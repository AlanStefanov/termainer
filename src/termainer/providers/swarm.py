from __future__ import annotations

import asyncio
import json
import shlex
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
        raw = await self._run("service", "ls")
        services: List[ContainerSummary] = []
        lines = raw.strip().split("\n")
        if not lines:
            return services
        # Skip header line
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split(None, 5)
            if len(parts) < 4:
                continue
            sid = parts[0]
            name = parts[1]
            mode = parts[2]
            replicas = parts[3]
            image = parts[4] if len(parts) > 4 else ""
            ports = parts[5] if len(parts) > 5 else ""
            services.append(
                {
                    "id": sid,
                    "name": name,
                    "image": image,
                    "status": f"{mode} {replicas}",
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

    async def set_restart_policy(self, container_id: str, policy: str) -> None:
        # policy: "none" | "on-failure" | "any"
        await self._run("service", "update", f"--restart-condition={policy}", container_id)

    async def exec_command(self, container_id: str, command: str) -> AsyncIterator[str]:
        # Swarm services don't support exec directly — find a running task container first
        try:
            raw = await self._run(
                "service", "ps", container_id,
                "--filter", "desired-state=running",
                "--format", "{{.ID}}", "--no-trunc",
            )
            task_ids = [t.strip() for t in raw.strip().split("\n") if t.strip()]
        except Exception as e:
            yield f"[error buscando tareas del servicio: {e}]"
            return
        if not task_ids:
            yield "[error: no hay tareas en ejecución para este servicio]"
            return
        try:
            cid_raw = await self._run(
                "inspect", "--format",
                "{{.Status.ContainerStatus.ContainerID}}",
                task_ids[0],
            )
            actual_cid = cid_raw.strip()
        except Exception as e:
            yield f"[error obteniendo contenedor de la tarea: {e}]"
            return
        if not actual_cid:
            yield "[error: no se encontró contenedor para la tarea]"
            return
        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()
        cmd = ["exec", actual_cid] + parts
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
