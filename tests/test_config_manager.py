from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from termainer.config_manager import (
    AppConfig,
    ServerConfig,
    _get_config_paths,
    _parse_yaml,
    load_config,
)


def test_server_config_defaults() -> None:
    sc = ServerConfig(label="test", provider="docker")
    assert sc.label == "test"
    assert sc.provider == "docker"
    assert sc.host is None
    assert sc.user == "root"
    assert sc.key_path is None
    assert sc.password is None
    assert sc.port == 22


def test_server_config_remote() -> None:
    sc = ServerConfig(
        label="prod",
        provider="kubernetes",
        host="k8s.example.com",
        user="admin",
        key_path="/home/user/.ssh/key.pem",
        port=2222,
    )
    assert sc.host == "k8s.example.com"
    assert sc.user == "admin"
    assert sc.key_path == "/home/user/.ssh/key.pem"
    assert sc.port == 2222


def test_app_config_defaults() -> None:
    cfg = AppConfig()
    assert cfg.lang == "en"
    assert cfg.servers == []


def test_app_config_with_servers() -> None:
    servers = [ServerConfig(label="local", provider="docker")]
    cfg = AppConfig(lang="es", servers=servers)
    assert cfg.lang == "es"
    assert len(cfg.servers) == 1


def test_get_config_paths_includes_xdg(monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    paths = _get_config_paths()
    assert any("custom/config/termainer/config.yaml" in str(p) for p in paths)


def test_get_config_paths_fallback_home(monkeypatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    paths = _get_config_paths()
    assert any(str(p).endswith(".config/termainer/config.yaml") for p in paths)


def test_get_config_paths_includes_cwd() -> None:
    paths = _get_config_paths()
    assert any(str(p).endswith("config.yaml") and len(str(p)) < 100 for p in paths)


def test_parse_yaml_empty() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        f.flush()
        cfg = _parse_yaml(Path(f.name))
    os.unlink(f.name)
    assert cfg.lang == "en"
    assert cfg.servers == []


def test_parse_yaml_single_server() -> None:
    yaml_content = """
lang: es
servers:
  - label: "Local Docker"
    provider: docker
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        cfg = _parse_yaml(Path(f.name))
    os.unlink(f.name)
    assert cfg.lang == "es"
    assert len(cfg.servers) == 1
    assert cfg.servers[0].label == "Local Docker"
    assert cfg.servers[0].provider == "docker"
    assert cfg.servers[0].host is None
    assert cfg.servers[0].user == "root"


def test_parse_yaml_multi_server() -> None:
    yaml_content = """
lang: en
servers:
  - label: "Local Docker"
    provider: docker
  - label: "Production"
    host: ec2.example.com
    user: ubuntu
    key: ~/.ssh/prod.pem
    provider: kubernetes
    port: 2222
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        cfg = _parse_yaml(Path(f.name))
    os.unlink(f.name)
    assert len(cfg.servers) == 2
    assert cfg.servers[0].label == "Local Docker"
    assert cfg.servers[0].host is None

    s1 = cfg.servers[1]
    assert s1.label == "Production"
    assert s1.host == "ec2.example.com"
    assert s1.user == "ubuntu"
    assert s1.key_path == "~/.ssh/prod.pem"
    assert s1.provider == "kubernetes"
    assert s1.port == 2222


def test_parse_yaml_key_alias() -> None:
    """'key' and 'key_path' should both work."""
    yaml_content = """
servers:
  - label: "Test"
    provider: docker
    host: 192.168.1.1
    key_path: /path/to/key
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        cfg = _parse_yaml(Path(f.name))
    os.unlink(f.name)
    assert cfg.servers[0].key_path == "/path/to/key"


def test_parse_yaml_with_password() -> None:
    yaml_content = """
servers:
  - label: "Test"
    provider: docker
    host: 192.168.1.1
    user: admin
    password: s3cret
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        cfg = _parse_yaml(Path(f.name))
    os.unlink(f.name)
    assert cfg.servers[0].password == "s3cret"
    assert cfg.servers[0].user == "admin"


def test_load_config_no_file() -> None:
    """With no config file, load_config should return defaults."""
    cfg = load_config()
    assert cfg.lang == "en"
    assert cfg.servers == []


def test_parse_yaml_unknown_field_ignored() -> None:
    """Unknown fields should be silently ignored."""
    yaml_content = """
servers:
  - label: "Test"
    provider: docker
    unknown_field: "should be ignored"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        cfg = _parse_yaml(Path(f.name))
    os.unlink(f.name)
    assert len(cfg.servers) == 1
    assert cfg.servers[0].label == "Test"


def test_parse_yaml_missing_label_raises() -> None:
    """Missing required 'label' field should raise KeyError."""
    yaml_content = """
servers:
  - provider: docker
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        with pytest.raises(KeyError):
            _parse_yaml(Path(f.name))
    os.unlink(f.name)
