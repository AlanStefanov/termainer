# Termainer — FAQ

## General

### What is Termainer?
Termainer is a TUI (Terminal User Interface) for container observability and operations directly from your terminal. It supports Docker, Kubernetes, Docker Swarm, Podman, and OpenShift, both locally and remotely via SSH.

### How do I start Termainer?
```bash
# If installed globally
termainer

# Or from the repo
python -m termainer.app
```

### What version am I currently using?
0.4.1

### Where does Termainer store its configuration?
Everything lives in `~/.config/termainer/`:
- `provider_servers.json` — cache of which SSH servers have each provider
- `servers.json` — user-added servers from the UI

---

## SSH Configuration

### My SSH servers don't show up in the list
Termainer automatically filters out servers pointing to `localhost` or `127.0.0.1`. If your server doesn't appear, check that its `HostName` is not localhost.

### My SSH entry doesn't have an explicit `Port` and doesn't work
While `Port 22` is SSH's default, some uncommon directives in your config file may interfere with the parser. If your SSH entry doesn't show up or fails to connect, add `Port` explicitly:

```
Host my-server
  HostName 192.168.1.100
  User myuser
  Port 22
```

### Does Termainer parse every SSH directive?
No. Termainer only reads `Host`, `HostName`, `User`, `Port`, and `IdentityFile`. Directives like `ServerAliveInterval`, `ProxyJump`, `LocalForward`, etc. are ignored but should not cause issues. If you find a directive that breaks the parser, report it at https://github.com/AlanStefanov/termainer/issues

### I use `Include` in my SSH config
Termainer's parser does not follow `Include` directives. All servers must be defined directly in `~/.ssh/config`, or added from the Termainer UI (Manage Servers menu).

### Can I use password-protected SSH keys?
Yes. If your key has a passphrase, Termainer will prompt you for it on connect. It also supports `sshpass` if installed.

### How do I add a server not in my SSH config?
From the server selector:
1. Click **"Manage Servers"**
2. Click **"+ Add Server"**
3. Fill in alias, hostname, user, port, and key path (optional)
4. Save

Added servers are stored in `~/.config/termainer/servers.json` and do not modify your `~/.ssh/config`.

---

## Providers

### Docker
**Requirements:** `docker` installed locally OR SSH connection to a host with Docker.

The health check command is `docker info`.

### Kubernetes
**Requirements:** `kubectl` installed locally OR SSH connection to a host with kubectl.

The health check command is `kubectl cluster-info`.

If you have multiple contexts in `~/.kube/config`, Termainer uses the currently active context.

### Docker Swarm
**Requirements:** `docker` installed locally OR SSH connection to a host with Docker in swarm mode.

The health check command is `docker info`. Termainer automatically detects if the node is a manager or worker.

### Podman
**Requirements:** `podman` installed locally OR SSH connection to a host with Podman.

The health check command is `podman info`. Supports both rootless and root containers.

### OpenShift
**Requirements:** `oc` installed locally OR SSH connection to a host with `oc`.

The health check command is `oc whoami`. Requires an active OpenShift login session.

---

## Troubleshooting

### "No providers found" on the Docker dashboard
This means no server (local or SSH) has Docker available. Verify:
1. That `docker info` works on your local machine
2. That you selected at least one SSH server with Docker in the selection modal
3. That the remote SSH server has `docker` installed and your user has permissions

### The server selection modal doesn't look right
Termainer adapts to your terminal size. If your terminal is very narrow (< 80 columns), some elements may reorder or collapse. Try widening the terminal.

### I can't navigate with the keyboard in modals
Modals support:
- **Tab / Shift+Tab** — navigate between elements
- **↑ / ↓** — navigate between servers (selection modal)
- **Space** — toggle server on/off
- **Enter** — connect or confirm
- **Esc** — close modal or go back

If something doesn't work with the keyboard, check that your terminal (e.g., tmux or screen) isn't intercepting the keys.

### My server cache was cleared
The cache is stored at `~/.config/termainer/provider_servers.json`. If this file gets corrupted or deleted, simply re-select servers from the modal and the cache will be regenerated.

### How do I report a bug?
Report issues at: https://github.com/AlanStefanov/termainer/issues  
Please include:
- Termainer version (`termainer --doctor`)
- Operating system and terminal
- Steps to reproduce
- If possible, a screenshot or log

---

## Contributing

### How do I contribute?
1. Fork the repo
2. Create a branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

### Code style
- We use `ruff` for linting
- Type hints are mandatory
- Tests with `pytest` + `pytest-asyncio`
- Textual 8.x for the UI
