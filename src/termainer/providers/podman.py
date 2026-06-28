from __future__ import annotations

import asyncio
import json
import shlex
import shutil
from typing import AsyncIterator, Dict, List, Optional

from ..remote.ssh import SSHConnection
from .base import ContainerDetails, ContainerStats, ContainerSummary


class PodmanProvider:
    name = "podman"

    def __init__(self, ssh: Optional[SSHConnection] = None) -> None:
        self._podman_path: Optional[str] = None
        self._ssh = ssh

    async def is_available(self) -> bool:
        if self._ssh:
            try:
                await self._ssh.run(["podman", "info"])
                self._podman_path = "podman"
                return True
            except RuntimeError:
                return False
        self._podman_path = shutil.which("podman")
        if not self._podman_path:
            return False
        proc = await asyncio.create_subprocess_exec(
            self._podman_path, "info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        code = await proc.wait()
        return code == 0

    async def list_containers(self) -> List[ContainerSummary]:
        raw = await self._run("ps", "-a", "--format", "json")
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        return [data] if data else []

    async def inspect(self, container_id: str) -> ContainerDetails:
        raw = await self._run("inspect", container_id)
        data = json.loads(raw)
        if isinstance(data, list):
            return data[0] if data else {}
        return data

    async def stats(self, container_id: str) -> AsyncIterator[ContainerStats]:
        if self._ssh:
            async with self._ssh.stream([
                "sh", "-c",
                f"while true; do {self._podman_path} stats --no-stream --format json {container_id}; sleep 1; done"
            ]) as reader:
                while True:
                    line = await reader.readline()
                    if not line:
                        break
                    raw = line.decode("utf-8", errors="replace").strip()
                    if raw:
                        data = json.loads(raw)
                        if isinstance(data, list):
                            if data:
                                yield data[0]
                        else:
                            yield data
        else:
            while True:
                raw = await self._run("stats", "--no-stream", "--format", "json", container_id)
                if raw.strip():
                    data = json.loads(raw)
                    if isinstance(data, list):
                        if data:
                            yield data[0]
                    else:
                        yield data
                await asyncio.sleep(1)

    async def logs(
        self, container_id: str, tail: int = 100, follow: bool = False
    ) -> AsyncIterator[str]:
        cmd = ["logs", "--tail", str(tail)]
        if follow:
            cmd.append("-f")
        cmd.append(container_id)

        if self._ssh:
            async with self._ssh.stream(["podman"] + cmd) as reader:
                while True:
                    line = await reader.readline()
                    if not line:
                        break
                    yield line.decode("utf-8", errors="replace").rstrip("\n")
                    if not follow:
                        break
        else:
            proc = await asyncio.create_subprocess_exec(
                self._podman_path, *cmd,
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
            async with self._ssh.stream(["podman"] + cmd) as reader:
                while True:
                    line = await reader.readline()
                    if not line:
                        break
                    yield line.decode("utf-8", errors="replace").rstrip("\n")
        else:
            proc = await asyncio.create_subprocess_exec(
                self._podman_path, *cmd,
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
            return await self._ssh.run(["podman"] + list(args))
        proc = await asyncio.create_subprocess_exec(
            self._podman_path, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"podman {' '.join(args)} failed: {stderr.decode()}"
            )
        return stdout.decode("utf-8", errors="replace")
