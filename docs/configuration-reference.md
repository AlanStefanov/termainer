# Configuration Reference

Termainer can be configured to monitor containers across multiple servers. This document covers all configuration options.

---

## Configuration File

Create `~/.config/termainer/config.yaml` (or `$XDG_CONFIG_HOME/termainer/config.yaml`).

The app also looks for `./config.yaml` (current working directory) as a fallback.

### Global Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `lang` | string | `"en"` | UI language. Supported: `en`, `es` |

### Server Entries

Each server under the `servers` list has these fields:

| Field | Required | Type | Default | Description |
|-------|----------|------|---------|-------------|
| `label` | **yes** | string | — | Display name shown in the UI |
| `provider` | **yes** | string | — | Container runtime: `docker`, `swarm`, `podman`, `kubernetes`, `k8s`, `openshift` |
| `host` | no | string | — | SSH host (IP or hostname). Omit for local Docker/Podman |
| `user` | no | string | `"root"` | SSH user |
| `key` | no | string | — | Path to SSH private key (`.pem` file). Use `~` for home dir |
| `password` | no | string | — | SSH password (requires `sshpass` installed). Not recommended |
| `port` | no | integer | `22` | SSH port |

### Example: Full config

```yaml
lang: en

servers:
  # Local server (no host field)
  - label: "Local Docker"
    provider: docker

  # Remote EC2 with key-based auth
  - label: "Production Web"
    host: ec2-54-123-45-67.us-east-1.compute.amazonaws.com
    user: ubuntu
    key: ~/.ssh/production.pem
    provider: docker

  # Remote K8s cluster
  - label: "Staging K8s"
    host: k8s-staging.example.com
    user: admin
    key: ~/.ssh/staging-key
    provider: kubernetes

  # Podman on a VPS
  - label: "Dev Podman"
    host: 192.168.1.50
    user: dev
    key: ~/.ssh/dev.pem
    provider: podman
    port: 2222
```

### Example: Config in Spanish

```yaml
lang: es

servers:
  - label: "Docker Local"
    provider: docker

  - label: "Servidor Producción"
    host: ec2-54-123-45-67.us-east-1.compute.amazonaws.com
    user: ubuntu
    key: ~/.ssh/production.pem
    provider: docker
```

> **Note**: The key is always `servers`, regardless of language (`lang`).

---

## Single Server via .env

If you only need to monitor one remote server, you can use a `.env` file instead of YAML:

```bash
cp .env.example .env
# Edit .env with your server details
termainer
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TERMAINER_REMOTE_HOST` | **yes** | — | Remote host (IP or hostname) |
| `TERMAINER_REMOTE_USER` | no | `root` | SSH user |
| `TERMAINER_REMOTE_KEY_PATH` | no* | — | SSH private key path |
| `TERMAINER_REMOTE_PASSWORD` | no* | — | SSH password (requires `sshpass`) |
| `TERMAINER_REMOTE_PORT` | no | `22` | SSH port |
| `TERMAINER_REMOTE_PROVIDER` | no | auto | Provider override: `docker`, `swarm`, `kubernetes`, `podman`, `openshift` |
| `TERMAINER_LANG` | no | `en` | UI language: `en` or `es` |

\* Either `TERMAINER_REMOTE_KEY_PATH` or `TERMAINER_REMOTE_PASSWORD` must be set (or none if using SSH agent).

---

## CLI Flags Reference

All CLI flags override both `.env` and `config.yaml` values.

| Flag | Description |
|------|-------------|
| `--provider` | Provider: `auto` (default), `docker`, `swarm`, `podman`, `kubernetes`, `k8s`, `openshift` |
| `--host` | SSH host (overrides env/config) |
| `--ssh-user` | SSH user |
| `--ssh-key` | SSH key path |
| `--ssh-password` | SSH password |
| `--ssh-port` | SSH port |
| `--config` | Path to config.yaml (default: auto-detect XDG path) |
| `--env` | Path to .env file (default: `.env`) |
| `--version` | Show version and exit |

---

## Precedence

Values are resolved in this order (last wins):

1. Defaults (hardcoded in the app)
2. `config.yaml` values
3. `.env` file values
4. CLI flags (`--host`, `--ssh-user`, etc.)

---

## SSH Authentication

### Key-based (recommended)

```bash
# EC2 / cloud servers
termainer --host ec2-54-123-45-67.compute.amazonaws.com \
          --ssh-user ubuntu \
          --ssh-key ~/.ssh/production.pem
```

### Password-based

Requires `sshpass`:

```bash
sudo apt install sshpass   # Debian/Ubuntu
sudo yum install sshpass   # RHEL/CentOS
```

```bash
termainer --host 192.168.1.100 \
          --ssh-user root \
          --ssh-password 'mypassword'
```

### SSH Agent

If neither key nor password is provided, Termainer uses your SSH agent (default SSH behavior).

---

## Language Selection

Termainer supports **English** and **Spanish** for the UI.

Set it via:

1. **Config file**: `lang: es` in `config.yaml`
2. **Environment variable**: `TERMAINER_LANG=es`
3. **Detection will be automatic in future releases** (uses `locale.getdefaultlocale()`)

---

## Multi-Server Tips

- **Naming**: Use descriptive labels (e.g., "Prod Web", "Staging K8s", "Dev Docker") to identify servers quickly.
- **Technology-First Navigation**: The environment screen is technology-based (Docker, Swarm, Podman, Kubernetes, OpenShift).
- **All Servers View**: Inside each technology dashboard, select "All" to aggregate resources from every server of that technology.
- **Server Tabs**: Switch between servers directly in the dashboard using the tabs at the top.
- **Backward Compat**: If you don't create a config file, Termainer falls back to `.env` / CLI flags (single server mode) or auto-detects a local provider.
