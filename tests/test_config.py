from __future__ import annotations

import tempfile
from pathlib import Path

from termainer.config import build_ssh_from_env, load_env_file


def test_load_env_file_not_found() -> None:
    env = load_env_file("/nonexistent/.env")
    assert env == {}


def test_load_env_file_empty() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("")
        f.flush()
        env = load_env_file(f.name)
    Path(f.name).unlink(missing_ok=True)
    assert env == {}


def test_load_env_file_comments_only() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("# This is a comment\n# Another comment\n")
        f.flush()
        env = load_env_file(f.name)
    Path(f.name).unlink(missing_ok=True)
    assert env == {}


def test_load_env_file_key_value() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("TERMAINER_REMOTE_HOST=example.com\n")
        f.flush()
        env = load_env_file(f.name)
    Path(f.name).unlink(missing_ok=True)
    assert env["TERMAINER_REMOTE_HOST"] == "example.com"


def test_load_env_file_quoted_values() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write('TERMAINER_REMOTE_PASSWORD="s3cret"\n')
        f.write("TERMAINER_REMOTE_USER='admin'\n")
        f.flush()
        env = load_env_file(f.name)
    Path(f.name).unlink(missing_ok=True)
    assert env["TERMAINER_REMOTE_PASSWORD"] == "s3cret"
    assert env["TERMAINER_REMOTE_USER"] == "admin"


def test_load_env_file_multiple() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("TERMAINER_REMOTE_HOST=host1\n")
        f.write("TERMAINER_REMOTE_USER=user1\n")
        f.write("TERMAINER_REMOTE_PORT=2222\n")
        f.flush()
        env = load_env_file(f.name)
    Path(f.name).unlink(missing_ok=True)
    assert env["TERMAINER_REMOTE_HOST"] == "host1"
    assert env["TERMAINER_REMOTE_USER"] == "user1"
    assert env["TERMAINER_REMOTE_PORT"] == "2222"


def test_build_ssh_from_env_no_host() -> None:
    env = {"TERMAINER_REMOTE_USER": "ubuntu"}
    result = build_ssh_from_env(env)
    assert result is None


def test_build_ssh_from_env_minimal() -> None:
    env = {"TERMAINER_REMOTE_HOST": "example.com"}
    ssh = build_ssh_from_env(env)
    assert ssh is not None
    assert ssh.host == "example.com"
    assert ssh.user == "root"
    assert ssh.port == 22
    assert ssh.key_path is None
    assert ssh.password is None


def test_build_ssh_from_env_full() -> None:
    env = {
        "TERMAINER_REMOTE_HOST": "example.com",
        "TERMAINER_REMOTE_USER": "admin",
        "TERMAINER_REMOTE_KEY_PATH": "/path/to/key.pem",
        "TERMAINER_REMOTE_PORT": "2222",
    }
    ssh = build_ssh_from_env(env)
    assert ssh.host == "example.com"
    assert ssh.user == "admin"
    assert ssh.port == 2222


def test_build_ssh_from_env_password() -> None:
    env = {
        "TERMAINER_REMOTE_HOST": "example.com",
        "TERMAINER_REMOTE_PASSWORD": "s3cret",
    }
    ssh = build_ssh_from_env(env)
    assert ssh.password == "s3cret"


def test_build_ssh_from_env_cli_overrides() -> None:
    env = {"TERMAINER_REMOTE_HOST": "env-host.com"}
    ssh = build_ssh_from_env(env, cli_host="cli-host.com", cli_user="cli-user")
    assert ssh.host == "cli-host.com"
    assert ssh.user == "cli-user"


def test_build_ssh_from_env_cli_host_without_env() -> None:
    ssh = build_ssh_from_env({}, cli_host="cli-host.com", cli_user="cli-user")
    assert ssh is not None
    assert ssh.host == "cli-host.com"
    assert ssh.user == "cli-user"


def test_build_ssh_from_env_cli_port() -> None:
    env = {"TERMAINER_REMOTE_HOST": "host.com"}
    ssh = build_ssh_from_env(env, cli_port=2222)
    assert ssh.port == 2222


def test_get_provider_from_env_none() -> None:
    from termainer.config import get_provider_from_env
    assert get_provider_from_env({}) is None


def test_get_provider_from_env_set() -> None:
    from termainer.config import get_provider_from_env
    assert get_provider_from_env({"TERMAINER_REMOTE_PROVIDER": "docker"}) == "docker"


def test_get_provider_from_env_empty_string() -> None:
    from termainer.config import get_provider_from_env
    assert get_provider_from_env({"TERMAINER_REMOTE_PROVIDER": ""}) is None
