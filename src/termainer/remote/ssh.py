from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from typing import Optional


class SSHConnection:
    def __init__(
        self,
        host: str,
        user: Optional[str] = None,
        key_path: Optional[str] = None,
        password: Optional[str] = None,
        port: int = 22,
    ) -> None:
        self.host = host
        self.user = user  # None → let SSH config resolve the user
        self.key_path = os.path.expanduser(key_path) if key_path else None
        self.password = password
        self.port = port
        self._use_sshpass = bool(password) and shutil.which("sshpass") is not None
        self._password_warned = False
        self._tunnel_proc: Optional[asyncio.subprocess.Process] = None
        self._tunnel_socket: Optional[str] = None

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
        if self.user:
            return f"{self.user}@{self.host}"
        return self.host

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

    async def create_tunnel(
        self,
        remote_socket: str = "/var/run/docker.sock",
    ) -> str:
        """Create an SSH tunnel forwarding a remote Unix socket to a local temp socket.

        Args:
            remote_socket: Path to the remote Unix socket to forward.

        Returns:
            Path to the local tunnel socket.

        Raises:
            RuntimeError: If the tunnel process fails to start.
        """
        tmp = tempfile.mktemp(suffix=".sock", prefix="termainer-")
        cmd = ["ssh", "-N", "-L", f"{tmp}:{remote_socket}"]
        cmd.extend(self._build_base_args())
        cmd.append(self._target())

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        # Wait for the socket to appear or process to fail
        for _ in range(20):
            if proc.returncode is not None:
                _, stderr = await proc.communicate()
                raise RuntimeError(
                    f"SSH tunnel failed: {stderr.decode('utf-8', errors='replace').strip()}"
                )
            if os.path.exists(tmp):
                break
            await asyncio.sleep(0.25)
        else:
            # Socket never appeared — kill the process
            proc.kill()
            await proc.wait()
            raise RuntimeError("SSH tunnel timed out waiting for socket")

        self._tunnel_proc = proc
        self._tunnel_socket = tmp
        return tmp

    async def close_tunnel(self) -> None:
        """Close the SSH tunnel if one is open."""
        if self._tunnel_proc:
            try:
                self._tunnel_proc.kill()
                await self._tunnel_proc.wait()
            except Exception:
                pass
            self._tunnel_proc = None
        if self._tunnel_socket:
            try:
                os.unlink(self._tunnel_socket)
            except (FileNotFoundError, OSError):
                pass
            self._tunnel_socket = None

    def __repr__(self) -> str:
        user = self.user or ""
        return f"{user}@{self.host}:{self.port}" if user else f"{self.host}:{self.port}"
