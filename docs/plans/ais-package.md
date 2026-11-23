# Feature Specification: The `ais` Package

Branch `ais-package` off `origin/indev`. Part of the series in
[active-measurement-rebuild.md](active-measurement-rebuild.md).

## 1. Overview

This PR adds `airial_api/ais/`, the adaptive importance sampling estimator and the data types
the active measurement feature works with, as a pure numpy package. It imports nothing from
Flask, boto3 or the database layer and holds no state between calls. Every type that a later
PR will keep in Valkey serialises with msgpack through `to_cache` / `from_cache`, following
the pattern on the base object model. Nothing on `indev` imports it yet; the active
measurement module and the survey map PRs do.

## 2. Goals

**User-facing.**
- None directly. This is the arithmetic the measurement PRs are built on.

**Engineering.**
- The estimator can be rebuilt from stored proposals and the review log on every request, so
  no process holds a measurement in memory.
- Proposals, serving state, survey terms and placed boxes round-trip through msgpack bytes
  that Valkey can hold and any gunicorn worker can read.
- The vendored research arithmetic in `ais.py` and `importance_sampling_update.py` is carried
  verbatim.

## 3. Core Concepts

- **Proposal** (`proposal.py`). One generation of the sampling proposal: `reviewed_area_ids`
  fixes the unit order, `raw` is the regressor's expected count per unit, `proposal` the shaped
  vector units are drawn from, with `n_labels`, `model_id` and `alpha`. `check_next` validates
  a generation against the stored ones.
- **Estimator** (`estimator.py`). The AIS estimator over one survey's units, wrapping the
  vendored `AIS` and `ImportanceSamplingUpdate`. `record` appends a reviewed unit;
  `estimate` returns the count and its standard error; `replay` rebuilds an identical
  estimator from the proposals and the review log.
- **MeasurementState** (`schedule.py`). What serving a unit needs and no more: the unit order,
  the generations without their vectors, the draw order as far as the stored generations
  determine it, and the latest expected counts. `draw_order`, `generation_at` and `horizon`
  compute it from the proposals.
- **SurveyTerms and PlacedBoxes** (`abundance.py`). The terms that turn a count into an
  abundance over the habitable area, and the detector's boxes placed on the ground.
  `overall_abundance` reports the abundance with each source of uncertainty.
- **Representation and overlap** (`representation.py`, `overlap.py`). The spread of the
  density across transects, and the weight of an animal seen in more than one image.
- **Cache format.** `to_cache` returns `packb` of a plain dict: arrays as lists, optional
  fields as `None`, nested dataclasses as dicts. `from_cache` unpacks and passes the dict to
  the constructor, whose `__post_init__` coerces lists back to arrays.

**Invariants.**
- `from_cache(x.to_cache())` equals `x` for every cached type, arrays included.
- A draw depends on the seed, the proposal in force and the units already drawn, never on the
  counts, so a replayed estimator agrees with the live one on the next unit.
- `ais.py` and `importance_sampling_update.py` are byte-identical to the research code.

## 4. Edge Cases

| Scenario | Expected behaviour |
| :--- | :--- |
| Proposal with `model_id` or `alpha` unset | Cached as `None`; restored as `None`. |
| Vectors of differing length, or empty | `ValueError` from `Proposal.__post_init__`. |
| Generation out of sequence or `n_labels` not increasing | `ValueError` from `check_next`. |
| `SurveyTerms` with no draws | Empty arrays round-trip as empty float arrays. |
| Empty `PlacedBoxes` | Round-trips with length 0. |
| `MeasurementState.build` with no proposals | Returns `None`. |
| Estimator asked for a unit when none remain | `RuntimeError("pool exhausted")`. |
| Recording a unit twice | `ValueError`. |

## 5. Acceptance Criteria

Verified locally on 2026-11-04 from `airial_api/` with no app context and no services running.

- [x] `python -c "import ais"` succeeds and loads no Flask, boto3, psycopg, `database` or
      `app` module.
- [x] `EstimatorCache` does not exist; `__all__` does not name it.
- [x] No `to_bytes` / `from_bytes`, no `np.load` / `savez`, no `io` import remains in the
      package.
- [x] `Proposal`, `SurveyTerms`, `PlacedBoxes` and `MeasurementState` each equal their
      `from_cache(to_cache())` round-trip, including unset optionals, empty arrays and integer
      id arrays; `MeasurementState` restores `Generation` instances and its `switch_at` and
      `model_count` answers are unchanged.
- [x] `draw_order` is deterministic for a seed; `Estimator.replay` reproduces the live
      estimator's estimate and next unit.
- [x] `py_compile` passes on every file in the package; no added line exceeds 80 columns
      other than divider comments.
