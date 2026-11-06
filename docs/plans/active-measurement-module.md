# Feature Specification: Active Measurement Module

Branch `active-measurement-module`, stacked on `ais-package` until that merges, then
rebased onto `origin/indev`. Part of the series in
[active-measurement-rebuild.md](active-measurement-rebuild.md).

## 1. Overview

This PR lands the measurement workflow end to end: tiles are cut, a measurement is
created, proposal generations are posted and stored as rows, tiles are served one at a time
with the detector's boxes drafted on them, the reviewer submits them in the new Abundance
Estimation view, and the estimate is replayed from the review log on every request. No
process holds state: the serving state sits in Valkey as msgpack and is rebuilt from
PostgreSQL whenever it is missing. The survey map and the abundance terms come in the PR
after this one; here the estimate is a count, an interval and a density.

## 2. Goals

**User-facing.**
- A reviewer can start a survey's abundance estimation from the dashboard or the nav,
  review tiles one at a time with the detector's boxes drafted, and watch the running
  estimate and its interval tighten.
- The page says what phase the review is in, when the detection check ends, and why
  reviewing is not possible yet when the survey is not prepared. The count and its
  interval are withheld during the detection check, whose draws sit on tiles where the
  detector fired so the interval collapses without saying anything about the rest of the
  survey, and until `figures_from` on the estimate, the larger of the stop rule's minimum sample
  and 1% of the tiles (`SHOW_FRACTION`): before that, one animal in a tile the proposal
  thought empty moves the count by hundreds.

**Engineering.**
- Proposal generations are rows in `core.proposal_generations`; posting the same
  generation twice is a 409 from the unique constraint.
- The ground area of the units' images, the union of thousands of footprints, takes
  seconds to compute and is fixed for a measurement, so the estimate route computes it
  once under its own statement timeout and keeps it under `am_area_<uuid>`.
- The serving state is one msgpacked `MeasurementState` under `am_state_<uuid>` in Valkey,
  written on a miss and after each new generation, dropped on finish, delete and reset.
- The estimator is rebuilt from the stored proposals and the review log on every request,
  so every gunicorn worker serves the same next unit and reports the same estimate.
- Nothing at module level changes between requests. No S3 for proposals or state; S3 holds
  only the tile crops, which are images.
- One detection score constant, `DRAFT_THRESHOLD`, exported for the survey map PR. The
  threshold a survey's map draws estimated detections at is the lowest score among the
  boxes placed to fill the gap between the annotated count and the estimate, which a new
  survey does not have yet. Until the survey map PR supplies the live value, boxes are
  drafted at 0.95, a round figure near PR527's 0.984. `next-unit` echoes the threshold so
  the view's text follows it.
- The regressor's output under a proposal objective is relative, in (0, 1] with the
  likeliest tile at 1, not a count, so the view does not show it. `next-unit` reports the
  detector's expected count of the tile instead: the sum of its boxes' scores above the
  draft threshold, with the number of those boxes.
