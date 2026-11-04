# Feature Specification: Schema and Migrations

Branch `schema-migrations` off `origin/indev`. Part of the series in
[active-measurement-rebuild.md](active-measurement-rebuild.md).

## 1. Overview

This PR lands every table and column the active measurement rebuild needs, and puts the
migration workflow back on its feet: the canonical DDL is restored as
`docs/database/schemas/airial1-2.sql`, three Atlas migrations bring the history up to it, the
object models match, and the sample dump restores to the same schema. No router, module or
SpiceDB code changes. The only behavioural change visible to the API is that image metadata
now carries a `transect_id`.

## 2. Goals

**User-facing.**
- None directly. Everything here is groundwork for the measurement PRs.

**Engineering.**
- Proposal generations have a durable home in PostgreSQL, so a measurement survives a
  Valkey restart or a gunicorn worker change.
- Measurement units form a linked list with keys that point the right way and clean up on
  delete.
- Images know their flight line, so transect-aware sampling has a column to read.
- `bootstrap-dev.compose.yml`, the docs and the migrations skill point at a DDL file that
  exists, and the migration chain, the DDL and the dump agree with each other.

## 3. Core Concepts

- **Proposal generation.** One fit of the sampling proposal: the unit order
  (`reviewed_area_ids`), the regressor's expected count per unit (`raw`) and the shaped
  vector the sampler draws from (`proposal`), plus `n_labels`, `model_id` and `alpha`. Stored
  in `core.proposal_generations`, one row per generation, vectors whole in unit order.
  It lives in `core` beside `am_units` because it is measurement working data, not project
  management.
- **Linked list.** `am_units.previous_unit_id` and `next_unit_id` reference `am_unit_id`,
  with `ON DELETE SET NULL` so removing a unit leaves its neighbours valid. The former
  uniqueness on `reg_model_id` and `dect_model_id` is dropped: every unit of a measurement
  shares the same two models.
- **Transect.** `image_metadata.transect_id`, the flight line an image was taken on,
  numbered from 0 within its survey, `-1` for none. Exposed as `NO_TRANSECT` in the model.
- **Canonical DDL.** `docs/database/schemas/airial1-2.sql`, the full schema as it stands
  after the last migration. `atlas.sum` covers the migration directory.
- **Schema graph.** `object_models/schema_graph.py` gains the `proposal_generations` to
  `active_measurements` and `active_measurements` to `surveys` edges, so parent-scoped
  queries on generations resolve.

**Invariants.**
- `(active_measurement_id, generation)` is unique.
- `reviewed_area_ids`, `raw` and `proposal` are the same non-zero length; the request model
  rejects anything else before it reaches the database.
- Every foreign key in the three schemas is `DEFERRABLE`, matching the rest of the DDL.

## 4. Edge Cases

| Scenario | Expected behaviour |
| :--- | :--- |
| Measurement deleted | Its generations cascade away. |
| Regression model deleted | `model_id` on its generations becomes `NULL`; the vectors stay. |
| Unit deleted from the middle of the list | Neighbours' pointers to it become `NULL`; nothing else changes. |
| Same generation inserted twice | Unique violation from the database. |
| Vectors of differing length, or empty | `ValidationError` from `CreateProposalGenerationReq`. |
| Metadata created without `transect_id` | Stored as `-1`. |
| Metadata created with `transect_id` | Stored as given. |
| Fresh bootstrap (`bootstrap-dev.compose.yml`) | Loads `airial1-2.sql` and produces the same catalog as the migration chain. |
| Dev restore (`development.compose.yml`) | The regenerated `local_db/pct_b` restores to the same catalog, with the same sample rows as before. |

## 5. Acceptance Criteria

Verified locally on 2026-11-03.

**Migrations, DDL and dump agree.** Checked by applying the migration chain and the DDL to
two fresh PostGIS databases and diffing their column, constraint, index and enum catalogs,
then restoring the regenerated dump into a third and diffing it the same way.
- [x] `atlas migrate validate` passes on `local_db/migrations`.
- [x] Migration chain and `airial1-2.sql` produce identical catalogs (0 differing lines).
- [x] The regenerated `local_db/pct_b` restores cleanly and matches the DDL catalog. It was
      built by restoring the previous dump, applying only the three migrations, and dumping
      again, so it carries the same sample rows (5,723 images, 49 reviewed areas,
      46,988 predictions) and stays at 2.9 MB.
- [x] `bootstrap-dev.compose.yml` mounts `airial1-2.sql`; no file references `airial1-1.sql`.

**Object models.** Exercised directly against the sample database inside one rolled-back
transaction. 10 of 10 checks passed.
- [x] `core.proposal_generations` has the planned columns; `transect_id` defaults to `-1`;
      linked-list keys reference `am_unit_id` with `ON DELETE SET NULL`; the model-id
      uniqueness is gone.
- [x] The schema graph finds `proposal_generations` to `surveys` through the measurement.
- [x] `ProposalGeneration._create` returns the stored row with vectors in order, no SpiceDB
      updates; `serialize()` is JSON-ready; a duplicate generation raises `UniqueViolation`;
      mismatched vector lengths fail validation.
- [x] `ImageMetadata._create` stores `transect_id`, defaulting to `NO_TRANSECT`.

**Suite.** `uv run pytest testing/` against the local database: 22 passed.

**Style.** `py_compile` passes on the changed files; no added Python line exceeds 80 columns
other than the file's divider comments.
