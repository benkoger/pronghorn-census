# Database & Authorization Architecture

This document details the database layer, PostgreSQL schemas based on the canonical DDL in `docs/database/schemas/airial1-1.sql`, the custom Psycopg3 abstraction, PostGIS spatial extensions, and the Relationship-Based Access Control (ReBAC) system.

---

## 1. Database Schemas (PostgreSQL 17 + PostGIS 3.5)

The database schema is partitioned into three PostgreSQL schemas, with PostGIS spatial types hosted in `public`:

### Custom Enum Types
* **`core.activity_type`**: `'auto cropper'`, `'active measurement'`
* **`projectmanagement.model_type`**: `'detection'`, `'regression'`, `'depth estimation'`
* **`projectmanagement.survey_status`**: `'uploaded'`, `'preparing'`, `'ready for measurement'`, `'measuring'`, `'finished'`
* **`usermanagement.user_status`**: `'active'`, `'invited'`, `'disabled'`

---

### `core` Schema
Handles aerial survey imagery, georeferenced spatial footprints, telemetry metadata, computer vision inference, spatial review crops, and census units:
* **`images`**: Metadata for raw survey frames (`name`, `img_key` in S3, pixel dimensions `image_length_px`, `image_width_px`, `in_training`, `crops_generated`, `opened_by_user_id`, `uuid`).
* **`image_metadata`**: Flight telemetry and camera orientation records linked 1:1 to images (`image_id`, `captured_at`, `gps_lon`, `gps_lat`, `gps_alt_msl_m`, `yaw_deg`, `pitch_deg`, `fov_deg`, `terrain_elev_m`, `agl_m`, `uuid`).
* **`image_footprints`**: Georeferenced spatial footprint polygons and camera pose solve records linked 1:1 to images (`image_id`, `footprint` polygon, `footprint_metadata` polygon, `has_detection`, `bbox_wsen`, `footprint_partial`, `area_m2`, `area_geodesic_m2`, `dem_name`, `georef_status`, `rmse_h_m`, pose deltas, `gcps` JSONB, `uuid`).
* **`predictions`**: Candidate detections produced by CV models (`score`, bounding box `box_tx`, `box_ty`, `box_bx`, `box_by`, integer `label`, `model_id`, `uuid`).
* **`reviewed_area`**: Bounded spatial crops produced by Auto-Cropper (default $2100 \times 2100$ px, `ra_key` in S3, `type` of `core.activity_type`, `reviewed_by_user_id`, `uuid`).
* **`annotations`**: Verified ground-truth bounding boxes (`label_id`, `image_id`, `pred_id`, `herd_unit_id`, `type`, `created_by_user_id`, `uuid`).
* **`am_units`**: Active measurement census units (`model_count`, `human_count`, `current_count`, `relative_position`, confidence intervals).
* **`training`**: Junction table (`reviewed_area_id`, `model_id`) tracking crops used for model training.
* **`annotations_reviewed_area`**: Spatial junction table (`annotation_id`, `reviewed_area_id`).

---

### `projectmanagement` Schema
Manages survey organizational hierarchies, geographic herd units, models, and taxonomies:
* **`projects`**: Top-level research or census projects (`name`, `uuid`).
* **`herd_units`**: Wildlife management units / geographic boundaries (`name`, `habitable_area`, `uuid`).
* **`surveys`**: Specific flight campaigns conducted within a herd unit (`name`, `survey_date`, `status` of `survey_status`, `survey_area`, `additional_info`, `uuid`).
* **`models`**: Computer vision models deployed for assisted labeling (`name`, `schema_id`, `model_type`, `uuid`).
* **`schemas`**: Classification taxonomies defining valid categories for a model (`name`, `uuid`).
* **`labels`**: Class definitions (`name`, numeric `label`, `schema_id`, `color`, `image_link`, `uuid`).
* **`active_measurements`**: Abundance measurement definitions (`survey_id`, `label_id`, `target_percentage`, `final_count`, `final_ci_upper`, `final_ci_lower`, `random_seed`, `retraining_cadence`, `uuid`).
* **Relationship / Junction Tables**:
  * `projects_users` (`project_id`, `user_id`, `role_id`)
  * `projects_schemas` (`project_id`, `schema_id`)
  * `projects_herd_units` (`project_id`, `herd_unit_id`)
  * `projects_models` (`project_id`, `model_id`)
  * `projects_surveys` (`survey_id`, `project_id`)
  * `surveys_models` (`survey_id`, `model_id`)
  * `surveys_herd_units` (`survey_id`, `herd_unit_id`)
  * `herd_units_models` (`herd_unit_id`, `model_id`)

---

