from __future__ import annotations

import asyncio
import json
import shlex
import shutil
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, List, Optional, Tuple

from ..remote.ssh import SSHConnection
from .base import ContainerDetails, ContainerStats, ContainerSummary


class KubernetesProvider:
    name = "kubernetes"

    def __init__(self, ssh: Optional[SSHConnection] = None) -> None:
        self._kubectl_path: Optional[str] = None
        self._ssh = ssh

    async def is_available(self) -> bool:
        if self._ssh:
            try:
                await self._ssh.run(["kubectl", "cluster-info"])
                self._kubectl_path = "kubectl"
                return True
            except RuntimeError:
                return False
        self._kubectl_path = shutil.which("kubectl")
        if not self._kubectl_path:
            return False
        proc = await asyncio.create_subprocess_exec(
            self._kubectl_path, "cluster-info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        code = await proc.wait()
        return code == 0

    async def list_containers(self) -> List[ContainerSummary]:
        raw = await self._run(
            "get", "pods", "--all-namespaces", "-o", "json"
        )
        data = json.loads(raw)
        pods = []
        for item in data.get("items", []):
            status = item.get("status", {})
            spec = item.get("spec", {})
            metadata = item.get("metadata", {})
            container_statuses = status.get("containerStatuses", [])
            containers = spec.get("containers", [])
            ready = sum(1 for c in container_statuses if c.get("ready"))
            total = len(containers)
            restarts = sum(int(c.get("restartCount", 0)) for c in container_statuses)
            images = [c.get("image", "") for c in containers]
            namespace = metadata.get("namespace", "default")
            name = metadata.get("name", "unknown")
            pods.append({
                "id": f"{namespace}/{name}",
                "name": name,
                "namespace": namespace,
                "status": status.get("phase", "Unknown"),
                "image": ", ".join(images),
                "node": spec.get("nodeName", ""),
                "ready": f"{ready}/{total}",
                "restart": str(restarts),
                "created": self._age(metadata.get("creationTimestamp", "")),
                "networks": status.get("podIP", ""),
                "ports": self._ports(containers),
                "containers": [c.get("name", "") for c in containers],
                "raw": item,
            })
        return pods

    async def inspect(self, container_id: str) -> ContainerDetails:
        namespace, name = self._parse_id(container_id)
        raw = await self._run(
            "get", "pod", name, "-n", namespace, "-o", "json"
        )
        return json.loads(raw)

    async def stats(self, container_id: str) -> AsyncIterator[ContainerStats]:
        namespace, name = self._parse_id(container_id)
        if self._ssh:
            async with self._ssh.stream([
                "sh", "-c",
                f"while true; do {self._kubectl_path} top pod {name} -n {namespace}; sleep 2; done"
            ]) as reader:
                while True:
                    line = await reader.readline()
                    if not line:
                        break
                    line = line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) >= 3 and parts[0] != "NAME":
                        yield {
                            "pod": name,
                            "namespace": namespace,
                            "cpu": parts[1],
                            "memory": parts[2],
                        }
        else:
            while True:
                try:
                    raw = await self._run("top", "pod", name, "-n", namespace)
                    lines = raw.strip().split("\n")
                    if len(lines) >= 2:
                        parts = lines[1].split()
                        if len(parts) >= 3:
                            yield {
                                "pod": name,
                                "namespace": namespace,
                                "cpu": parts[1],
                                "memory": parts[2],
                            }
                except RuntimeError:
                    yield {"pod": name, "namespace": namespace, "cpu": "N/A", "memory": "N/A"}
                await asyncio.sleep(2)

    async def logs(
        self, container_id: str, tail: int = 100, follow: bool = False
    ) -> AsyncIterator[str]:
        namespace, name = self._parse_id(container_id)
        cmd = ["logs", "--tail", str(tail), name, "-n", namespace]
        if follow:
            cmd.append("-f")

        if self._ssh:
            async with self._ssh.stream(["kubectl"] + cmd) as reader:
                while True:
                    line = await reader.readline()
                    if not line:
                        break
                    yield line.decode("utf-8", errors="replace").rstrip("\n")
                    if not follow:
                        break
        else:
            proc = await asyncio.create_subprocess_exec(
                self._kubectl_path, *cmd,
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
        env_dict: Dict[str, str] = {}
        containers = (
            details.get("spec", {}).get("containers", [])
        )
        for container in containers:
            for env in container.get("env", []):
                key = env.get("name", "")
                val = env.get("value", "")
                if not val and env.get("valueFrom"):
                    val = "<valueFrom>"
                if key:
                    env_dict[key] = val
        return env_dict

    async def start(self, container_id: str) -> None:
        raise RuntimeError("Start no aplica a pods de Kubernetes")

    async def stop(self, container_id: str) -> None:
        raise RuntimeError("Stop no aplica a pods de Kubernetes; usa delete/scale en una futura vista Kubernetes")

    async def restart(self, container_id: str) -> None:
        raise RuntimeError("Restart de Kubernetes se implementara sobre deployments/rollouts")

    async def remove(self, container_id: str, force: bool = False) -> None:
        namespace, name = self._parse_id(container_id)
        await self._run("delete", "pod", name, "-n", namespace)

    async def set_restart_policy(self, container_id: str, policy: str) -> None:
        raise RuntimeError(
            "En Kubernetes la política de reinicio (restartPolicy) está definida en el "
            "manifiesto del Deployment/StatefulSet y no puede cambiarse en un pod en ejecución. "
            "Usa 'kubectl edit deployment <nombre>' para modificarla y forzar un rollout."
        )

    async def exec_command(self, container_id: str, command: str) -> AsyncIterator[str]:
        namespace, name = self._parse_id(container_id)
        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()
        cmd = ["exec", name, "-n", namespace, "--"] + parts
        if self._ssh:
            async with self._ssh.stream(["kubectl"] + cmd) as reader:
                while True:
                    line = await reader.readline()
                    if not line:
                        break
                    yield line.decode("utf-8", errors="replace").rstrip("\n")
        else:
            proc = await asyncio.create_subprocess_exec(
                self._kubectl_path, *cmd,
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

    def _parse_id(self, container_id: str) -> Tuple[str, str]:
        if "/" in container_id:
            namespace, name = container_id.split("/", 1)
            return namespace, name
        return "default", container_id

    @staticmethod
    def _ports(containers: list[dict]) -> str:
        ports = []
        for container in containers:
            for port in container.get("ports", []):
                container_port = port.get("containerPort")
                protocol = port.get("protocol", "TCP")
                if container_port:
                    ports.append(f"{container_port}/{protocol.lower()}")
        return ", ".join(ports)

    @staticmethod
    def _age(timestamp: str) -> str:
        if not timestamp:
            return ""
        try:
            created = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return timestamp
        delta = datetime.now(timezone.utc) - created
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h"
        return f"{hours // 24}d"

    async def _run(self, *args: str) -> str:
        if self._ssh:
            return await self._ssh.run(["kubectl"] + list(args))
        proc = await asyncio.create_subprocess_exec(
            self._kubectl_path, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"kubectl {' '.join(args)} failed: {stderr.decode()}"
            )
        return stdout.decode("utf-8", errors="replace")
