# AIRIAL CORE INFRASTRUCTURE - AGENT GUIDE (AGENTS.md)

This document is the primary onboarding and operational guide for AI coding assistants working in this repository. Read this file carefully before inspecting or modifying code.

---

## 1. Executive Summary & Project Context

* **Project**: **Airial** (also referred to as *Pronghorn Census* / *Assisted Labeling & Census Software*).
* **Domain**: Computer vision-assisted wildlife census and abundance estimation (specifically aerial surveys of wildlife like pronghorn).
* **Organization**: Academic / Non-profit wildlife conservation research (University of Wyoming - Ben Koger Lab).
* **Development Reality**:
  * **Team size**: **1 human developer**.
  * **Goal**: Deliver a functional, feature-complete, end-to-end working product as rapidly as possible.
  * **Testing Status**: Automated tests are currently **not implemented / deferred** by design. Do **not** block work on tests, scold about test coverage, or spend time building extensive test suites unless explicitly instructed. Prioritize pragmatic, working code and rapid end-to-end feature delivery.

---

## 2. System Architecture & Tech Stack

```
                                  +-----------------------+
                                  |     Vue 3 + TS SPA    |
                                  |  (generator_web_app)  |
                                  +-----------+-----------+
                                              | HTTP / REST (5173 -> 8000)
                                              v
                                  +-----------------------+
                                  |    Flask Python API   |
                                  |     (airial_api)      |
                                  +---+---+-------+---+---+
                                      |   |       |   |
             +------------------------+   |       |   +------------------------+
             |                            |       |                            |
             v                            v       v                            v
+------------------------+   +--------------+   +---------------+   +------------------------+
| PostgreSQL 17+PostGIS  |   |  Valkey 8.1  |   |    SpiceDB    |   |     S3 / Ceph API      |
|  (Custom Psycopg3 DB)  |   | (Cache/Sess) |   |    (ReBAC)    |   |    (Images/Crops)      |
+------------------------+   +--------------+   +---------------+   +------------------------+
```

### Component Summary

| Component | Technology | Path / Location | Notes |
| :--- | :--- | :--- | :--- |
| **Frontend** | Vue 3, TypeScript 5.8, Vite 6, Pinia, Bootstrap 5, Vue-Konva | `generator_web_app/` | SPA for labeling, verification, and data administration |
| **Backend API** | Python 3.13+, Flask 3.1, Werkzeug, uv | `airial_api/` | RESTful API, custom database layer, image processing |
| **Database** | PostgreSQL 17 + PostGIS 3.5 | `docs/database/schemas/airial1-1.sql`, `local_db/migrations/` | Schemas: `core`, `projectmanagement`, `usermanagement` (Canonical DDL in `docs/database/schemas/airial1-1.sql`) |
| **Database Abstraction**| Psycopg 3 (`psycopg[binary]`, `psycopg-pool`) | `airial_api/database/` | **STRICTLY NO ORM**. Custom high-performance abstraction |
| **Authorization** | SpiceDB (Authzed client, gRPC) | `airial_api/database/spicedb_schema/` | Fine-grained Relationship-Based Access Control (ReBAC) |
| **Cache & Sessions** | Valkey 8.1 (open-source Redis fork) | Port 6379 | DB 0: Flask-Session, DB 1: Flask-Caching |
| **Object Storage** | S3 API (Ceph Object Gateway or AWS S3) | Boto3 client | Aerial survey imagery, crops, artifacts |
| **CV / Labeling Tool** | OpenCV, NumPy, Scikit-Learn (KMeans) | `airial_api/crop_generator.py` | Spatial clustering & subcrop generation |
| **Migrations** | Atlas | `local_db/migrations/` | Managed declarative/versioned SQL migrations |

---

## 3. Database Layer: Rules & Philosophy

> [!IMPORTANT]
> **NO ORMs (e.g., SQLAlchemy, Django ORM, Tortoise).**
> The project deliberately chose **not** to use an ORM due to overhead, slow queries on large spatial datasets, and leaky abstractions. We use a purpose-built abstraction layer built on `psycopg3`.

### Abstraction Mechanics (`airial_api/database/database.py`)
1. **Connection Pooling**: Managed via `ConnectionPool` in `Database.create_pool()`.
2. **Context Wrapper (`@connect`)**: Decorator on `Database` methods that automatically checks out a connection and cursor unless one is explicitly passed in.
3. **Pydantic Model Mapping**: Queries use `class_row(Model)` or instantiate Pydantic models defined in `airial_api/database/object_models/`.
4. **Custom Enums**: PostgreSQL enums (`projectmanagement.model_type`, `core.activity_type`) are automatically fetched and registered on each connection.
5. **Dual Identifiers**: Every major record supports both:
   * Serial integer primary key (`<entity>_id`)
   * Public UUID (`uuid`)
   * Defined using `PrimaryKey = int | UUID` and `Keyring(pkey: int, uuid: UUID)`.
   * Queries dynamically resolve ID type via `resolve_identifier` and `filter_by_object_ids` in `query_builder.py`.

---

## 4. Authorization & ReBAC (SpiceDB)

All permissions use SpiceDB Relationship-Based Access Control (ReBAC).

