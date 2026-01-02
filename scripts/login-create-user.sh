#!/usr/bin/env bash
set -euo pipefail

API_BASE=${API_BASE:-http://localhost:8000}
EMAIL=${EMAIL:-user@example.test}
PASSWORD=${PASSWORD:-supersafepassword}
ROLE=${ROLE:-admin}

echo "Creating user ${EMAIL} with role ${ROLE} at ${API_BASE}/users ..."
curl -i -X POST "${API_BASE}/users" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\",\"role\":\"${ROLE}\"}"
