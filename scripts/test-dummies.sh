#!/usr/bin/env bash
# ─────────────────────────────────────────────────
# Termainer — Test dummy environment manager
# ─────────────────────────────────────────────────
# Spins up/pauses/tears down test containers and pods
# for QA testing with Termainer.
#
# Usage:
#   ./scripts/test-dummies.sh up       # Start everything
#   ./scripts/test-dummies.sh status   # Show status
#   ./scripts/test-dummies.sh down     # Tear everything down
#   ./scripts/test-dummies.sh restart  # Restart everything
# ─────────────────────────────────────────────────

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NAMESPACE="termainer-test"
KUBE_CTX="kind-termainer-test"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}▣${NC} $1"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }
err()   { echo -e "${RED}✗${NC} $1"; }

# ── Help ──
usage() {
    echo "Termainer Test Dummies"
    echo ""
    echo "Usage: $0 {up|down|status|restart}"
    echo ""
    echo "Commands:"
    echo "  up        Create all test containers and pods"
    echo "  down      Remove all test containers and pods"
    echo "  status    Show current state"
    echo "  restart   Restart everything (down + up)"
    exit 1
}

# ── Docker dummies ──
docker_up() {
    info "Starting Docker containers..."

    docker run -d --name termainer-nginx    --rm -p 8081:80        nginx:alpine      2>/dev/null && ok "nginx:alpine (port 8081)" || warn "nginx already running"
    docker run -d --name termainer-alpine   --rm                   alpine            2>/dev/null sleep infinity && ok "alpine (sleep)" || warn "alpine already running"
    docker run -d --name termainer-redis    --rm -p 6380:6379      redis:7-alpine    2>/dev/null && ok "redis:7-alpine (port 6380)" || warn "redis already running"
    docker run -d --name termainer-stress   --rm --memory="256m" --cpus="0.5" alpine 2>/dev/null sleep 3600 && ok "alpine (capped 256MB/0.5CPU)" || warn "stress already running"
    docker run -d --name termainer-busybox  --rm                   busybox:latest    2>/dev/null sleep infinity && ok "busybox (sleep)" || warn "busybox already running"
}

docker_down() {
    info "Stopping Docker containers..."
    for c in termainer-nginx termainer-alpine termainer-redis termainer-stress termainer-busybox; do
        docker rm -f "$c" 2>/dev/null && ok "Removed $c" || true
    done
}

docker_status() {
    echo ""
    info "Docker containers:"
    rtk docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | grep termainer- || warn "No Termainer test containers"
}

# ── Podman dummies ──
podman_up() {
    info "Starting Podman containers..."

    podman run -d --name termainer-podman-nginx  --rm -p 8082:80 docker.io/nginx:alpine     2>/dev/null && ok "nginx:alpine (port 8082)" || warn "nginx already running"
    podman run -d --name termainer-podman-alpine --rm    docker.io/alpine:latest            2>/dev/null sleep infinity && ok "alpine (sleep)" || warn "alpine already running"
}

podman_down() {
    info "Stopping Podman containers..."
    for c in termainer-podman-nginx termainer-podman-alpine; do
        podman rm -f "$c" 2>/dev/null && ok "Removed $c" || true
    done
}

podman_status() {
    echo ""
    info "Podman containers:"
    rtk podman ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | grep termainer-podman || warn "No Termainer test containers"
}

# ── Kubernetes dummies (Kind) ──
k8s_up() {
    info "Starting Kubernetes pods in namespace '${NAMESPACE}'..."

    if ! kind get clusters 2>/dev/null | grep -q termainer-test; then
        info "Creating Kind cluster 'termainer-test'..."
        kind create cluster --name termainer-test
        kubectl taint nodes termainer-test-control-plane node-role.kubernetes.io/control-plane:NoSchedule- 2>/dev/null || true
    fi

    kubectl --context "$KUBE_CTX" create namespace "$NAMESPACE" 2>/dev/null || true

    kubectl --context "$KUBE_CTX" run nginx-pod   --image=nginx:alpine   --namespace="$NAMESPACE" 2>/dev/null && ok "pod/nginx-pod"   || warn "nginx-pod already exists"
    kubectl --context "$KUBE_CTX" run redis-pod   --image=redis:7-alpine --namespace="$NAMESPACE" 2>/dev/null && ok "pod/redis-pod"   || warn "redis-pod already exists"
    kubectl --context "$KUBE_CTX" run busybox-pod --image=busybox:latest --namespace="$NAMESPACE" -- sleep infinity 2>/dev/null && ok "pod/busybox-pod" || warn "busybox-pod already exists"
    kubectl --context "$KUBE_CTX" run error-pod   --image=nginx:alpine   --namespace="$NAMESPACE" -- /bin/false 2>/dev/null && ok "pod/error-pod"   || warn "error-pod already exists"

    kubectl --context "$KUBE_CTX" create deployment web-deploy --image=nginx:alpine --replicas=2 --namespace="$NAMESPACE" 2>/dev/null && ok "deploy/web-deploy" || warn "web-deploy already exists"
    kubectl --context "$KUBE_CTX" create deployment api-deploy --image=redis:7-alpine --replicas=1 --namespace="$NAMESPACE" 2>/dev/null && ok "deploy/api-deploy" || warn "api-deploy already exists"

    echo ""
    info "Waiting for pods to be ready..."
    kubectl --context "$KUBE_CTX" wait pods --all -n "$NAMESPACE" --for=condition=Ready --timeout=60s 2>/dev/null && ok "All pods ready" || warn "Some pods not ready (expected for error-pod)"
}

k8s_down() {
    info "Removing Kubernetes namespace '${NAMESPACE}'..."
    kubectl --context "$KUBE_CTX" delete namespace "$NAMESPACE" --ignore-not-found --wait=false >/dev/null 2>&1 && ok "Deleted namespace $NAMESPACE" || true
    info "To delete the Kind cluster: kind delete cluster --name termainer-test"
}

k8s_status() {
    echo ""
    info "Kubernetes pods (namespace ${NAMESPACE}):"
    if kubectl --context "$KUBE_CTX" get pods -n "$NAMESPACE" 2>/dev/null | grep -q .; then
        kubectl --context "$KUBE_CTX" get pods -n "$NAMESPACE" -o wide
    else
        warn "No pods in namespace ${NAMESPACE} (or Kind cluster not running)"
    fi
}

# ── Main ──
case "${1:-help}" in
    up)
        docker_up
        podman_up
        k8s_up
        echo ""
        ok "Test environment ready! Run 'termainer' to inspect."
        echo ""
        info "  Docker:   termainer --provider docker"
        info "  Podman:   termainer --provider podman"
        info "  K8s:      termainer --provider kubernetes"
        info "  OpenShift: termainer --provider openshift  (if oc is configured)"
        echo ""
        info "Quick test:"
        info "  source venv/bin/activate && termainer"
        ;;
    down)
        docker_down
        podman_down
        k8s_down
        ok "Test environment torn down"
        ;;
    status)
        docker_status
        podman_status
        k8s_status
        ;;
    restart)
        "$0" down
        sleep 2
        "$0" up
        ;;
    *)
        usage
        ;;
esac
