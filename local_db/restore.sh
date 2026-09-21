#!/bin/bash
set -e

# Define the backup directory location inside the container
BACKUP_DIR="/pct_b"

pg_restore -v -d "$POSTGRES_DB" -U "$POSTGRES_USER" "$BACKUP_DIR"

# Clean up default PostGIS tiger/topology schemas that are not used by Airial
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<-EOSQL
    DROP EXTENSION IF EXISTS postgis_tiger_geocoder CASCADE;
    DROP EXTENSION IF EXISTS postgis_topology CASCADE;
    DROP EXTENSION IF EXISTS fuzzystrmatch CASCADE;
    DROP SCHEMA IF EXISTS tiger CASCADE;
    DROP SCHEMA IF EXISTS tiger_data CASCADE;
    DROP SCHEMA IF EXISTS topology CASCADE;
EOSQL

