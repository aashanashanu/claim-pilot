#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TF_DIR="infra/aws"

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is required but was not found in PATH."
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required but was not found in PATH."
  exit 1
fi

backend_url="$(terraform -chdir="$TF_DIR" output -raw backend_url)"
frontend_url="$(terraform -chdir="$TF_DIR" output -raw frontend_url)"

if [[ -z "$backend_url" || -z "$frontend_url" ]]; then
  echo "Terraform outputs are missing backend_url or frontend_url."
  exit 1
fi

echo "Using backend: $backend_url"
echo "Using frontend: $frontend_url"

check_url() {
  local name="$1"
  local url="$2"
  local method="${3:-GET}"

  echo "Checking $name ($method $url)"
  if [[ "$method" == "POST" ]]; then
    curl -fsS -X POST "$url" >/tmp/claimpilot-smoke-last.json
  else
    curl -fsS "$url" >/tmp/claimpilot-smoke-last.json
  fi
  echo "OK: $name"
}

assert_contains() {
  local needle="$1"
  if ! grep -q "$needle" /tmp/claimpilot-smoke-last.json; then
    echo "Expected response to contain: $needle"
    echo "Actual response:"
    cat /tmp/claimpilot-smoke-last.json
    exit 1
  fi
}

check_url "backend health" "$backend_url/health"
assert_contains '"status":"ok"'

check_url "gmail health" "$backend_url/health/gmail"
assert_contains '"status":"ok"'

check_url "demo runbook" "$backend_url/demo/runbook" "POST"
assert_contains '"runbook":"phase4_demo_surface"'

check_url "storefront snapshot" "$backend_url/storefront"
assert_contains '"catalog"'

echo "Checking frontend reachability (GET $frontend_url)"
curl -fsSI "$frontend_url" >/tmp/claimpilot-smoke-frontend-head.txt
grep -qi "200" /tmp/claimpilot-smoke-frontend-head.txt

echo "All smoke checks passed."
