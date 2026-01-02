#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
API_BASE=${API_BASE:-http://localhost:8000}
TOKEN=${TOKEN:-}

if [ -z "$TOKEN" ]; then
  TOKEN=$("${SCRIPT_DIR}/login-authenticate.sh")
fi

echo "Fetching users with token at ${API_BASE}/users ..." >&2
curl -i -H "Authorization: Bearer ${TOKEN}" "${API_BASE}/users"
