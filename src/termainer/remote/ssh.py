from __future__ import annotations

import asyncio
import os
import shutil
from typing import Optional


class SSHConnection:
    def __init__(
        self,
        host: str,
        user: str = "root",
        key_path: Optional[str] = None,
        password: Optional[str] = None,
        port: int = 22,
    ) -> None:
        self.host = host
        self.user = user
        self.key_path = os.path.expanduser(key_path) if key_path else None
        self.password = password
        self.port = port
        self._use_sshpass = bool(password) and shutil.which("sshpass") is not None
        self._password_warned = False

    def _build_base_args(self) -> list[str]:
        args = [
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            "-o", "BatchMode=yes",
        ]
        if self.key_path:
            args.extend(["-i", self.key_path])
        if self.port != 22:
            args.extend(["-p", str(self.port)])
        return args

    def _target(self) -> str:
        return f"{self.user}@{self.host}"

    def _build_command(self, remote_cmd: list[str]) -> list[str]:
        if self._use_sshpass:
            cmd = ["sshpass", "-e", "ssh"]
        else:
            cmd = ["ssh"]
        cmd.extend(self._build_base_args())
        cmd.append(self._target())
        cmd.extend(remote_cmd)
        return cmd

    async def run(self, command: list[str]) -> str:
        cmd = self._build_command(command)
        env = os.environ.copy()
        if self._use_sshpass:
            env["SSHPASS"] = self.password

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace").strip()
            if not self._use_sshpass and self.password and not self._password_warned:
                self._password_warned = True
                raise RuntimeError(
                    f"SSH command failed: {err}\n"
                    "Hint: install 'sshpass' for password-based authentication"
                )
            raise RuntimeError(f"SSH command failed: {err}")
        return stdout.decode("utf-8", errors="replace")

    async def stream(self, command: list[str]) -> asyncio.StreamReader:
        cmd = self._build_command(command)
        env = os.environ.copy()
        if self._use_sshpass:
            env["SSHPASS"] = self.password

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
        return proc.stdout

    def __repr__(self) -> str:
        return f"{self.user}@{self.host}:{self.port}"
