# Branding y Visión del Producto

## Nombre del Proyecto

### Termainer

**Termainer** nace de la combinación de las palabras **Terminal** y **Container Management**, representando una nueva generación de herramientas de observabilidad y operación diseñadas para desarrolladores que prefieren trabajar directamente desde la línea de comandos.

El nombre es corto, fácil de recordar y transmite claramente su propósito: proporcionar toda la información crítica de los contenedores desde una única interfaz en la terminal.

---

## Propuesta de Valor

> Todo lo que necesitas saber de todos tus contenedores, en una sola terminal.

Termainer centraliza la información más importante para la operación y el diagnóstico de aplicaciones contenerizadas:

* Estado de contenedores.
* Estado de servicios (Swarm).
* Uso de CPU y memoria en tiempo real.
* Variables de entorno.
* Redes y volúmenes.
* Streaming de logs.
* Exportación de información para debugging.
* Monitoreo operativo sin abandonar la terminal.

La filosofía del proyecto es reducir el cambio de contexto y permitir que desarrolladores, arquitectos y equipos DevOps puedan inspeccionar, monitorear y diagnosticar servicios desde un único punto de acceso.

---

## Experiencia de Uso

Termainer está diseñado para sentirse como una herramienta nativa del ecosistema de terminales modernas:

```bash
pip install termainer
```

```bash
termainer
```

o mediante contenedores:

```bash
docker run -it termainer:latest
```

---

## Slogans

### Opción 1 (Principal)

> Todo lo que necesitas saber de todos tus contenedores, en una sola terminal.

### Opción 2

> Observabilidad de contenedores sin salir de la terminal.

### Opción 3

> Monitorea, inspecciona y depura tus contenedores desde un único lugar.

### Opción 4

> Tu centro de operaciones para contenedores.

### Opción 5

> Visibilidad completa de tus contenedores, directamente desde la terminal.

---

## Escalabilidad del Producto

Aunque la primera versión estará enfocada en Docker, la arquitectura y el nombre del proyecto permiten una evolución natural hacia otros entornos:

* Docker Swarm
* Docker Compose
* Podman
* Kubernetes
* OpenShift
* Entornos remotos
* Clústeres híbridos

En la versión actual, Termainer prioriza una navegación por tecnología (Docker, Swarm, Podman, Kubernetes, OpenShift) y permite luego seleccionar servidor local/remoto dentro de cada dashboard.

El objetivo a largo plazo es convertir a Termainer en una plataforma de observabilidad y operación para ecosistemas de contenedores, manteniendo siempre la simplicidad y velocidad de una aplicación nativa de terminal.

---

## Repositorio

```text
github.com/alanstefanov/termainer
```

### Subtítulo del Proyecto

> Container observability and operations directly from your terminal.

o

> The control center for your containers, built for the terminal.
