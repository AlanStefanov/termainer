<div align="center">

# Termainer

**Observabilidad y operación de contenedores directamente desde tu terminal.**

[![GitHub](https://img.shields.io/badge/GitHub-AlanStefanov/termainer-181717?style=flat-square&logo=github)](https://github.com/AlanStefanov/termainer)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![PyPI](https://img.shields.io/badge/PyPI-0.1.0-blue?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/termainer/)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-alanstefanov%2Ftermainer-2496ED?style=flat-square&logo=docker)](https://hub.docker.com/r/alanstefanov/termainer)
[![Homebrew](https://img.shields.io/badge/Homebrew-coming%20soon-FBB040?style=flat-square&logo=homebrew)](https://github.com/AlanStefanov/homebrew-termainer)
[![Textual](https://img.shields.io/badge/Built%20with-Textual-6C5CE7?style=flat-square)](https://textual.textualize.io/)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Alan%20Stefanov-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/alanstefanov/)

<br>

> Todo lo que necesitas saber de todos tus contenedores, en una sola terminal.

<br>

![UI Demo](docs/UI_post-home.png)

</div>

---

## Características

| | |
|---|---|
| **📊 Estadísticas en Vivo** | CPU, memoria y I/O de red en tiempo real con gráficos sparkline |
| **📜 Log Streaming** | Logs en vivo con pausa/reanudación, scroll y resaltado de sintaxis |
| **🔍 Inspección Completa** | Variables de entorno, redes, volúmenes, puertos y configuración |
| **🔌 Multi-Provider** | Soporta **Docker**, **Docker Swarm**, **Podman**, **Kubernetes** y **OpenShift** |
| **📤 Exportación de Reportes** | Guarda logs con metadatos para debugging y bug reporting |
| **🌐 Conexión Remota por SSH** | Conectate a servidores remotos (EC2, VPS, etc.) con Docker o K8s |
| **🖥️ Multi-Servidor** | Monitorea múltiples servidores remotos y locales simultáneamente |
| **⚡ TUI Moderna** | Construida con Textual y Rich — rápida, responsiva y nativa de la terminal |
| **🔄 Acciones sobre Contenedores** | Iniciar, detener, reiniciar y eliminar contenedores (Docker/Podman) |

---

## Instalación

### Desde PyPI (recomendado)

```bash
pip install termainer
```

### Desde Docker (ghcr.io — recomendado)

```bash
docker run -it -v /var/run/docker.sock:/var/run/docker.sock \
  ghcr.io/alanstefanov/termainer:latest
```

### Desde Docker Hub (opcional)

```bash
docker run -it -v /var/run/docker.sock:/var/run/docker.sock \
  alanstefanov/termainer:latest
```

### Desde fuente con install.sh

```bash
git clone https://github.com/AlanStefanov/termainer.git
cd termainer
chmod +x install.sh
./install.sh
```

Luego asegurate de tener `~/.local/bin` en tu `PATH`:

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

### Homebrew (próximamente)

```bash
# Una vez disponible en el tap oficial:
brew install termainer
```

Mientras tanto podés instalarlo manualmente desde el [tap comunitario](https://github.com/AlanStefanov/homebrew-termainer).

---

## Actualización

Dependiendo de cómo instalaste Termainer:

| Método | Comando |
|--------|---------|
| **pip** | `pip install --upgrade termainer` |
| **Docker (ghcr.io)** | `docker pull ghcr.io/alanstefanov/termainer:latest` |
| **Docker Hub** | `docker pull alanstefanov/termainer:latest` |
| **install.sh** | `cd termainer && git pull && ./install.sh` |

---

## Configuración

Termainer usa un **archivo de configuración YAML** para administrar múltiples servidores. Creá `~/.config/termainer/config.yaml`:

```yaml
lang: es

servers:
  - label: "Docker Local"
    provider: docker
    # Sin host = Docker local

  - label: "Servidor Producción"
    host: ec2-54-123-45-67.us-east-1.compute.amazonaws.com
    user: ubuntu
    key: ~/.ssh/production.pem
    provider: docker

  - label: "K8s Staging"
    host: k8s-staging.example.com
    user: admin
    key: ~/.ssh/staging-key
    provider: kubernetes
```

Ver la [Guía de Configuración](docs/configuration-reference-es.md) completa (en español).

### Un solo servidor rápido (.env)

Para un solo servidor remoto podés usar `.env` o flags de línea de comandos:

```bash
termainer --host ec2-54-123-45-67.us-east-1.compute.amazonaws.com \
          --ssh-user ubuntu \
          --ssh-key ~/.ssh/production.pem \
          --provider docker
```

---

## Uso

### Local

```bash
# Detección automática del provider
termainer

# Provider específico
termainer --provider docker
termainer --provider swarm
termainer --provider podman
termainer --provider kubernetes
termainer --provider openshift
```

### Conexión Remota (SSH)

Conectate a servidores remotos con Docker o Kubernetes corriendo:

```bash
# Usando flags de línea de comandos
termainer --host ec2-54-123-45-67.us-east-1.compute.amazonaws.com \
          --ssh-user ubuntu \
          --ssh-key ~/.ssh/production.pem \
          --provider docker

# Usando .env (recomendado para uso frecuente)
cp .env.example .env
# Editar .env con tus datos
termainer
```

#### Formas de autenticación SSH

| Método | Cómo usarlo |
|---|---|
| **Key `.pem`** | `--ssh-key ~/.ssh/key.pem` o `TERMAINER_REMOTE_KEY_PATH` en `.env` |
| **Password** | `--ssh-password 'mypass'` o `TERMAINER_REMOTE_PASSWORD` en `.env` (requiere `sshpass`) |

Para autenticación por password, instalá `sshpass`:

```bash
# Debian/Ubuntu
sudo apt install sshpass

# RHEL/CentOS/Fedora
sudo yum install sshpass
```

### Dashboard Multi-Servidor

La pantalla de entorno ahora es por tecnología (`Docker`, `Swarm`, `Kubernetes`, `Podman`, `OpenShift`).

Cuando configurás múltiples servidores en `config.yaml`, cada dashboard tecnológico puede agrupar sus servidores. Podés:

- Seleccionar **"Todos"** para ver recursos de todos los servidores de esa tecnología
- Seleccionar **un servidor** para aislar un entorno
- **Cambiar de servidor** en cualquier momento usando las pestañas en la parte superior del dashboard
- Cada contenedor muestra el **nombre del servidor** como prefijo en modo multi-servidor

### Atajos de Teclado

#### Pantalla de selección de tecnología

| Tecla | Acción |
|---|---|
| `←` / `↑` / `↓` / `→` | Navegar entre tecnologías |
| `Enter` | Abrir dashboard de tecnología |
| `q` | Salir |

#### Dashboard de contenedores

| Tecla | Acción |
|---|---|
| `↑` / `↓` | Navegar lista de contenedores |
| `Enter` | Seleccionar contenedor |
| `b` / `Escape` | Volver a selección de tecnología |
| `r` | Refrescar lista |
| `p` | Pausar/reanudar logs |
| `e` / `x` | Exportar logs a archivo |
| `a` | Iniciar contenedor |
| `t` | Detener contenedor |
| `R` | Reiniciar contenedor |
| `Delete` | Eliminar contenedor |
| `?` | Mostrar ayuda |
| `q` | Salir |

---

## Proveedores Soportados

| Proveedor | Listar | Inspeccionar | Stats | Logs | Env Vars | Start/Stop/Restart | Eliminar |
|---|---|---|---|---|---|---|---|
| **Docker** | ✅ | ✅ | ✅ (stream) | ✅ (follow) | ✅ | ✅ | ✅ |
| **Docker Swarm** | ✅ (servicios) | ✅ | ⚠️ básico | ✅ (service logs) | ✅ | ✅ (scale/update) | ✅ |
| **Podman** | ✅ | ✅ | ✅ (poll) | ✅ (follow) | ✅ | ✅ | ✅ |
| **Kubernetes** | ✅ | ✅ | ✅ (top) | ✅ (follow) | ✅ | ❌ | ✅ |
| **OpenShift** | ✅ | ✅ | ✅ (top) | ✅ (follow) | ✅ | ❌ | ✅ |

Todos los proveedores funcionan tanto local como remotamente vía SSH.

---

## Arquitectura

```
CLI (termainer)
  └── app.py              ← CLI args, .env, config.yaml
        ├── config_manager.py ← Parser YAML (multi-servidor)
        ├── server_manager.py ← Gestor de conexiones multi-servidor
        ├── remote/           ← Módulo de conexión remota
        │   └── ssh.py        ←   SSH vía subprocess (key + password)
        ├── config.py         ← Carga de .env y construcción SSH
        ├── providers/        ← Capa de abstracción multi-provider
        │   ├── base.py       ←   Protocolo abstracto
        │   ├── docker.py     ←   Docker CLI (local + remoto)
        │   ├── swarm.py      ←   Docker Swarm services (local + remoto)
        │   ├── podman.py     ←   Podman CLI (local + remoto)
        │   ├── kubernetes.py ←   kubectl (local + remoto)
        │   └── openshift.py  ←   oc (extiende K8s)
        ├── ui/               ← Interfaz TUI (Textual)
        │   ├── splash.py     ←   Pantalla de bienvenida
        │   ├── dashboard.py  ←   Dashboard principal
        │   ├── widgets.py    ←   Widgets reutilizables
        │   └── styles.tcss   ←   Estilos
        └── utils/
            └── helpers.py    ← Utilidades
```

---

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.10+ |
| UI Framework | [Textual](https://textual.textualize.io/) |
| Renderizado | [Rich](https://rich.readthedocs.io/) |
| Configuración | YAML (via PyYAML) |
| Providers | Docker CLI, Docker Swarm, Podman CLI, kubectl, oc |
| Conexión Remota | SSH vía subprocess (key + sshpass) |
| Async | asyncio |
| Testing | pytest, pytest-asyncio |
| Linting | Ruff |

---

## Documentación

- [Guía de Configuración](docs/configuration-reference-es.md)
- [Configuration Reference](docs/configuration-reference.md) (English)
- [Branding y Visión](docs/branding.md)
- [Diseño Técnico](docs/design.md)
- [Roadmap](docs/roadmap.md)

---

## Licencia

MIT — [Alan Emanuel Stefanov](https://github.com/AlanStefanov)

---

<p align="center">
  ⭐ Si te gusta el proyecto, dale una estrella en GitHub — ¡ayuda a que más personas lo descubran!
  <br>
  <a href="https://github.com/AlanStefanov/termainer">github.com/AlanStefanov/termainer</a>
</p>
