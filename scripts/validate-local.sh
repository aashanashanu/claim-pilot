#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Running backend tests"
python -m pytest

echo "Running focused integration checks"
python -m pytest tests/test_phase2_integrations.py tests/test_phase3_decision_capture.py tests/test_phase4_demo_surface.py

echo "Running frontend production build"
cd frontend
npm run build

echo "Local validation completed successfully"
