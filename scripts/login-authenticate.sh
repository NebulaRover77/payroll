#!/usr/bin/env bash
set -euo pipefail

API_BASE=${API_BASE:-http://localhost:8000}
EMAIL=${EMAIL:-user@example.test}
PASSWORD=${PASSWORD:-supersafepassword}

echo "Logging in as ${EMAIL} at ${API_BASE}/auth/login ..." >&2
RESPONSE=$(curl -s -X POST "${API_BASE}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")

TOKEN=$(printf '%s' "$RESPONSE" | python -c 'import sys, json; data=json.load(sys.stdin); print(data.get("access_token",""))')
if [ -z "$TOKEN" ]; then
  echo "Login failed. Full response:" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

echo "$TOKEN"
