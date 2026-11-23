---
name: db-migrations
description: >-
  Use this skill when modifying database tables, adding columns, updating PostgreSQL schemas (core, projectmanagement, usermanagement), writing SQL migrations, or synchronizing Pydantic models.
---

# Database Schema & Model Synchronization

This runbook guides agents on modifying PostgreSQL schemas and keeping backend object models synchronized.

## 1. Schema Architecture

The PostgreSQL database is divided into three distinct schemas:
1. `core`: `images`, `predictions`, `reviewed_area`, `annotations`, `am_units`, `proposal_generations`, `training`, `image_metadata`, `image_footprints`.
2. `projectmanagement`: `projects`, `surveys`, `herd_units`, `models`, `schemas`, `labels`, `active_measurements`.
3. `usermanagement`: `users`, `roles`, `organizations`, `user_roles`, `user_organizations`, `project_users`.

All tables utilize both an integer serial primary key (`<entity>_id`) and a UUID column (`uuid UNIQUE NOT NULL DEFAULT gen_random_uuid()`).
Spatial / geospatial tables use PostGIS geometries (`public.geometry(Polygon, 4326)`).

---

## 2. Migration Workflow

Migrations are managed with Atlas in `local_db/migrations/`.

1. **Inspect canonical schema**: Check `docs/database/schemas/airial1-2.sql` and the active migration history in `local_db/migrations/`.
2. **Update canonical schema**: Add or alter tables, columns, indexes, and constraints in `docs/database/schemas/airial1-<ver>.sql`.
   * *PostGIS types note*: Qualify PostGIS geometry types as `public.geometry(Polygon, 4326)` without double quotes so Atlas parses them without requiring `CREATE EXTENSION` inside the schema DDL.
3. **Write the Atlas Migration**:
   * `atlas migrate diff` cannot load this schema on the free Atlas tier: the desired-state DDL
     needs the PostGIS extension, and extensions in the desired state require `atlas login`.
     Write the migration by hand instead, in the same style as the existing files (one
     `-- Create/Modify "<table>" table` comment per statement, fully qualified and quoted
     identifiers, `DEFERRABLE` on every foreign key), named `YYYYMMDDHHMMSS_<name>.sql`.
   * Refresh the checksum file and validate the directory (no database needed):
     ```bash
     atlas migrate hash --dir "file://local_db/migrations"
     atlas migrate validate --dir "file://local_db/migrations"
     ```
   * Prove the migration chain and the DDL agree: apply each to a fresh database created from
     `template_postgis` in `prong_gres` (`psql -v ON_ERROR_STOP=1 -f`), then compare the
     two through `information_schema.columns`, `pg_constraint`, `pg_indexes` and `pg_enum`.
     `docs/plans/schema-migrations.md` describes the comparison used for Airial 1.2.
4. **Apply Migration**:
   * Check status:
     ```bash
     atlas migrate status --dir "file://local_db/migrations" --url "postgres://pronghorn_count:${DB_PASS}@localhost:5432/testing?sslmode=disable"
     ```
   * If baseline versions exist that were already loaded into the target DB, set the baseline version:
     ```bash
     atlas migrate set <baseline_version> --dir "file://local_db/migrations" --url "postgres://pronghorn_count:${DB_PASS}@localhost:5432/testing?sslmode=disable"
     ```
   * Apply pending migrations:
     ```bash
     atlas migrate apply --dir "file://local_db/migrations" --url "postgres://pronghorn_count:${DB_PASS}@localhost:5432/testing?sslmode=disable"
     ```
5. **Update Dev Backup Dump (`local_db/pct_b`)**:
   * Build the new dump from the committed one, not from a working database: restore
     `local_db/pct_b` into a fresh database, apply the new migrations there, and dump that.
     A working database carries local rows the sample data should not.
   * Re-dump updated schemas to `local_db/pct_b` using directory format:
     ```bash
     podman exec prong_gres pg_dump -Fd -U pronghorn_count -d testing \
       -n core -n projectmanagement -n usermanagement \
       -f /tmp/new_pct_b
     rm -rf local_db/pct_b/*
     podman cp prong_gres:/tmp/new_pct_b/. local_db/pct_b/
     podman exec prong_gres rm -rf /tmp/new_pct_b
     ```
6. **Synchronize Object Models (`airial_api/database/object_models/`)**:
   * Every table has a corresponding Pydantic / dataclass representation under `airial_api/database/object_models/`:
     * `core/`: Data models for images, annotations, predictions, image_metadata, image_footprints, etc.
     * `project_management/`: Data models for projects, surveys, herd units, models, labels.
     * `user_management/`: Data models for users, roles, organizations.
   * Register any newly added PostgreSQL enum types in `configure_connection` in `airial_api/database/database.py`.
7. **Update SpiceDB ReBAC (if entity hierarchy changed)**:
   * Edit `airial_api/database/spicedb_schema/schema.zed` if a new object type or relation was introduced.
   * If a new parent-child relation is created, write the SpiceDB relationship during insert in `airial_api/database/database.py` or the corresponding router.