- The reviewer can hide the boxes (button or the B key) to search under them, and a red
  4 x 4 grid over the tile keeps them oriented while zoomed in. The ] and [ keys zoom to
  the grid's cells one after another, the current cell outlined and named in the header;
  Reset View returns to the whole tile.
- The predictions blueprint is registered, so the preparation tooling can post a
  detector's boxes; `Model._create` becomes one statement and writes `schema_id`, which
  the table requires (it raised on every model creation before).

## 3. Core Concepts

- **Tile.** A `ReviewedArea` of type `active measurement`, one cell of a 2 x 4 grid over an
  image, named `<image name>__r<row>c<col>`. Its crop is cut from the source image the first
  time it is served (`app/tile_crops.py`) and lives at its `ra_key`.
- **Measurement.** A row of `projectmanagement.active_measurements`: label, seed,
  retraining cadence, target interval, and the final count once finished. A measurement
  with a final count serves no more units.
- **Proposal generation.** One fit of the sampling proposal: unit order, expected count
  per unit, shaped vector. Generation 0 is posted before any review with `n_labels = 0`;
  each later generation must keep the unit order and be fitted on more reviewed units
  than the last. `check_next` in the `ais` package enforces this before the insert.
- **Serving state.** `MeasurementState.build` over the generations and the seed: the serving
  order (units drawn without replacement, proportional to the proposal in force) and the
  horizon at which a refit is due. Cached, never authoritative.
- **Unit.** A row of `core.am_units` for each served tile, linked to the unit before and
  after it, with the regressor's expected count and, once closed, the reviewer's count and
  the running estimate at that step.
- **Draft annotations.** The detector's boxes at or above `DRAFT_THRESHOLD` whose center
  lies on the tile, inserted as annotations of the measurement's label and type
  `active measurement` when the tile is served. What is on the tile when it is marked
  reviewed is its count.
- **Estimator replay.** `Estimator.replay(unit_ids, proposals, log, seed)` over the reviewed
  units in serving order. Run at each stop-rule check and for the live estimate.
- **Phases.** Under generation 0's sharpened proposal (`alpha > 1`) the first units are
  the detection check; the generation that follows opens the full review.
- **Stop rule.** Every `CHECK_EVERY` units (or the cadence, capped at 100) the estimator is
  replayed and the reviewed units are closed with their running estimate. The measurement
  finishes when the relative interval has stayed at or below target for `PERSISTENCE`
  units after a minimum sample, or when `LAST_UNITS` tiles remain.
- **Reset tool.** `tools/reset_measurement.py` removes a survey's measurement, generations,
  units, draft annotations and cache keys in one transaction, optionally the tiles and
  their crops too. Test stack only for the latter.

**Invariants.**
- `next_unit` takes an advisory transaction lock per measurement; a concurrent request waits
  and then sees the pending unit.
- The stored units always equal a prefix of the serving order; a mismatch is a 409.
- A served but unreviewed unit is served again; no unit is skipped.

## 4. Edge Cases

| Scenario | Expected behaviour |
| :--- | :--- |
| `next-unit` before generation 0 | 409: no proposal; post generation 0 first. |
| Generation 0 posted twice | 409 from the unique constraint; the first stays. |
| Generation posted out of order or with fewer labels | 409 from `check_next`; nothing stored. |
| Valkey restarted mid-measurement | The next `load` rebuilds the state from the rows; the serving order is identical because it depends only on the rows and the seed. |
| Two workers serve `next-unit` at once | The advisory lock serialises them; both return the same pending unit. |
| Reviewer submits a tile with no boxes | Counted as zero; the next unit is served. |
| Refit due (cadence reached, no new generation yet) | 409 waiting for the refit; the view polls every five seconds. |
| Tiles exhausted | The measurement finishes with the estimate so far; `next-unit` returns 204 and the cache keys are dropped. |
| `create_tiles` on images that already have tiles | Skipped; the survey's tiles are returned. |
| `create_tiles` with `image_ids` | Only those images are cut. |
| Measurement deleted | Generations and units cascade; the cache keys are dropped. |
| Tile crop missing in S3 | Cut from the source image on first serve; a second serve finds it. |
| Source image missing in S3 | 409 naming the image; the unit stays pending and is served again once the image is uploaded, never skipped. |
| Estimate requested without a measurement | 200 with status `not prepared` and null figures; the page polls it as data. |
| Model created through the API | One statement with two CTEs; the row carries its schema and project link. |
| Estimate requested without a proposal | `waiting for proposal` with null figures, not an error. |

## 5. Acceptance Criteria

**Backend, in the API container against the sample database.** Verified 2026-11-05, 20 of
21 checks passed; the one failure was in the check script (a stale measurement object),
not the code, and is fixed. The check script creates
a measurement on survey 1, cuts tiles for six images, posts generation 0, serves and
submits units through the module functions and the proposal store with the real Valkey and
PostgreSQL, and cleans up with the reset tool's own functions.
- [x] Tiles: 48 cut for six images; a second call cuts none.
- [x] `next_unit` without a proposal raises the 409; the posted generation is one row;
      posting it again raises the 409.
- [x] The first unit is the first of the serving order; it is served again until reviewed;
      its draft annotations equal the detector's boxes on it above the threshold.
- [x] Ten reviewed units follow the serving order and form a linked list.
- [x] The live estimate reports `measuring`, ten reviewed, a count inside its interval.
- [x] Dropping `am_state_<uuid>` mid-measurement rebuilds an identical state and estimate.
- [x] Serving to exhaustion finishes the measurement with a final count; every reviewed
      unit carries a running estimate; release drops the key.
- [ ] The estimate reports `finished` afterwards (rerun pending after the script fix).
- [x] The reset tool leaves zero measurements, generations, units, tiles and draft
      annotations, and the survey's status is restored.

**Real survey load, 2026-11-06.** The cluster's preparation tool
(`abundance.active_count.prepare_from_artifacts`) pushed the PR527 centennial artifacts
into the local stack through the API: 4,772 footprints and metadata rows with transects,
the October detector and its 18,193 boxes, 38,176 tiles, the measurement (seed 6, frozen,
target 10%), and generations 0 and 1 (the detection check, then the full review's
proposal from the cluster's own frozen run). Afterwards the survey reads `ready for
measurement`, the status endpoint reports all five steps done, and the estimate reports
`measuring` in the detection check with a 50-unit switch.

**Tests, `airial_api/testing/test_active_measurements.py`.** In the shape of the
existing `test_images.py`: the `APITester` fixtures, the sample database with every test
rolled back, S3 mocked, the tester account. The survey's own measurement rows are deleted
inside the transaction first, so the tests see the survey as the sample database ships it.
- [x] Status and estimate without a measurement, and for an unknown survey.
- [x] The measurement row: create (schema and 400), get by id and uuid, 404, update, delete
      with its cache keys dropped; status and estimate with a measurement and no proposal.
- [x] Tiles: cut once for one image, the listing with bounds and grid names.
- [x] Proposal generations: the summary returned and listed, the row's vectors, the 409 on
      a duplicate and on a changed unit order, a second generation.
- [x] Serving: a tile withheld with a 409 when its source image is not in the bucket; the
      loop with the image seeded (the same unit until reviewed, its crop cut, the boxes
      drafted, the next unit, the units listing, the estimate's phase and masking fields);
      review to exhaustion finishing with a count and the state dropped.
- [x] The proposal store rebuilding the state from the rows and caching the area once.
- [x] Module functions: the detector's expectation per tile, the empty estimate, the
      preparation steps; the prediction routes (bulk get, by id, 404, create, 400).
- [x] 50 tests pass with `test_images.py`, run from the API image on the host network:
      `podman run --rm --network host --add-host prong_dev_valkey:127.0.0.1 -v ./airial_api:/app -w /app --entrypoint "" localhost/airial-core-infrastructure_pronghorn-api-dev:latest .venv/bin/python -m pytest testing -q`
      (the test env names the database at localhost and Valkey by its container name).

**Frontend.**
- [x] `vue-tsc --build` passes in the webapp container.
- [x] The Abundance Estimation view loads for the sample survey and shows the preparation
      steps; the status endpoint answers 200 and the estimate 404 until a measurement
      exists, which the view reports as not yet prepared.

**Style.**
- [x] `py_compile` passes on every changed Python file; the app creates with all sixteen
      measurement routes registered.
- [x] No added Python line exceeds 80 columns other than divider comments and route
      docstrings.
