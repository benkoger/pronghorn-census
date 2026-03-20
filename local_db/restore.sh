#!/bin/bash
set -e

# Define the backup directory location inside the container
BACKUP_DIR="/dev-bootstrap"

echo "Building local database from $BACKUP_DIR..."
pg_restore -v -d "$POSTGRES_DB" -U "$POSTGRES_USER" "$BACKUP_DIR"

echo "Creating SpiceDB logical database..."
psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE spicedb;"
