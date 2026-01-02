#!/usr/bin/env bash
set -euo pipefail

API_BASE=${API_BASE:-http://localhost:8000}

echo "Checking API health at ${API_BASE}/health ..."
curl -i "${API_BASE}/health"
