#!/bin/bash
set -e

# Define the backup directory location inside the container
BACKUP_DIR="/dev-bootstrap"

echo "Building local database from $BACKUP_DIR..."

# Run pg_restore
# -v: verbose
# -d: database name (matches POSTGRES_DB env var)
# -U: user (matches POSTGRES_USER env var)
pg_restore -v -d "$POSTGRES_DB" -U "$POSTGRES_USER" "$BACKUP_DIR"