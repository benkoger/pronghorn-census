# Active measurement serving state: cached in Valkey, rebuilt from PostgreSQL
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# The durable record of a measurement is its rows in core.proposal_generations
# (database.modules.activemeasurement reads and writes them). This module is
# the cache in front of them, in the shape of the user loader in routers/users:
# read the key, fall back to the database, write the key back.
#
#   am_state_<measurement uuid>   msgpacked MeasurementState: the unit order,
#                                 the serving order and the latest expected
#                                 counts. Rebuilt from the rows on a miss.
#   am_terms_<measurement uuid>   msgpacked SurveyTerms of the abundance, once
#                                 posted. The measurement row holds them;
#                                 rebuilt from it on a miss.
#   am_area_<measurement uuid>    msgpacked float: the ground area of the
#                                 units' images, the union of their
#                                 footprints. Fixed for a measurement and
#                                 seconds to compute, so computed once.
#   am_threshold_<measurement uuid>
#                                 msgpacked float: the detector score the
#                                 current generation drafts boxes at. Dropped
#                                 when a generation is posted.
#   am_boxes_<measurement uuid>   msgpacked PlacedBoxes: the detector's boxes
#                                 at that score, placed on the ground. Seconds
#                                 to place, so placed once per generation.
#
# Nothing is held in the process: every worker reads the same keys and the
# same rows.
# ---------------------------------------------------------------------------------------------------------------------------

import numpy as np
from msgpack import packb, unpackb

from ais import MeasurementState, PlacedBoxes, Proposal, SurveyTerms
from app.extensions import base, cache
from database.modules import abundance, activemeasurement
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
)

# ---------------------------------------------------------------------------------------------------------------------------

# A Flask-Caching timeout of 0 never expires; the keys are dropped by release.
NO_EXPIRY = 0


def _state_key(measurement: ActiveMeasurement) -> str:
    return f"am_state_{measurement.uuid}"


def _terms_key(measurement: ActiveMeasurement) -> str:
    return f"am_terms_{measurement.uuid}"


def _area_key(measurement: ActiveMeasurement) -> str:
    return f"am_area_{measurement.uuid}"


def _threshold_key(measurement: ActiveMeasurement) -> str:
    return f"am_threshold_{measurement.uuid}"


def _boxes_key(measurement: ActiveMeasurement) -> str:
    return f"am_boxes_{measurement.uuid}"


# ---------------------------------------------------------------------------------------------------------------------------


def load(measurement: ActiveMeasurement) -> MeasurementState | None:
    """Returns the measurement's serving state, or None without a proposal.

    Reads the cache first and rebuilds the state from the stored generations
    on a miss, writing it back for the next request.
    """
    if (cached := cache.get(_state_key(measurement))) is not None:
        return MeasurementState.from_cache(cached)

    proposals = base.execute(activemeasurement.get_proposals, measurement)
    state = MeasurementState.build(
        proposals, measurement.random_seed, measurement.retraining_cadence
    )
    if state is not None:
        cache.set(_state_key(measurement), state.to_cache(), timeout=NO_EXPIRY)

    return state


def vectors(
    measurement: ActiveMeasurement, state: MeasurementState
) -> list[np.ndarray]:
    """Returns each generation's proposal vector for `state`, oldest first."""
    proposals = base.execute(activemeasurement.get_proposals, measurement)
    return [p.proposal for p in proposals[: len(state.generations)]]


def save(measurement: ActiveMeasurement, proposal: Proposal) -> Proposal:
    """Stores the next generation and refreshes the serving state."""
    base.execute(activemeasurement.create_generation, measurement, proposal)
    cache.delete(_state_key(measurement))
    cache.delete(_threshold_key(measurement))
    cache.delete(_boxes_key(measurement))
    load(measurement)
    return proposal


def load_terms(measurement: ActiveMeasurement) -> SurveyTerms | None:
    """Returns the survey terms of the abundance, or None when not posted.

    Reads the cache first and the measurement row on a miss, writing the
    terms back for the next request.
    """
    if (cached := cache.get(_terms_key(measurement))) is not None:
        return SurveyTerms.from_cache(cached)
    if measurement.terms is None:
        return None

    terms = SurveyTerms(**measurement.terms)
    cache.set(_terms_key(measurement), terms.to_cache(), timeout=NO_EXPIRY)
    return terms


def save_terms(
    measurement: ActiveMeasurement, terms: SurveyTerms
) -> SurveyTerms:
    """Stores the survey terms on the measurement, replacing any before."""
    base.execute(abundance.set_terms, measurement, terms)
    cache.set(_terms_key(measurement), terms.to_cache(), timeout=NO_EXPIRY)
    return terms


def load_boxes(
    measurement: ActiveMeasurement, state: MeasurementState
) -> PlacedBoxes:
    """Returns the detector's boxes at the draft threshold, on the ground.

    Placed on a miss and kept until the next generation is posted, since the
    threshold changes with it.
    """
    if (cached := cache.get(_boxes_key(measurement))) is not None:
        return PlacedBoxes.from_cache(cached)

    boxes = base.execute(
        abundance.place_boxes, measurement, load_threshold(measurement, state)
    )
    cache.set(_boxes_key(measurement), boxes.to_cache(), timeout=NO_EXPIRY)
    return boxes


def load_area(
    measurement: ActiveMeasurement, state: MeasurementState
) -> float | None:
    """Returns the ground area in square meters the units were cut from.

    Computed from the footprints on a miss and kept for the measurement.
    """
    if (cached := cache.get(_area_key(measurement))) is not None:
        return float(unpackb(cached))

    area = base.execute(
        activemeasurement.get_measured_area,
        measurement.survey_id,
        state.reviewed_area_ids,
    )
    if area is not None:
        cache.set(_area_key(measurement), packb(area), timeout=NO_EXPIRY)
    return area


def load_surveyed_area(
    measurement: ActiveMeasurement, state: MeasurementState
) -> float | None:
    """Returns the area the estimate's density is over, in square meters.

    The surveyed area of the terms once they are posted, else the cached
    union of the units' footprints (`load_area`).
    """
    if (terms := load_terms(measurement)) is not None:
        return terms.surveyed_area_m2
    return load_area(measurement, state)


def load_threshold(
    measurement: ActiveMeasurement, state: MeasurementState
) -> float:
    """Returns the detector score the current generation drafts boxes at.

    The score at which the detector's box count over the units equals the
    generation's expected total, the sum of its regressor counts. Computed on
    a miss and kept until the next generation is posted.
    """
    if (cached := cache.get(_threshold_key(measurement))) is not None:
        return float(unpackb(cached))

    threshold = base.execute(
        activemeasurement.draft_threshold, measurement, float(state.raw.sum())
    )
    cache.set(_threshold_key(measurement), packb(threshold), timeout=NO_EXPIRY)
    return threshold


def release(measurement: ActiveMeasurement) -> None:
    """Drops the cached state, terms, area, threshold and boxes once the
    measurement has finished."""
    cache.delete(_state_key(measurement))
    cache.delete(_terms_key(measurement))
    cache.delete(_area_key(measurement))
    cache.delete(_threshold_key(measurement))
    cache.delete(_boxes_key(measurement))
