# Termainer - Diseño Técnico

## Resumen del Proyecto
Herramienta de línea de comandos (TUI) diseñada para la inspección y gestión interactiva de workloads en Docker, Docker Swarm, Podman, Kubernetes y OpenShift. El objetivo es ofrecer una experiencia de usuario similar a Portainer pero nativa en la terminal, optimizada para desarrolladores y arquitectos que prefieren el flujo de trabajo CLI.

## Stack Tecnológico
* **Lenguaje:** Python 3.10+
* **UI Framework:** [Textual](https://textual.textualize.io/) (para la interfaz basada en eventos y widgets)
* **Estilizado:** [Rich](https://rich.readthedocs.io/) (para componentes visuales y formato)
* **Interacción con Sistema:** `subprocess` / `asyncio` (para llamadas a comandos de contenedores)

## Arquitectura Multi-Provider

Termainer utiliza una capa de abstracción para soportar múltiples runtimes de contenedores:

```
src/termainer/
├── app.py                  # Punto de entrada de la app Textual
├── ui/
│   ├── dashboard.py        # Layout principal (Grid)
│   └── widgets.py          # Widgets reutilizables
├── providers/
│   ├── base.py             # Interfaz abstracta (Protocol)
│   ├── docker.py           # Driver Docker CLI
│   ├── swarm.py            # Driver Docker Swarm (servicios)
│   ├── podman.py           # Driver Podman CLI
│   ├── kubernetes.py       # Driver Kubernetes (kubectl / client-python)
│   └── openshift.py        # Driver OpenShift (oc, extiende K8s)
└── utils/
    └── helpers.py          # Funciones auxiliares
```

Cada provider implementa la interfaz definida en `base.py`, lo que permite que la UI consuma cualquier runtime sin acoplamiento.

## Arquitectura de la Interfaz (Grid Layout)

La aplicación se estructurará en un panel principal utilizando un `Grid` de Textual:

1.  **Sidebar / Nav:** Lista de contenedores/pods activos.
2.  **Panel de Detalles:**
    * Variables de entorno (`docker inspect` / `kubectl describe`).
    * Información de red y volúmenes.
3.  **Panel de Monitoreo:**
    * Uso de CPU/RAM en tiempo real (stream de `docker stats` / `kubectl top`).
4.  **Panel de Logs:**
    * Visualizador de logs con `tail` dinámico.
    * Opción de pausa para revisión histórica.

## Funcionalidades Clave (Features)
* **Stats:** Consumo de recursos en tiempo real sin necesidad de comandos independientes.
* **Log Streaming:** Visualización en vivo de los logs con scroll suave.
* **Exportación de Logs (Bug Reporting):**
    * Funcionalidad para guardar logs actuales a un archivo `.txt`.
    * Ruta de guardado configurable.
    * Incluye timestamp y metadatos del contenedor para facilitar el debugging.
* **Multi-Provider:** Selección dinámica de tecnología (Docker, Swarm, Podman, K8s, OpenShift).
* **Conectividad:** Soporte básico para conexión remota a través de socket Docker expuesto o kubeconfig.

## Matriz de Features por Provider

| Feature               | Docker | Swarm | Podman | Kubernetes | OpenShift |
|-----------------------|--------|-------|--------|------------|-----------|
| List resources        | ✅     | ✅    | ✅     | ✅         | ✅        |
| Inspect/describe      | ✅     | ✅    | ✅     | ✅         | ✅        |
| Stats (CPU/RAM)       | ✅     | ⚠️    | ✅     | ✅ (top)   | ✅ (top)  |
| Log streaming         | ✅     | ✅    | ✅     | ✅         | ✅        |
| Env vars              | ✅     | ✅    | ✅     | ✅         | ✅        |
| Export logs           | ✅     | ✅    | ✅     | ✅         | ✅        |

## Flujo de Trabajo (User Flow)
1.  **Inicio:** La TUI detecta tecnologías locales y conexiones remotas configuradas.
2.  **Selección de tecnología:** El usuario elige Docker, Swarm, Podman, Kubernetes u OpenShift.
3.  **Filtro de servidor:** Dentro del dashboard, elige "Todos" o un servidor específico de esa tecnología.
4.  **Inspección:** Al seleccionar un recurso, se cargan automáticamente detalles y stream de stats/logs.
5.  **Reporte:** El usuario exporta logs para debugging.
