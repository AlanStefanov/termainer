# Guía de Configuración

Termainer puede configurarse para monitorear contenedores en múltiples servidores. Este documento cubre todas las opciones de configuración.

---

## Archivo de Configuración

Creá `~/.config/termainer/config.yaml` (o `$XDG_CONFIG_HOME/termainer/config.yaml`).

La app también busca `./config.yaml` (directorio actual) como alternativa.

### Opciones Globales

| Opción | Tipo | Default | Descripción |
|--------|------|---------|-------------|
| `lang` | string | `"en"` | Idioma de la interfaz. Soportados: `en`, `es` |

### Entradas de Servidor

Cada servidor en la lista `servers` tiene estos campos:

| Campo | Requerido | Tipo | Default | Descripción |
|-------|-----------|------|---------|-------------|
| `label` | **sí** | string | — | Nombre visible en la interfaz |
| `provider` | **sí** | string | — | Runtime de contenedores: `docker`, `swarm`, `podman`, `kubernetes`, `k8s`, `openshift` |
| `host` | no | string | — | Host SSH (IP o hostname). Omitir para Docker/Podman local |
| `user` | no | string | `"root"` | Usuario SSH |
| `key` | no | string | — | Ruta a clave privada SSH (archivo `.pem`). Usá `~` para home |
| `password` | no | string | — | Contraseña SSH (requiere `sshpass` instalado). No recomendado |
| `port` | no | integer | `22` | Puerto SSH |

### Ejemplo: Config completa

```yaml
lang: es

servers:
  # Servidor local (sin host)
  - label: "Docker Local"
    provider: docker

  # EC2 remoto con clave
  - label: "Servidor Producción"
    host: ec2-54-123-45-67.us-east-1.compute.amazonaws.com
    user: ubuntu
    key: ~/.ssh/production.pem
    provider: docker

  # Cluster K8s remoto
  - label: "K8s Staging"
    host: k8s-staging.example.com
    user: admin
    key: ~/.ssh/staging-key
    provider: kubernetes

  # Podman en un VPS
  - label: "Dev Podman"
    host: 192.168.1.50
    user: dev
    key: ~/.ssh/dev.pem
    provider: podman
    port: 2222
```

---

## Un Solo Servidor vía .env

Si solo necesitás monitorear un servidor remoto, podés usar un archivo `.env`:

```bash
cp .env.example .env
# Editar .env con los datos del servidor
termainer
```

### Variables de Entorno

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `TERMAINER_REMOTE_HOST` | **sí** | — | Host remoto (IP o hostname) |
| `TERMAINER_REMOTE_USER` | no | `root` | Usuario SSH |
| `TERMAINER_REMOTE_KEY_PATH` | no* | — | Ruta a clave privada SSH |
| `TERMAINER_REMOTE_PASSWORD` | no* | — | Contraseña SSH (requiere `sshpass`) |
| `TERMAINER_REMOTE_PORT` | no | `22` | Puerto SSH |
| `TERMAINER_REMOTE_PROVIDER` | no | auto | Provider: `docker`, `swarm`, `kubernetes`, `podman`, `openshift` |
| `TERMAINER_LANG` | no | `en` | Idioma: `en` o `es` |

\* Debe configurarse `TERMAINER_REMOTE_KEY_PATH` o `TERMAINER_REMOTE_PASSWORD` (o ninguno si usás SSH agent).

---

## Flags de Línea de Comandos

Todos los flags CLI sobreescriben valores de `.env` y `config.yaml`.

| Flag | Descripción |
|------|-------------|
| `--provider` | Provider: `auto` (default), `docker`, `swarm`, `podman`, `kubernetes`, `k8s`, `openshift` |
| `--host` | Host SSH (sobreescribe env/config) |
| `--ssh-user` | Usuario SSH |
| `--ssh-key` | Ruta a clave SSH |
| `--ssh-password` | Contraseña SSH |
| `--ssh-port` | Puerto SSH |
| `--config` | Ruta a config.yaml (default: detección automática XDG) |
| `--env` | Ruta a .env (default: `.env`) |
| `--version` | Muestra versión y sale |

---

## Precedencia

Los valores se resuelven en este orden (el último gana):

1. Defaults (hardcodeados en la app)
2. Valores de `config.yaml`
3. Valores de `.env`
4. Flags CLI (`--host`, `--ssh-user`, etc.)

---

## Autenticación SSH

### Por clave (recomendado)

```bash
# Servidores EC2 / cloud
termainer --host ec2-54-123-45-67.compute.amazonaws.com \
          --ssh-user ubuntu \
          --ssh-key ~/.ssh/production.pem
```

### Por contraseña

Requiere `sshpass`:

```bash
sudo apt install sshpass   # Debian/Ubuntu
sudo yum install sshpass   # RHEL/CentOS
```

```bash
termainer --host 192.168.1.100 \
          --ssh-user root \
          --ssh-password 'micontraseña'
```

### SSH Agent

Si no se provee clave ni contraseña, Termainer usa tu SSH agent (comportamiento SSH por defecto).

---

## Selección de Idioma

Termainer soporta **inglés** y **español** para la interfaz.

Configuralo con:

1. **Archivo de configuración**: `lang: es` en `config.yaml`
2. **Variable de entorno**: `TERMAINER_LANG=es`
3. **En el futuro**: detección automática vía `locale.getdefaultlocale()`

---

## Tips Multi-Servidor

- **Nombres**: Usá etiquetas descriptivas (ej. "Prod Web", "K8s Staging", "Dev Docker") para identificar servidores rápido.
- **Navegación por Tecnología**: La pantalla de entorno es por tecnología (Docker, Swarm, Podman, Kubernetes, OpenShift).
- **Vista "Todos"**: Dentro de cada dashboard tecnológico podés seleccionar "Todos" para agregar recursos de todos los servidores de esa tecnología.
- **Pestañas**: Cambiá entre servidores directamente desde el dashboard usando las pestañas en la parte superior.
- **Compatibilidad**: Si no creás un archivo de configuración, Termainer usa `.env` / flags CLI (modo un servidor) o detecta automáticamente un provider local.
