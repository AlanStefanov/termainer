from __future__ import annotations

import asyncio
import json
import shutil
from typing import AsyncIterator, List, Optional

from ..remote.ssh import SSHConnection
from .kubernetes import KubernetesProvider


class OpenShiftProvider(KubernetesProvider):
    name = "openshift"

    def __init__(self, ssh: Optional[SSHConnection] = None) -> None:
        super().__init__(ssh=ssh)
        self._oc_path: Optional[str] = None

    async def is_available(self) -> bool:
        if self._ssh:
            try:
                await self._ssh.run(["oc", "whoami"])
                self._kubectl_path = "oc"
                return True
            except RuntimeError:
                return False
        self._kubectl_path = shutil.which("oc")
        if not self._kubectl_path:
            return False
        proc = await asyncio.create_subprocess_exec(
            self._kubectl_path, "whoami",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        code = await proc.wait()
        return code == 0

    async def list_containers(self) -> List[dict]:
        raw = await self._run(
            "get", "pods", "--all-namespaces", "-o", "json"
        )
        data = json.loads(raw)
        pods = []
        for item in data.get("items", []):
            pods.append({
                "id": f"{item['metadata']['namespace']}/{item['metadata']['name']}",
                "name": item["metadata"]["name"],
                "namespace": item["metadata"]["namespace"],
                "status": item["status"]["phase"],
                "node": item.get("spec", {}).get("nodeName", ""),
                "containers": [
                    c["name"] for c in item["spec"]["containers"]
                ],
                "raw": item,
            })
        return pods

    async def stats(self, container_id: str) -> AsyncIterator[dict]:
        namespace, name = self._parse_id(container_id)
        while True:
            try:
                raw = await self._run(
                    "adm", "top", "pod", name, "-n", namespace
                )
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
