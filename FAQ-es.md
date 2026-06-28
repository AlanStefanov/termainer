# Termainer — FAQ

## General

### ¿Qué es Termainer?
Termainer es una TUI (Terminal User Interface) para observabilidad y operaciones de contenedores directamente desde tu terminal. Soporta Docker, Kubernetes, Docker Swarm, Podman y OpenShift, tanto local como remoto vía SSH.

### ¿Cómo inicio Termainer?
```bash
# Si está instalado globalmente
termainer

# O desde el repo
python -m termainer.app
```

### ¿Qué versión uso actualmente?
0.4.1

### ¿Dónde guarda Termainer su configuración?
Todo se almacena en `~/.config/termainer/`:
- `provider_servers.json` — caché de qué servidores SSH tienen cada provider
- `servers.json` — servidores agregados manualmente desde la UI

---

## Configuración SSH

### Mis servidores SSH no aparecen en la lista
Termainer filtra automáticamente los servidores que apuntan a `localhost` o `127.0.0.1`. Si tu servidor no aparece, verifica que su `HostName` no sea localhost.

### Mi entrada SSH no tiene `Port` explícito y no funciona
Aunque `Port 22` es el default de SSH, algunas directivas poco comunes en el archivo de configuración pueden interferir con el parser. Si tu entrada SSH no aparece o no se conecta correctamente, agrega explícitamente:

```
Host mi-servidor
  HostName 192.168.1.100
  User usuario
  Port 22
```

### ¿Termainer parsea todas las directivas de SSH?
No. Termainer solo lee `Host`, `HostName`, `User`, `Port` e `IdentityFile`. Directivas como `ServerAliveInterval`, `ProxyJump`, `LocalForward`, etc. son ignoradas pero no deberían causar problemas. Si encuentras una directiva que rompe el parser, repórtalo en https://github.com/AlanStefanov/termainer/issues

### Uso `Include` en mi SSH config
El parser de Termainer no sigue directivas `Include`. Todos los servidores deben estar definidos en `~/.ssh/config` directamente, o ser agregados desde la UI de Termainer (menú "Gestionar servidores").

### ¿Puedo usar llaves SSH con contraseña?
Sí. Si tu llave tiene passphrase, Termainer te la pedirá al conectar. También soporta `sshpass` si está instalado.

### ¿Cómo agrego un servidor que no está en mi SSH config?
Desde el selector de servidores:
1. Presiona el botón **"Gestionar servidores"**
2. Presiona **"+ Agregar servidor"**
3. Completa alias, hostname, usuario, puerto y ruta de llave (opcional)
4. Guarda

Los servidores agregados se guardan en `~/.config/termainer/servers.json` y no modifican tu `~/.ssh/config`.

---

## Providers

### Docker
**Requisitos:** `docker` instalado localmente O conexión SSH a un host con Docker.

El comando de health check es `docker info`.

### Kubernetes
**Requisitos:** `kubectl` instalado localmente O conexión SSH a un host con kubectl.

El comando de health check es `kubectl cluster-info`.

Si tienes múltiples contextos en `~/.kube/config`, Termainer usa el contexto activo actual.

### Docker Swarm
**Requisitos:** `docker` instalado localmente O conexión SSH a un host con Docker en modo swarm.

El comando de health check es `docker info`. Termainer detecta automáticamente si el nodo es manager o worker.

### Podman
**Requisitos:** `podman` instalado localmente O conexión SSH a un host con Podman.

El comando de health check es `podman info`. Soporta tanto contenedores rootless como root.

### OpenShift
**Requisitos:** `oc` instalado localmente O conexión SSH a un host con `oc`.

El comando de health check es `oc whoami`. Requiere una sesión activa de login en OpenShift.

---

## Troubleshooting

### "No providers found" en el dashboard Docker
Esto significa que ningún servidor (local ni SSH) tiene Docker disponible. Verifica:
1. Que `docker info` funcione en tu máquina local
2. Que hayas seleccionado al menos un servidor SSH con Docker en el modal de selección
3. Que el servidor SSH remoto tenga `docker` instalado y el usuario tenga permisos

### El modal de selección de servidores no se ve bien
Termaina se adapta al tamaño de tu terminal. Si la terminal es muy angosta (< 80 columnas), algunos elementos pueden reordenarse o contraerse. Intenta agrandar la terminal.

### No puedo navegar con teclado en los modales
Los modales soportan:
- **Tab / Shift+Tab** — navegar entre elementos
- **↑ / ↓** — navegar entre servidores (modal de selección)
- **Espacio** — marcar/desmarcar servidor
- **Enter** — conectar o confirmar
- **Esc** — cerrar modal o volver atrás

Si algo no funciona con teclado, verifica que tu terminal no esté interceptando las teclas (ej. tmux o screen).

### Se borró mi caché de servidores
La caché está en `~/.config/termainer/provider_servers.json`. Si el archivo se corrompe o se borra, simplemente vuelve a seleccionar los servidores desde el modal y la caché se regenerará.

### ¿Cómo reporto un bug?
Reporta issues en: https://github.com/AlanStefanov/termainer/issues  
Incluye:
- Versión de Termainer (`termainer --doctor`)
- Sistema operativo y terminal
- Pasos para reproducir
- Si es posible, un screenshot o log

---

## Contribuir

### ¿Cómo contribuyo?
1. Fork del repo
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de tus cambios
4. Push a la rama
5. Abre un Pull Request

### Estilo de código
- Usamos `ruff` para linting
- Type hints obligatorios
- Tests con `pytest` + `pytest-asyncio`
- Textual 8.x para la UI
