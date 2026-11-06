# Feature Specification: Database Google Python Style Guide

Branch `database-google-docs` off `origin/indev`.

## 1. Overview

This PR refactors the database package (`airial_api/database/`) to adhere to the Google Python Style Guide and standard docstring conventions. It adds structured docstrings across all modules, classes, and methods, standardizes import ordering according to PEP 8 and Google style, removes obsolete and unused typing imports, and formats lines to standard column boundaries.

This is a documentation and code-quality update with zero runtime, schema, or functional behavioral changes.

## 2. Goals

**User-facing.**
- None. API behaviors, database schemas, and HTTP endpoints remain unchanged.

**Engineering.**
- Provide consistent Google-style docstrings (`Args:`, `Returns:`, `Raises:`) across all query builders, object models, and database access methods.
- Standardize import ordering across all 35 database source files into standard library, third-party, and local application blocks.
- Modernize collection typing (e.g., `collections.abc.Callable`, `collections.abc.Iterable`) and clean up unused imports (`Optional`, `Type`, redundant `UUID` bindings).
- Keep lines within 126-column formatting limits where practical without compromising readability.

## 3. Core Concepts

- **Google Style Docstrings.** Triple-quoted docstrings with `Args:`, `Returns:`, and `Raises:` sections for functions and methods, and class docstrings detailing responsibilities and attributes.
- **Import Ordering.** Three distinct blocks separated by single blank lines:
  1. Standard library imports.
  2. Third-party packages (`psycopg`, `pydantic`, `authzed`).
  3. Internal project modules (`database.query_builder`, `database.object_models`).
- **Typing Modernization.** Replacement of deprecated `typing` constructs with standard library equivalents and pruning of unreferenced imports.

**Invariants.**
- Zero SQL query modifications: all queries, placeholders, and parameters remain identical.
- Zero method signature or return value changes.
- Zero schema or SpiceDB relationship changes.

## 4. Edge Cases

| Scenario | Expected behaviour |
| :--- | :--- |
| Runtime execution | Unchanged; no algorithmic or functional modifications. |
| SQL queries | SQL strings, query compositions, and parameters remain identical. |
| Model interfaces | All method signatures, arguments, defaults, and return types remain identical. |
| Pydantic schemas | Request and response validation rules and field types remain identical. |
| Import namespace | Unused imports removed; all exported public symbols in `__all__` remain available. |

## 5. Acceptance Criteria

- [x] All 35 modified files in `airial_api/database/` pass Python compilation (`py_compile`) with zero syntax errors.
- [x] All public modules have module-level docstrings describing their role in the database architecture.
- [x] Classes, methods, and functions follow Google-style docstrings (`Args:`, `Returns:`, `Raises:`).
- [x] Import ordering adheres to standard library, third-party, and internal application groupings.
- [x] No behavioural, query, or schema regressions are introduced.
