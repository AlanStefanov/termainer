# Roadmap de Desarrollo: Termainer

Este documento detalla la ruta crítica y los pasos técnicos para implementar Termainer desde cero utilizando Python, Textual y Rich.

## Fase 1: Configuración del Entorno y Estructura
1.  **Inicialización del Proyecto:**
    * Crear entorno virtual: `python -m venv venv`.
    * Instalar dependencias clave: `pip install textual rich`.
    * Estructura de carpetas:
        ```text
        termainer/
        ├── src/
        │   └── termainer/
        │       ├── __init__.py
        │       ├── app.py
        │       ├── ui/
        │       │   ├── __init__.py
        │       │   ├── dashboard.py
        │       │   └── widgets.py
        │       ├── providers/
        │       │   ├── __init__.py
        │       │   ├── base.py
        │       │   ├── docker.py
        │       │   ├── swarm.py
        │       │   ├── podman.py
        │       │   ├── kubernetes.py
        │       │   └── openshift.py
        │       └── utils/
        │           ├── __init__.py
        │           └── helpers.py
        ├── tests/
        │   ├── __init__.py
        │   ├── test_providers.py
        ├── docs/
        │   ├── branding.md
        │   ├── design.md
        │   └── roadmap.md
        └── requirements.txt
        ```

## Fase 2: Módulo de Interacción con Contenedores (Backend)

### 2a. Interfaz Base (Provider Protocol)
1.  **Crear interfaz abstracta en `base.py`:**
    * `list_containers()` → Lista de contenedores/pods.
    * `inspect(container_id)` → Detalles completos.
    * `stats(container_id)` → Stream de CPU/RAM.
    * `logs(container_id, tail=100, follow=False)` → Logs.
    * `get_env(container_id)` → Variables de entorno.

### 2b. Provider Docker
1.  **Envoltura de comandos usando `subprocess`:**
    * `docker ps -a --format json`
    * `docker inspect <id>`
    * `docker stats --no-stream --format json`
    * `docker logs --tail 100 <id>`

### 2c. Provider Podman
1.  **Análogo a Docker pero con CLI `podman`:**
    * `podman ps -a --format json`
    * `podman inspect <id>`
    * `podman stats --no-stream --format json`
    * `podman logs --tail 100 <id>`

### 2d. Provider Swarm
1.  **Servicios Docker Swarm sobre CLI `docker`:**
    * `docker info --format '{{.Swarm.LocalNodeState}}'`
    * `docker service ls --format '{{json .}}'`
    * `docker service inspect <id>`
    * `docker service logs --tail 100 <id>`

### 2e. Provider Kubernetes
1.  **Usando `kubectl` o `kubernetes` client-python:**
    * `kubectl get pods --all-namespaces -o json`
    * `kubectl describe pod <name> -n <ns>`
    * `kubectl top pod <name> -n <ns>`
    * `kubectl logs --tail=100 -f <name> -n <ns>`

### 2f. Provider OpenShift
1.  **Extiende el provider K8s usando `oc`:**
    * `oc get pods --all-namespaces -o json`
    * `oc describe pod <name> -n <ns>`
    * `oc adm top pod <name> -n <ns>`
    * `oc logs --tail=100 -f <name> -n <ns>`

### 2g. Manejo de Errores
* Validación del socket Docker / Podman / kubeconfig al inicio.
* Mensajes de error claros si el runtime no está disponible.

## Fase 3: Construcción de la UI (Frontend con Textual)
1.  **Layout Principal:**
    * Implementar el `Grid` principal en `dashboard.py`.
    * Definir los paneles: `Contenedores`, `Detalles`, `Stats`, `Logs`.
2.  **Desarrollo de Widgets:**
    * **Contenedores:** Widget de lista interactiva (selección).
    * **Logs:** Área de texto con scroll (usar `RichLog` de Textual).
    * **Stats:** Widget que se refresque periódicamente (intervalo de 1-2 segundos).
3.  **Selector de Tecnología:**
    * Pantalla inicial por tecnología (Docker, Swarm, Podman, K8s, OpenShift).
    * Selector de servidor dentro del dashboard de cada tecnología.

## Fase 4: Implementación de Funcionalidades (Features)
1.  **Sincronización:**
    * Conectar la selección de un contenedor en la lista con la actualización de los paneles de `inspect` y `logs`.
2.  **Streaming de Logs:**
    * Crear una tarea asíncrona en Textual para mantener el log streaming activo sin bloquear la UI.
3.  **Exportación (Bug Report):**
    * Implementar función que tome el buffer actual de logs y lo escriba en `reporte_bug_<timestamp>.txt`.
    * Añadir metadatos (nombre, imagen, hora) al principio del archivo.
4.  **Multi-Provider Runtime:**
    * Detección automática del runtime disponible.
    * Conmutación en caliente entre tecnologías y servidores.

## Fase 5: Testing y Refinamiento
1.  **Testing Local:** Probar con distintos estados de contenedores (corriendo, pausados, error).
2.  **Testing Multi-Provider:** Verificar funcionamiento en Docker, Swarm, Podman, kind/minikube, OpenShift Local.
3.  **Optimización:** Ajustar tiempos de refresco para que la UI no se sienta pesada.
4.  **Packaging:** Configurar `pyproject.toml` con entry point `termainer`.

## Fase 6: Documentación y Lanzamiento
1.  **README.md:** Escribir las instrucciones de instalación y uso.
2.  **Publicación:** Subir a PyPI y a `github.com/alanstefanov/termainer`.
