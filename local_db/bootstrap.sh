#!/bin/bash 
set -e 

psql -h "$DB_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /db_definitions.sql
