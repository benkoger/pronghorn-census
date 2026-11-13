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
- Organize imports consistently: Organize imports alphabetically.
- Clean up obsolete boilerplate: eliminate redundant author tags (`# Author: ...`), obsolete `# TODO` comments, and normalize file permissions.
- Ensure strict zero-regression behavior: no modifications to endpoint paths, decorator stacks, status codes, payload structures, or query handling.

**Invariants.**
- No endpoint URL route, HTTP verb, query parameter, or status code is changed.
- Decorator chains (`@permission_required`, `@login_required`, `@roles_required`, `@validate()`) remain in identical execution order.
- Request payload models (`flask_pydantic` validated models) and response serialization schemas remain identical.
- Zero changes to database queries, SQL execution, or SpiceDB relationship writing logic.

## 4. Acceptance Criteria

Verified locally on 2026-11-06 on branch `google_style_routers`.

- [x] All 22 router files in `airial_api/app/routers/` pass `py_compile` with zero syntax errors.
- [x] Every public route handler in all router blueprints has a descriptive Google-style docstring detailing `Args:` and `Returns:` (and `Raises:` where explicit errors are raised).
- [x] Standardized OpenAPI/Swagger specification YAML blocks (`---`) completed across all endpoints with consistent dual-identifier schemas, valid request parameters, and status responses.
- [x] Imports across all 22 router files follow standard PEP 8 / Google grouping: standard library first, third-party libraries second, internal application modules third.
- [x] Outdated author comments (`# Author: ...`) and stale TODO comments removed across router files.
- [x] File mode of `airial_api/app/routers/__init__.py` normalized to 644 (from 755).
- [x] Zero functional regressions: no changes to endpoint logic, database transactions, SpiceDB permissions, or response status codes.
