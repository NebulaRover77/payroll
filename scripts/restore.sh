#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE=${1:?"Pass the backup file to restore"}
DB_URL="${PAYROLL_DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/payroll}"

echo "Restoring $BACKUP_FILE into $DB_URL"
psql "$DB_URL" < "$BACKUP_FILE"
echo "Restore completed"
