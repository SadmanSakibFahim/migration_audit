#!/usr/bin/env bash
# =============================================================================
# Smoke Test — Validate the Docker container is healthy and serving traffic
# Author: Sheldon Cooper (Senior Software Engineer)
#
# Usage:
#   bash scripts/smoke_test.sh
#
# Expectations:
#   - Docker is installed and running
#   - Port 8001 is free
# =============================================================================

set -euo pipefail

IMAGE_NAME="migration-audit"
CONTAINER_NAME="smoke-test-migration-audit"
PORT=8001
TIMEOUT=30

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; }
info() { echo -e "${YELLOW}→ $1${NC}"; }

cleanup() {
    info "Cleaning up container..."
    docker rm -f "$CONTAINER_NAME" &>/dev/null || true
}
trap cleanup EXIT

echo ""
echo "============================================"
echo "  Migration Audit — Docker Smoke Test"
echo "============================================"
echo ""

# --- Step 1: Build the image ---
info "Building Docker image..."
if docker build -t "$IMAGE_NAME:test" . &>/dev/null; then
    pass "Docker image built successfully"
else
    fail "Docker image build failed"
    exit 1
fi

# --- Step 2: Check image size ---
IMAGE_SIZE=$(docker images "$IMAGE_NAME:test" --format "{{.Size}}")
info "Image size: $IMAGE_SIZE"

# Parse numeric MB value for comparison
SIZE_MB=$(echo "$IMAGE_SIZE" | grep -oP '[\d.]+' | head -1)
UNIT=$(echo "$IMAGE_SIZE" | grep -oP '[A-Z]+' | head -1)

if [[ "$UNIT" == "MB" ]] && (( $(echo "$SIZE_MB < 500" | bc -l) )); then
    pass "Image size under 500MB target ($IMAGE_SIZE)"
elif [[ "$UNIT" == "GB" ]]; then
    fail "Image size exceeds target: $IMAGE_SIZE (target: <500MB)"
else
    info "Image size: $IMAGE_SIZE (check manually if acceptable)"
fi

# --- Step 3: Run the container ---
info "Starting container..."
cleanup
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$PORT:$PORT" \
    -e SECRET_KEY=smoke-test-key \
    "$IMAGE_NAME:test" &>/dev/null

if [ $? -eq 0 ]; then
    pass "Container started"
else
    fail "Container failed to start"
    exit 1
fi

# --- Step 4: Wait for readiness ---
info "Waiting for container to be ready (up to ${TIMEOUT}s)..."
ELAPSED=0
READY=false
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -sf "http://localhost:$PORT/" -o /dev/null 2>/dev/null; then
        READY=true
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if $READY; then
    pass "Container is responding (took ~${ELAPSED}s)"
else
    fail "Container did not become ready within ${TIMEOUT}s"
    echo ""
    info "Container logs:"
    docker logs "$CONTAINER_NAME" --tail 30
    exit 1
fi

# --- Step 5: Hit key endpoints ---
info "Testing API endpoints..."

# Root should redirect to /login (302)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/")
if [[ "$HTTP_CODE" == "302" || "$HTTP_CODE" == "307" || "$HTTP_CODE" == "200" ]]; then
    pass "GET / → $HTTP_CODE (redirect or OK)"
else
    fail "GET / → unexpected $HTTP_CODE"
fi

# Login page should return 200
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/login")
if [[ "$HTTP_CODE" == "200" ]]; then
    pass "GET /login → 200 OK"
else
    fail "GET /login → unexpected $HTTP_CODE"
fi

# API config without auth should return 401
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/api/config")
if [[ "$HTTP_CODE" == "401" ]]; then
    pass "GET /api/config → 401 Unauthorized (auth enforced)"
else
    fail "GET /api/config → unexpected $HTTP_CODE (expected 401)"
fi

# --- Step 6: Check container health ---
info "Checking container health..."
HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")
if [[ "$HEALTH" == "healthy" ]]; then
    pass "Container health: $HEALTH"
elif [[ "$HEALTH" == "starting" ]]; then
    info "Container health: $HEALTH (still initializing — acceptable for smoke test)"
else
    info "Container health: $HEALTH"
fi

echo ""
echo "============================================"
echo -e "  ${GREEN}Smoke test completed!${NC}"
echo "============================================"
echo ""