### Hierarchy (`schema.zed`)
```
platform (root)
  └── organization (root, admin, annotator)
        └── project (annotator)
              ├── herd_unit
              │     └── survey
              │           ├── active_measurement
              │           │     └── am_unit
              │           └── image
              │                 ├── prediction
              │                 ├── reviewed_area
              │                 └── annotation
              └── model
                    └── schema
                          └── label
```

### Route Enforcement (`airial_api/app/decorators.py`)
* `@permission_required("access")`: Automatically inspects request parameters (e.g., `image_id`, `herd_unit_id`), checks object existence in DB, extracts UUIDs, and executes a SpiceDB `CheckPermission` or `BulkCheckPermission`.
* `@roles_required("admin")`: Enforces traditional administrative roles on users.
* When inserting records that live under parents, the API writes the corresponding relationship into SpiceDB using `Database.write_spice_relationships(...)`.

---

## 5. Computer Vision & Assisted Labeling Engine

High-resolution aerial survey frames can be hundreds of megapixels. Annotators cannot feasibly scan full frames. The pipeline implements a model-assisted labeling workflow:

1. **Auto-Cropper (`auto_crop(...)` in `crop_generator.py`)**:
   * Takes an aerial `Image`, candidate `Prediction` objects, and valid `Label` taxonomy.
   * Uses `KMeans` spatial clustering on prediction coordinates to group detections into bounding crops (default 2100x2100 px `ReviewedArea` records).
   * If predictions exceed crop bounds, it recursively increases cluster count ($k \leftarrow k + 1$) until all predictions belong to a valid crop.
   * Generates draft `Annotation` records linked to the enclosed predictions and uploads the cropped image slices to S3.
2. **Crop-Verifier (`/crop-verifier/` UI & `cropVerifierStore.ts`)**:
   * Directly verifies the output crops produced by the Auto-Cropper.
   * Loads `ReviewedArea` crops needing review into the Konva canvas alongside draft annotations.
   * Human annotators confirm detections, adjust bounding box boundaries, correct misclassified species, delete false positives, and draw boxes for missed wildlife.
   * Submitting commits verified annotations to the database and marks the `ReviewedArea` as reviewed.
3. **Prediction Sub-Cropper (`create_subcrop(...)`)**:
   * Utility for generating small subcrops (default 150px) centered directly on individual model predictions, cached in Valkey for rapid chip viewing.

---

## 6. Frontend Architecture (`generator_web_app/`)

* **Framework**: Vue 3 with TypeScript, using `<script setup lang="ts">`.
* **State Management (`src/modules/stores/`)**:
  * `systemStore.ts`: Authentication state, current user profile, bootstrap status.
  * `projectStore.ts`: Hierarchical context selectors (Org -> Project -> Herd Unit -> Survey / Model).
  * `cropperStore.ts`: State machine for auto-cropper batch review and submission.
  * `cropVerifierStore.ts`: Fast-path chip verification loop with keyboard navigation.
* **Canvas Labeling**: Implemented with `vue-konva` for interactive panning, zooming, and bounding-box drawing/editing.
* **Routing (`src/router.ts`)**:
  * Global navigation guard checks whether API is bootstrapped (`/setup` route).
  * Enforces authentication (`/authenticate` route) for protected views.

---

## 7. Container Orchestration & Local Dev

### Compose Configurations

| File | Primary Use Case | Database Source |
| :--- | :--- | :--- |
| `development.compose.yml` | Normal local dev | Restores sample DB from `local_db/pct_b` & SpiceDB from `local_db/backup.zed` |
| `bootstrap-dev.compose.yml` | Clean dev environment | Initializes fresh schema from `docs/database/schemas/airial1-1.sql` & `schema.zed` |
| `production.compose.yml` | Production deployment | Hardened setup with TLS certificates, Gunicorn WSGI, and Nginx |

### Common Commands

```bash
# Start local development environment (Podman or Docker)
podman compose -f development.compose.yml up -d
# or
docker compose -f development.compose.yml up -d

# Start clean bootstrap environment
podman compose -f bootstrap-dev.compose.yml up -d

# Frontend local development (outside container)
cd generator_web_app
npm install
npm run dev        # Dev server on http://localhost:5173
npm run type-check # Run vue-tsc type checking

# Backend API local development (outside container)
cd airial_api
uv sync
uv run python app.py  # Runs Flask debug server on http://localhost:8000
```

---

## 8. Agent Rules of Engagement

When modifying this repository, follow these principles:

1. **Be pragmatic & build end-to-end**: The user is a solo human developer aiming for working software. Avoid overengineering or proposing heavy architectural rewrites.
2. **Never introduce an ORM**: Always write queries using `psycopg3`, `psycopg.sql`, and the existing `Database` abstraction methods.
3. **Respect dual-ID typing**: Keep methods compatible with both `int` and `UUID` IDs (`PrimaryKey = int | UUID`).
4. **Maintain SpiceDB consistency**: If you add new hierarchical entities or relationships, update `schema.zed` and ensure relationship writes occur on record creation.
5. **Handle images carefully**: Large image payloads belong in S3 (or Valkey cache for ephemeral crops); never store raw image bytes in PostgreSQL.
