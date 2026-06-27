"""Tests for SSH config parsing functionality."""

from __future__ import annotations

from pathlib import Path
import tempfile

from termainer.ssh_config import parse_ssh_config, SSHServer, filter_ssh_servers_for_container_mgmt, get_ssh_servers


def test_parse_ssh_config_empty_file() -> None:
    """Empty SSH config should return empty dict."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.config') as f:
        f.write("")
        f.flush()
        config_path = f.name
    
    try:
        result = parse_ssh_config(config_path)
        assert result == {}
    finally:
        Path(config_path).unlink()


def test_parse_ssh_config_single_host() -> None:
    """Single host entry should be parsed correctly."""
    config_content = """
Host prod-web
    HostName ec2-54-123-45-67.us-east-1.compute.amazonaws.com
    User ubuntu
    IdentityFile ~/.ssh/production.pem
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.config') as f:
        f.write(config_content)
        f.flush()
        config_path = f.name
    
    try:
        result = parse_ssh_config(config_path)
        assert "prod-web" in result
        server = result["prod-web"]
        assert server.host == "prod-web"
        assert server.hostname == "ec2-54-123-45-67.us-east-1.compute.amazonaws.com"
        assert server.user == "ubuntu"
        assert server.port == 22
        assert server.identity_file == "~/.ssh/production.pem"
    finally:
        Path(config_path).unlink()


def test_parse_ssh_config_multiple_hosts() -> None:
    """Multiple host entries should be parsed correctly."""
    config_content = """
Host prod-web
    HostName prod.example.com
    User ubuntu

Host staging-k8s
    HostName staging.example.com
    User admin
    Port 2222

Host dev-local
    HostName 192.168.1.100
    User devuser
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.config') as f:
        f.write(config_content)
        f.flush()
        config_path = f.name
    
    try:
        result = parse_ssh_config(config_path)
        assert len(result) == 3
        assert "prod-web" in result
        assert "staging-k8s" in result
        assert "dev-local" in result
        
        # Check port override
        assert result["staging-k8s"].port == 2222
        assert result["prod-web"].port == 22
    finally:
        Path(config_path).unlink()


def test_parse_ssh_config_with_comments() -> None:
    """Comments should be ignored."""
    config_content = """
# This is a comment
Host prod-web
    HostName prod.example.com
    # Another comment
    User ubuntu
"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.config') as f:
        f.write(config_content)
        f.flush()
        config_path = f.name
    
    try:
        result = parse_ssh_config(config_path)
        assert len(result) == 1
        assert "prod-web" in result
    finally:
        Path(config_path).unlink()


def test_ssh_server_display_name() -> None:
    """SSHServer display_name should format correctly."""
    server1 = SSHServer(host="prod-web", hostname="prod.example.com")
    assert server1.display_name == "prod-web (prod.example.com)"
    
    server2 = SSHServer(host="local", hostname="local")
    assert server2.display_name == "local"


def test_filter_ssh_servers_for_container_mgmt() -> None:
    """Should filter out localhost entries."""
    servers = {
        "prod": SSHServer(host="prod", hostname="prod.example.com"),
        "local": SSHServer(host="local", hostname="localhost"),
        "dev": SSHServer(host="dev", hostname="192.168.1.100"),
        "loopback": SSHServer(host="loopback", hostname="127.0.0.1"),
    }
    
    result = filter_ssh_servers_for_container_mgmt(servers)
    assert len(result) == 2
    assert "prod" in result
    assert "dev" in result
    assert "local" not in result
    assert "loopback" not in result


def test_parse_ssh_config_no_file() -> None:
    """Parsing non-existent file should return empty dict."""
    result = parse_ssh_config("/nonexistent/path/.ssh/config")
    assert result == {}


def test_get_ssh_servers_integration() -> None:
    """get_ssh_servers should use ~/.ssh/config if it exists."""
    # This test verifies the integration, actual content depends on system config
    result = get_ssh_servers()
    # Just check that it returns a dict (even if empty)
    assert isinstance(result, dict)
