---
name: db-migrations
description: >-
  Use this skill when modifying database tables, adding columns, updating PostgreSQL schemas (core, projectmanagement, usermanagement), writing SQL migrations, or synchronizing Pydantic models.
---

# Database Schema & Model Synchronization

This runbook guides agents on modifying PostgreSQL schemas and keeping backend object models synchronized.

## 1. Schema Architecture

The PostgreSQL database is divided into three distinct schemas:
1. `core`: `images`, `predictions`, `reviewed_area`, `annotations`, `active_measurements`, `am_units`, `activity`.
2. `projectmanagement`: `projects`, `surveys`, `herd_units`, `models`, `schemas`, `labels`.
3. `usermanagement`: `users`, `roles`, `organizations`, `user_roles`, `user_organizations`, `project_users`.

All tables utilize both an integer serial primary key (`<entity>_id`) and a UUID column (`uuid UNIQUE NOT NULL DEFAULT gen_random_uuid()`).

---

## 2. Migration Workflow

Migrations are managed with Atlas in the `migrations/` directory.

1. **Inspect existing baseline**: Check `migrations/` and `local_db/db_definitions.sql`.
2. **Write targeted SQL change**: Add incremental DDL or update scripts in `airial_api/database/sql_scripts/` or `migrations/`.
3. **Synchronize Object Models (`airial_api/database/object_models/`)**:
   * Every table has a corresponding Pydantic / dataclass representation under `airial_api/database/object_models/`:
     * `core/`: Data models for images, annotations, predictions, etc.
     * `project_management/`: Data models for projects, surveys, herd units, models, labels.
     * `user_management/`: Data models for users, roles, organizations.
   * Update the model definition:
     * Set `__tablename__`, `__schema__`, `__pk_name__`.
     * Update request/response models (e.g. `Create<Entity>Req`, `<Entity>Response`).
4. **Update SpiceDB ReBAC (if entity hierarchy changed)**:
   * Edit `airial_api/database/spicedb_schema/schema.zed` if a new object type or relation was introduced.
   * If a new parent-child relation is created, write the SpiceDB relationship during insert in `airial_api/database/database.py` or the corresponding router.
5. **Update Schema Definitions**:
   * Ensure `local_db/db_definitions.sql` reflects the latest structure for clean bootstrap builds.