### `usermanagement` Schema
Manages authentication, system initialization, and multi-tenancy:
* **`users`**: User accounts (`username`, `email`, `password_hash`, `external_auth_id`, `external_auth_provider`, `status` of `user_status`, `last_login`, `locale`, `uuid`).
* **`roles`**: System roles (`name`, `uuid`).
* **`organizations`**: Multi-tenant organizations (`name`, `logo_url`, `uuid`).
* **`initialization`**: System bootstrap status flag (`first_run boolean NOT NULL DEFAULT true`).
* **Junction Tables**:
  * `organizations_projects` (`project_id`, `organization_id`)
  * `organizations_users` (`user_id`, `organization_id`, `role_id`)

---

## 2. Database Abstraction Layer (Strictly NO ORM)

Airial intentionally avoids traditional ORMs like SQLAlchemy or Tortoise. Aerial census data involves high-volume spatial points, bounding boxes, and large image metadata tables where ORM abstractions introduce noticeable serialization overhead and unpredictable query generation.

### Abstraction Mechanics (`airial_api/database/database.py`)
1. **Connection Pooling**: Managed via `psycopg_pool.ConnectionPool`. Configured with health checks, max lifetime (290s), and automatic cleanup.
2. **Context Decorator (`@connect`)**: Wraps database operations, automatically borrowing a connection and cursor from the pool unless one is explicitly passed in.
3. **Safe SQL Composition**: Uses `psycopg.sql` (`Identifier`, `Placeholder`, `Composed`) via helper functions in `query_builder.py` to prevent SQL injection while maintaining raw query performance.
4. **Pydantic Model Mapping**: Deserializes SQL result sets into typed Pydantic models (`database/object_models/`) using `psycopg.rows.class_row`.
5. **PostgreSQL Enum Registration**: Enums (`projectmanagement.model_type`, `core.activity_type`) are registered automatically on newly opened connections.

### Dual Identifier Pattern
All primary entities support two identifiers:
* **Serial Integer ID (`<entity>_id`)**: Fast internal foreign keys and integer indexing.
* **UUID (`uuid`)**: Public, URL-safe identifiers used in API endpoints, frontend state, and SpiceDB relationships.

The codebase defines:
```python
PrimaryKey = int | UUID
Keyring(pkey: int, uuid: UUID)
```
Queries dynamically resolve whether an integer or UUID was passed using `resolve_identifier()` and `filter_by_object_ids()` in `query_builder.py`.

---

## 3. Schema Migrations (Atlas)

Database schema changes are managed with [Atlas](https://atlasgo.io/) in the `local_db/migrations/` directory:
* Versioned SQL migration files are tracked with an integrity checksum in `local_db/migrations/atlas.sum`.
* The canonical schema definition for reference is maintained in `docs/database/schemas/airial1-1.sql`.
* Ephemeral development diffing and migration applications are executed against the running `prong_gres` database container.

---

## 4. Authorization & Permissions (SpiceDB ReBAC)

Airial implements fine-grained Relationship-Based Access Control (ReBAC) powered by [SpiceDB](https://authzed.com/spicedb) (based on Google's Zanzibar paper).

### Object Hierarchy (`airial_api/database/spicedb_schema/schema.zed`)
```
platform (root)
  └── organization (root, admin, annotator)
        └── project (annotator)
              ├── herd_unit
              │     └── survey
              │           ├── active_measurement
              │           │     └── am_unit
              │           └── image
              │                 ├── image_metadata
              │                 ├── image_footprint
              │                 ├── prediction
              │                 ├── reviewed_area
              │                 └── annotation
              └── model
                    └── schema
                          └── label
```

### Permission Enforcement
* Child objects inherit access from parent containers (e.g., access to an `image` implies access to its child `predictions`, `reviewed_areas`, and `annotations`).
* Permissions are evaluated with sub-millisecond gRPC checks.
* **Flask Decorator (`@permission_required("access")`)**:
  * Automatically intercepts incoming request parameters (such as `image_id` or `herd_unit_id`).
  * Resolves the entity UUID from the database.
  * Issues a SpiceDB `CheckPermission` or `BulkCheckPermission` request for the authenticated `current_user`.
  * Returns HTTP 403 / 401 if unauthorized.
* **Relationship Writes**: When entities are created or linked, `Database.write_spice_relationships()` writes the graph edge to SpiceDB.

---

## 5. Cache & Session Store (Valkey)

* **Valkey DB 0 (Flask-Session)**: Stores server-side session payloads signed cryptographically with `SECRET_KEY`. Cookies are set with `SameSite=Lax`.
* **Valkey DB 1 (Flask-Caching)**: Short-term cache for image byte buffers (TTL 500s) to avoid repeated S3 requests during active cropping sessions.
