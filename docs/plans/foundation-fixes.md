# Feature Specification: Foundation Fixes

Branch `pr0-database-layer` off `origin/indev`. Part of the series in
[active-measurement-rebuild.md](active-measurement-rebuild.md).

## 1. Overview

This PR lands the small data-layer fixes the active measurement work depends on, with no
measurement code in them: a crop-type filter so measurement tiles never reach the crop
verifier and three one-line object-model corrections. The only external surface change is
an optional `type` query parameter on `GET /api/v1/reviewed-area`, which the crop verifier
view now sends.

## 2. Goals

**User-facing.**
- Annotators in the crop verifier see only auto-cropper crops, never abundance tiles.

**Engineering.**

## 3. Core Concepts

- **Reviewed area.** A crop of an image stored in `core.reviewed_area`, with a `type` of
  either `auto cropper` or `active measurement` (`core.activity_type`).
- **Tile.** A reviewed area of type `active measurement`, cut on a grid by the measurement
  workflow (later PRs). Tiles share the table with auto-cropper crops.
- **Crop verifier.** The human review queue for auto-cropper crops.
- **Scope.** The dict of column equalities the paginated getters append to `WHERE`.

**Invariants.**
- A reviewed area's `type` never changes after insert.
- The verifier's available-crop query, its count query, and the list endpoint apply the same
  type filter, so the counts a user sees match the queue they are served.

## 4. Edge Cases

| Scenario | Expected behaviour |
| :--- | :--- |
| Survey has only tiles, no auto-cropper crops | Verifier shows the empty state; count is 0. |
| `type` omitted on the list endpoint | No type filter; both kinds returned (backwards compatible). |
| `type` given with an unknown value | Pydantic rejects it with 400 before the query runs. |
| Footprint insert with `null` GeoJSON or GCPs | Explicit `::text` / `::jsonb` casts resolve the parameter types; `NULL` is inserted. |
| Prediction insert | `class_row` is set before execute, so `fetchone` returns a `Prediction`, not a tuple. |
| Unit `serialize()` | `from_attributes=True` lets the response model read the dataclass. |
| Expired session or revoked access | Unchanged; handled by the decorators before any query. |

## 5. Acceptance Criteria

Verified locally on 2026-11-02 with `docs/plans/checks/verify_foundation_fixes.py`, run from
`airial_api/` with `uv run python ../docs/plans/checks/verify_foundation_fixes.py` against
the sample database in the `prong_gres` container. The script exercises the module functions and object models directly
inside one transaction and rolls it back, so it needs no API session and leaves the data
untouched. Result: 8 of 8 passed.

**Verifier filtering.** Sample survey 1 has 32 unreviewed auto-cropper crops and 38,151
unreviewed tiles.
- [x] The verifier count returns 32; the queue serves only `auto cropper` crops.
- [x] The paginated list without `type` totals 38,183 (both kinds); with
      `type='auto cropper'` it totals 32.
- [x] `RAQuery(type="bogus")` fails validation ("Input should be 'auto cropper' or
      'active measurement'"), which the route surfaces as 400.

**Object models.**
- [x] Prediction creation returns a `Prediction` instance.
- [x] Footprint creation with `footprint=None`, `footprint_metadata=None`, `gcps=[]` succeeds.
- [x] `AmUnit.serialize()` returns a 17-key dict.

**Not verified locally.** The HTTP layer itself (decorators, 400 mapping, the Vue view sending
`type`) was not exercised end to end, because the API container is not running and the
checks avoid creating a session. Covered by `vue-tsc` and by the validation check above.

**Style and tooling.**
- [x] No added Python line exceeds 80 columns (0 over).
- [x] `py_compile` passes on all changed files.
- [x] `vue-tsc --build` passes in the `prong_dev_webapp` container.
