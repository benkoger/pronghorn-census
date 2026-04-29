#!/bin/bash
set -e

# Define the backup directory location inside the container
BACKUP_DIR="/pct_b"

echo "Building local database from $BACKUP_DIR..."
pg_restore -v -d "$POSTGRES_DB" -U "$POSTGRES_USER" "$BACKUP_DIR"

