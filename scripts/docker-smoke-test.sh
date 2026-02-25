#!/usr/bin/env bash
# Docker full-stack smoke test for petclinic-python.
# Builds and starts all services via docker compose, waits for health,
# then verifies 3 key endpoints respond correctly.
#
# Usage:
#   ./scripts/docker-smoke-test.sh          # build + test + teardown
#   SKIP_BUILD=1 ./scripts/docker-smoke-test.sh  # skip build (use existing images)
#   KEEP_RUNNING=1 ./scripts/docker-smoke-test.sh  # don't tear down after test

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
MAX_WAIT=180        # Max seconds to wait for services to become healthy
POLL_INTERVAL=5     # Seconds between health polls
GATEWAY_PORT=8080
CUSTOMERS_PORT=8081
VETS_PORT=8083

PASS=0
FAIL=0

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

log()  { printf '\033[1;34m[smoke]\033[0m %s\n' "$*"; }
pass() { printf '\033[1;32m  ✓ PASS:\033[0m %s\n' "$*"; PASS=$((PASS + 1)); }
fail() { printf '\033[1;31m  ✗ FAIL:\033[0m %s\n' "$*"; FAIL=$((FAIL + 1)); }

cleanup() {
    if [ "${KEEP_RUNNING:-}" = "1" ]; then
        log "KEEP_RUNNING=1 — leaving containers running"
        return
    fi
    log "Tearing down Docker stack..."
    cd "$PROJECT_DIR" && docker compose down --volumes --remove-orphans 2>/dev/null || true
}

# ──────────────────────────────────────────────
# Wait for a service health endpoint
# ──────────────────────────────────────────────

wait_for_health() {
    local name="$1" url="$2"
    local elapsed=0
    log "Waiting for $name at $url ..."
    while [ $elapsed -lt $MAX_WAIT ]; do
        if curl -sf "$url" >/dev/null 2>&1; then
            log "$name is healthy (${elapsed}s)"
            return 0
        fi
        sleep "$POLL_INTERVAL"
        elapsed=$((elapsed + POLL_INTERVAL))
    done
    fail "$name did not become healthy within ${MAX_WAIT}s"
    return 1
}

# ──────────────────────────────────────────────
# Endpoint assertion helpers
# ──────────────────────────────────────────────

assert_status() {
    local desc="$1" url="$2" expected_status="$3"
    local actual_status
    actual_status=$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo "000")
    if [ "$actual_status" = "$expected_status" ]; then
        pass "$desc — HTTP $actual_status"
    else
        fail "$desc — expected HTTP $expected_status, got $actual_status"
    fi
}

assert_json_contains() {
    local desc="$1" url="$2" expected_text="$3"
    local body
    body=$(curl -sf "$url" 2>/dev/null || echo "")
    if echo "$body" | grep -q "$expected_text"; then
        pass "$desc — response contains '$expected_text'"
    else
        fail "$desc — response missing '$expected_text'"
    fi
}

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

trap cleanup EXIT

cd "$PROJECT_DIR"

# Step 1: Build and start
if [ "${SKIP_BUILD:-}" = "1" ]; then
    log "SKIP_BUILD=1 — starting with existing images"
    docker compose up -d
else
    log "Building and starting Docker stack..."
    docker compose up -d --build
fi

# Step 2: Wait for health on infrastructure + business services
wait_for_health "config-server"     "http://localhost:8888/actuator/health"
wait_for_health "discovery-server"  "http://localhost:8761/actuator/health"
wait_for_health "customers-service" "http://localhost:${CUSTOMERS_PORT}/actuator/health"
wait_for_health "vets-service"      "http://localhost:${VETS_PORT}/actuator/health"
wait_for_health "api-gateway"       "http://localhost:${GATEWAY_PORT}/actuator/health"

# Step 3: Smoke-test 3 key endpoints
log ""
log "Running endpoint checks..."

# Endpoint 1: Customers service returns seeded owners
assert_status "GET /owners (customers-service)" \
    "http://localhost:${CUSTOMERS_PORT}/owners" "200"
assert_json_contains "GET /owners has seed data" \
    "http://localhost:${CUSTOMERS_PORT}/owners" "George"

# Endpoint 2: Vets service returns seeded vets
assert_status "GET /vets (vets-service)" \
    "http://localhost:${VETS_PORT}/vets" "200"
assert_json_contains "GET /vets has seed data" \
    "http://localhost:${VETS_PORT}/vets" "James"

# Endpoint 3: API Gateway health (proves gateway is routing)
assert_status "GET /actuator/health (api-gateway)" \
    "http://localhost:${GATEWAY_PORT}/actuator/health" "200"
assert_json_contains "Gateway health is UP" \
    "http://localhost:${GATEWAY_PORT}/actuator/health" "UP"

# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────

log ""
log "══════════════════════════════════════"
log "  Results: $PASS passed, $FAIL failed"
log "══════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
