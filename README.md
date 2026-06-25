<div align="center">

# Alan Stefanov

### Engineering Manager  · Developer Experience · Platform Engineering · FinOps · Cloud Architecture

Building scalable platforms, leading teams, and optimizing cloud operations.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Alan_Stefanov-blue?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/in/alanstefanov/)
[![Email](https://img.shields.io/badge/Email-alan.emanuel.stefanov@gmail.com-red?style=for-the-badge&logo=gmail)](mailto:alan.emanuel.stefanov@gmail.com)
[![GitHub](https://img.shields.io/badge/GitHub-AlanStefanov-black?style=for-the-badge&logo=github)](https://github.com/AlanStefanov)

</div>

---

<p align="center">
  <img src="https://i.ibb.co/BKK1DspJ/Black-Minimal-Motivation-Quote-Linked-In-Banner-1.png" alt="Alan Stefanov Banner"/>
</p>

---

<div align="center">

# Termainer

**Container observability and operations directly from your terminal.**

[![GitHub](https://img.shields.io/badge/GitHub-AlanStefanov/termainer-181717?style=flat-square&logo=github)](https://github.com/AlanStefanov/termainer)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![PyPI](https://img.shields.io/badge/PyPI-0.1.0-blue?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/termainer/)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-alanstefanov%2Ftermainer-2496ED?style=flat-square&logo=docker)](https://hub.docker.com/r/alanstefanov/termainer)
[![Homebrew](https://img.shields.io/badge/Homebrew-coming%20soon-FBB040?style=flat-square&logo=homebrew)](https://github.com/AlanStefanov/homebrew-termainer)
[![Textual](https://img.shields.io/badge/Built%20with-Textual-6C5CE7?style=flat-square)](https://textual.textualize.io/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Alan%20Stefanov-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/alanstefanov/)

<br>

> Everything you need to know about all your containers, in a single terminal.

</div>

---

## Features

| | |
|---|---|
| **📊 Live Stats** | Real-time CPU, memory, and network I/O with sparkline charts |
| **📜 Log Streaming** | Live logs with pause/resume, scroll support, and syntax highlighting |
| **🔍 Full Inspection** | Environment variables, networks, volumes, ports, and configuration |
| **🔌 Multi-Provider** | Supports **Docker**, **Docker Swarm**, **Podman**, **Kubernetes**, and **OpenShift** |
| **📤 Report Export** | Save logs with metadata for debugging and bug reporting |
| **🌐 Remote SSH Connection** | Connect to remote servers (EC2, VPS, etc.) running Docker or K8s |
| **🖥️ Multi-Server** | Monitor multiple remote and local servers simultaneously |
| **⚡ Modern TUI** | Built with Textual and Rich — fast, responsive, and terminal-native |
| **🔄 Container Lifecycle** | Start, stop, restart, and remove containers (Docker/Podman) |

---

## Installation

### From PyPI (recommended)

```bash
pip install termainer
```

### From Docker (ghcr.io — recommended)

```bash
docker run -it -v /var/run/docker.sock:/var/run/docker.sock \
  ghcr.io/alanstefanov/termainer:latest
```

### From Docker Hub (optional)

```bash
docker run -it -v /var/run/docker.sock:/var/run/docker.sock \
  alanstefanov/termainer:latest
```

### From source with install.sh

```bash
git clone https://github.com/AlanStefanov/termainer.git
cd termainer
chmod +x install.sh
./install.sh
```

Make sure `~/.local/bin` is in your `PATH`:

```bash
export PATH="$PATH:$HOME/.local/bin"
termainer
```

### Manual

```bash
git clone https://github.com/AlanStefanov/termainer.git
cd termainer
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
termainer
```

### Homebrew (coming soon)

```bash
# Once available in the official tap:
brew install termainer
```

In the meantime you can install manually from the [community tap](https://github.com/AlanStefanov/homebrew-termainer).

---

## Updating

Depending on how you installed Termainer:

| Method | Command |
|--------|---------|
| **pip** | `pip install --upgrade termainer` |
| **Docker (ghcr.io)** | `docker pull ghcr.io/alanstefanov/termainer:latest` |
| **Docker Hub** | `docker pull alanstefanov/termainer:latest` |
| **install.sh** | `cd termainer && git pull && ./install.sh` |

---

## Configuration

Termainer uses a **YAML config file** to manage multiple servers. Create `~/.config/termainer/config.yaml`:

```yaml
lang: en

servers:
  - label: "Local Docker"
    provider: docker
    # No host needed for local Docker

  - label: "Production Web"
    host: ec2-54-123-45-67.us-east-1.compute.amazonaws.com
    user: ubuntu
    key: ~/.ssh/production.pem
    provider: docker

  - label: "Staging K8s"
    host: k8s-staging.example.com
    user: admin
    key: ~/.ssh/staging-key
    provider: kubernetes
```

See the full [Configuration Reference](guide/configuration-reference.md) for all options.

### Quick single-server (.env)

For a single remote server, you can use `.env` or CLI flags instead:

```bash
termainer --host ec2-54-123-45-67.us-east-1.compute.amazonaws.com \
          --ssh-user ubuntu \
          --ssh-key ~/.ssh/production.pem \
          --provider docker
```

---

## Usage

### Display Tips (Low Resolution)

If your terminal has low vertical space (for example 1366x768), reduce terminal zoom one or two steps before launching Termainer. In most terminals this is Control + Minus.

Termainer also has responsive modes, but zooming out slightly improves readability and avoids panel clipping.

### Local

```bash
# Auto-detect provider
termainer

# Specific provider
termainer --provider docker
termainer --provider swarm
termainer --provider podman
termainer --provider kubernetes
termainer --provider openshift
```

### Remote (SSH)

Connect to remote servers running Docker or Kubernetes:

```bash
# Using CLI flags
termainer --host ec2-54-123-45-67.us-east-1.compute.amazonaws.com \
          --ssh-user ubuntu \
          --ssh-key ~/.ssh/production.pem \
          --provider docker

# Using .env (recommended for frequent use)
cp .env.example .env
# Edit .env with your server details
termainer
```

#### SSH Authentication Methods

| Method | How to use |
|---|---|
| **Key (`.pem`)** | `--ssh-key ~/.ssh/key.pem` or `TERMAINER_REMOTE_KEY_PATH` in `.env` |
| **Password** | `--ssh-password 'mypass'` or `TERMAINER_REMOTE_PASSWORD` in `.env` (requires `sshpass`) |

For password-based auth, install `sshpass`:

```bash
# Debian/Ubuntu
sudo apt install sshpass

# RHEL/CentOS/Fedora
sudo yum install sshpass
```

### Multi-Server Dashboard

The environment screen is technology-first (`Docker`, `Swarm`, `Kubernetes`, `Podman`, `OpenShift`).

When you configure multiple servers in `config.yaml`, each technology dashboard can aggregate its related servers. You can:

- Select **"All"** to see resources from all servers for that selected technology
- Select **a specific server** to isolate one environment
- **Switch servers** anytime using the server tabs at the top of the dashboard
- Each container shows its **server name** prefix when in multi-server mode

### Keyboard Shortcuts

#### Technology selection screen

| Key | Action |
|---|---|
| `←` / `↑` / `↓` / `→` | Navigate technologies |
| `Enter` | Open technology dashboard |
| `q` | Quit |

#### Container dashboard

| Key | Action |
|---|---|
| `↑` / `↓` | Navigate container list |
| `Enter` | Select container |
| `b` / `Escape` | Back to technology selection |
| `r` | Refresh container list |
| `p` | Pause/resume logs |
| `e` / `x` | Export logs to file |
| `a` | Start container |
| `t` | Stop container |
| `R` | Restart container |
| `Delete` | Remove container |
| `?` | Show help |
| `q` | Quit |

---

## Supported Providers

| Provider | List | Inspect | Stats | Logs | Env Vars | Start/Stop/Restart | Remove |
|---|---|---|---|---|---|---|---|
| **Docker** | ✅ | ✅ | ✅ (stream) | ✅ (follow) | ✅ | ✅ | ✅ |
| **Docker Swarm** | ✅ (services) | ✅ | ⚠️ basic | ✅ (service logs) | ✅ | ✅ (scale/update) | ✅ |
| **Podman** | ✅ | ✅ | ✅ (poll) | ✅ (follow) | ✅ | ✅ | ✅ |
| **Kubernetes** | ✅ | ✅ | ✅ (top) | ✅ (follow) | ✅ | ❌ | ✅ |
| **OpenShift** | ✅ | ✅ | ✅ (top) | ✅ (follow) | ✅ | ❌ | ✅ |

All providers work both locally and remotely via SSH.

---

## Architecture

```
CLI (termainer)
  └── app.py              ← CLI args, .env loading, SSH conn
        ├── config_manager.py ← YAML config parser (multi-server)
        ├── server_manager.py ← Multi-server connection manager
        ├── remote/           ← Remote connection module
        │   └── ssh.py        ←   SSH via subprocess (key + password)
        ├── config.py         ← .env parser and SSH builder
        ├── providers/        ← Multi-provider abstraction layer
        │   ├── base.py       ←   Abstract Protocol
        │   ├── docker.py     ←   Docker CLI (local + remote)
        │   ├── swarm.py      ←   Docker Swarm services (local + remote)
        │   ├── podman.py     ←   Podman CLI (local + remote)
        │   ├── kubernetes.py ←   kubectl (local + remote)
        │   └── openshift.py  ←   oc (extends K8s)
        ├── ui/               ← TUI layer (Textual)
        │   ├── splash.py     ←   Welcome screen
        │   ├── dashboard.py  ←   Main dashboard
        │   ├── widgets.py    ←   Reusable widgets
        │   └── styles.tcss   ←   Stylesheet
        └── utils/
            └── helpers.py    ← Utilities
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| UI Framework | [Textual](https://textual.textualize.io/) |
| Rendering | [Rich](https://rich.readthedocs.io/) |
| Configuration | YAML (via PyYAML) |
| Providers | Docker CLI, Docker Swarm, Podman CLI, kubectl, oc |
| Remote Access | SSH via subprocess (key + sshpass) |
| Async | asyncio |
| Testing | pytest, pytest-asyncio |
| Linting | Ruff |

---

## Documentation

- [Configuration Reference](guide/configuration-reference.md)
- [Configuration Reference (ES)](guide/configuration-reference-es.md)

---

## License

MIT — [Alan Emanuel Stefanov](https://github.com/AlanStefanov)

---

<p align="center">
  ⭐ If you like this project, give it a star on GitHub — it helps others discover it!
  <br>
  <a href="https://github.com/AlanStefanov/termainer">github.com/AlanStefanov/termainer</a>
</p>
