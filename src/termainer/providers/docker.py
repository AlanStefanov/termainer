from __future__ import annotations

import asyncio
import json
import re
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
        raw = await self._run("ps", "-a", "--format", "{{json .}}")
        containers = []
        for line in raw.strip().split("\n"):
            if not line.strip():
                continue
            item = json.loads(line)
            containers.append({k.lower(): v for k, v in item.items()})
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

    async def close(self) -> None:
        pass

    async def _run(self, *args: str) -> str:
        if self._ssh:
            return await self._ssh.run(["docker"] + list(args))
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
