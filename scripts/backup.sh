#!/usr/bin/env bash
set -euo pipefail

DB_URL="${PAYROLL_DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/payroll}"
OUTPUT_DIR=${1:-backups}
mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_FILE="$OUTPUT_DIR/payroll-$TIMESTAMP.sql"

echo "Creating backup to $BACKUP_FILE"
pg_dump "$DB_URL" > "$BACKUP_FILE"
echo "Backup complete"
