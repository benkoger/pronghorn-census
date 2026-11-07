# Feature Specification: Routers Google Python Style Guide

Branch `google_style_routers` off `origin/indev`.

## 1. Overview

This PR refactors all 22 router modules in `airial_api/app/routers/` to adhere strictly to the Google Python Style Guide and standard docstring conventions. It adds comprehensive, structured Google-style docstrings (`Args:`, `Returns:`, `Raises:`) where they were missing or incomplete across all route handlers and helper functions, standardizes import ordering according to PEP 8 and Google style conventions (standard library, third-party, local application), formats code lines to respect clean column limits, and removes obsolete author headers and stale comments.

This is a documentation and code-quality refactor with zero runtime, database schema, or HTTP API behavioral changes.

## 2. Goals

**User-facing.**
- None. API behaviors, database schemas, authentication flows, and HTTP endpoints remain completely unchanged.

**Engineering.**
- Standardize all 22 router files in `airial_api/app/routers/` to Google Python Style Guide conventions.
- Provide structured, descriptive Google-style docstrings (`Args:`, `Returns:`, `Raises:` where applicable) for every endpoint handler and helper function across all router blueprints.
- Organize imports consistently: standard library, third-party packages, internal project modules (database models, extensions, decorators).
- Clean up obsolete boilerplate: eliminate redundant author tags (`# Author: ...`), obsolete `# TODO` comments, and normalize file permissions.
- Ensure strict zero-regression behavior: no modifications to endpoint paths, decorator stacks, status codes, payload structures, or query handling.

## 3. Core Concepts

- **Docstring Format**: All router modules and route functions use Google Python Style Guide docstring format:
  - Single-line summary sentence ending with a period.
  - Multi-line descriptions with separated sections: `Args:`, `Returns:`, `Raises:` where appropriate.
  - OpenAPI/Swagger YAML blocks (`---`) preserved where present for existing documentation tooling.
- **Import Ordering**: Grouped and separated by blank lines according to PEP 8 and Google style:
  1. Standard library imports (e.g., `import io`, `from datetime import UTC, datetime`, `from uuid import UUID`).
  2. Third-party packages (e.g., `flask`, `flask_login`, `flask_pydantic`, `authzed`).
  3. Internal application modules (e.g., `app.decorators`, `app.extensions`, `database.object_models.*`).
- **Standardized Datetime & Types**: Modern standard library idioms such as `datetime.now(UTC)` rather than `datetime.now(timezone.utc)`, formatted string specifiers (`f"{uuid!s}"`), and clean multi-line wrapping for long calls.
- **Affected Router Modules** (22 files):
  - `__init__.py`: Package docstring, sorted blueprint imports and registrations.
  - `active_measurements.py`: Active measurement CRUD endpoints.
  - `am_units.py`: Measurement unit navigation and status endpoints.
  - `annotations.py`: Annotation CRUD, bounding boxes, and relationships.
  - `authenticate.py`: OAuth2 login/callback and legacy credential authentication.
  - `autocropper.py`: Automated spatial batch cropping and draft annotation generation.
  - `cropverifier.py`: Auto-crop review queue, locking, and verification.
  - `herd_units.py`: Herd unit hierarchy endpoints.
  - `image_footprints.py`: Geospatial image footprint endpoints.
  - `image_metadata.py`: Image telemetry, GPS, and metadata endpoints.
  - `images.py`: Image management, presigned S3 URLs, download, and review queues.
  - `labels.py`: Classification taxonomy and label management.
  - `models.py`: Model registry, weights/artifacts management in S3, and training configs.
  - `organizations.py`: Organization administrative endpoints.
  - `predictions.py`: Model inference prediction CRUD and bulk updates.
  - `projects.py`: Project hierarchy, membership, and scoping endpoints.
  - `reviewed_area.py`: Bounding crops, review status, and related annotations.
  - `roles.py`: User authorization role endpoints.
  - `schemas.py`: Taxonomy schema definitions and assignments.
  - `surveys.py`: Survey flight metadata, bounds, and image relationships.
  - `system.py`: Platform health and bootstrap initialization checks.
  - `users.py`: User account lifecycle, sessions, and active organization context.

**Invariants.**
- No endpoint URL route, HTTP verb, query parameter, or status code is changed.
- Decorator chains (`@permission_required`, `@login_required`, `@roles_required`, `@validate()`) remain in identical execution order.
- Request payload models (`flask_pydantic` validated models) and response serialization schemas remain identical.
- Zero changes to database queries, SQL execution, or SpiceDB relationship writing logic.

## 4. Acceptance Criteria

Verified locally on 2026-11-06 on branch `google_style_routers`.

- [x] All 22 router files in `airial_api/app/routers/` pass `py_compile` with zero syntax errors.
- [x] Every public route handler in all router blueprints has a descriptive Google-style docstring detailing `Args:` and `Returns:` (and `Raises:` where explicit errors are raised).
- [x] Imports across all 22 router files follow standard PEP 8 / Google grouping: standard library first, third-party libraries second, internal application modules third.
- [x] Outdated author comments (`# Author: ...`) and stale TODO comments removed across router files.
- [x] File mode of `airial_api/app/routers/__init__.py` normalized to 644 (from 755).
- [x] Zero functional regressions: no changes to endpoint logic, database transactions, SpiceDB permissions, or response status codes.
