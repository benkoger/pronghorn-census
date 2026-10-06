# Storage of active measurement proposals: vectors in S3, a compact serving state in the cache
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# A proposal generation is one .npz object under
#   active_measurements/<active measurement uuid>/proposals/<generation>.npz
#
# The cache holds one MeasurementState per running measurement: the unit order, the serving order
# and the latest regressor counts. Its size depends on the number of units only, never on the
# number of generations, and it is dropped when the measurement finishes (release).
#
# The vectors the estimator needs are read from S3 once per process and generation (vectors).
#
# The survey terms of the abundance are one .npz object under
#   active_measurements/<active measurement uuid>/terms.npz
# held in the cache while the measurement runs. Their size does not depend on the survey.
#
# The detector's boxes placed on the ground are one .npz object under
#   active_measurements/<active measurement uuid>/boxes.npz
# read from S3 once per process and never held in the cache.
# ---------------------------------------------------------------------------------------------------------------------------

from typing import Optional
from uuid import UUID

import numpy as np
from botocore.exceptions import ClientError
from flask import current_app

from ais import MeasurementState, PlacedBoxes, Proposal, SurveyTerms, check_next
from app.extensions import cache, s3
from database.errors import MeasurementBlocked
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
)

# ---------------------------------------------------------------------------------------------------------------------------

S3_PREFIX = "active_measurements"
NO_EXPIRY = 0
STATE_VERSION = 4  # raised when MeasurementState changes, so an older cached state is not read
TERMS_VERSION = 2
MEASUREMENTS_IN_PROCESS = 4

_proposals: dict[UUID, list[Proposal]] = {}  # this process's copy of the generations read so far
_boxes: dict[UUID, PlacedBoxes] = {}  # this process's copy of the placed boxes read so far

# ---------------------------------------------------------------------------------------------------------------------------


def _key(measurement: ActiveMeasurement, generation: int) -> str:
    return f"{S3_PREFIX}/{measurement.uuid}/proposals/{generation:04d}.npz"


def _cache_key(measurement: ActiveMeasurement) -> str:
    return f"am_state_{STATE_VERSION}_{measurement.uuid}"


def _terms_key(measurement: ActiveMeasurement) -> str:
    return f"{S3_PREFIX}/{measurement.uuid}/terms.npz"


def _boxes_key(measurement: ActiveMeasurement) -> str:
    return f"{S3_PREFIX}/{measurement.uuid}/boxes.npz"


def _terms_cache_key(measurement: ActiveMeasurement) -> str:
    return f"am_terms_{TERMS_VERSION}_{measurement.uuid}"


def _read(measurement: ActiveMeasurement, up_to: Optional[int] = None) -> list[Proposal]:
    """
    Returns the measurement's generations, oldest first, reading from S3 those this process
    does not hold yet: the first `up_to`, or every stored one. Generations are numbered without
    gaps, so they are fetched in order until one is missing.
    """
    bucket = current_app.config["BUCKET_NAME"]
    proposals = _proposals.pop(measurement.uuid, [])

    while up_to is None or len(proposals) < up_to:
        try:
            obj = s3.get_object(Bucket=bucket, Key=_key(measurement, len(proposals)))
        except ClientError as error:
            if error.response["Error"]["Code"] in ("NoSuchKey", "404"):
                break
            raise
        proposals.append(Proposal.from_bytes(obj["Body"].read()))

    _proposals[measurement.uuid] = proposals
    while len(_proposals) > MEASUREMENTS_IN_PROCESS:
        _proposals.pop(next(iter(_proposals)))

    return proposals if up_to is None else proposals[:up_to]


def _build(measurement: ActiveMeasurement, proposals: list[Proposal]) -> Optional[MeasurementState]:
    return MeasurementState.build(
        proposals, measurement.random_seed, measurement.retraining_cadence
    )


# ---------------------------------------------------------------------------------------------------------------------------


def load(measurement: ActiveMeasurement) -> Optional[MeasurementState]:
    """Returns the measurement's serving state, or None when it has no proposal yet."""
    state = cache.get(_cache_key(measurement))

    if state is None:
        state = _build(measurement, _read(measurement))
        if state is not None:
            cache.set(_cache_key(measurement), state, NO_EXPIRY)

    return state


def vectors(measurement: ActiveMeasurement, state: MeasurementState) -> list[np.ndarray]:
    """Returns the proposal vector of every generation of `state`, oldest first."""
    return [p.proposal for p in _read(measurement, up_to=len(state.generations))]


def save(measurement: ActiveMeasurement, proposal: Proposal) -> Proposal:
    """Stores the next generation in S3 and refreshes the cached serving state."""
    stored = _read(measurement)

    try:
        check_next(stored, proposal)
    except ValueError as error:
        raise MeasurementBlocked(str(error))

    s3.put_object(
        Bucket=current_app.config["BUCKET_NAME"],
        Key=_key(measurement, proposal.generation),
        Body=proposal.to_bytes(),
        ContentType="application/octet-stream",
    )

    stored.append(proposal)
    cache.set(_cache_key(measurement), _build(measurement, stored), NO_EXPIRY)
    return proposal


def load_terms(measurement: ActiveMeasurement) -> Optional[SurveyTerms]:
    """Returns the survey terms of the measurement's abundance, or None when none are stored."""
    data = cache.get(_terms_cache_key(measurement))

    if data is None:
        try:
            obj = s3.get_object(
                Bucket=current_app.config["BUCKET_NAME"], Key=_terms_key(measurement)
            )
        except ClientError as error:
            if error.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return None
            raise
        data = obj["Body"].read()
        cache.set(_terms_cache_key(measurement), data, NO_EXPIRY)

    try:
        return SurveyTerms.from_bytes(data)
    except (KeyError, ValueError):  # stored in an older layout
        return None


def save_terms(measurement: ActiveMeasurement, terms: SurveyTerms) -> SurveyTerms:
    """Stores the survey terms in S3, replacing any stored before, and refreshes the cache."""
    data = terms.to_bytes()

    s3.put_object(
        Bucket=current_app.config["BUCKET_NAME"],
        Key=_terms_key(measurement),
        Body=data,
        ContentType="application/octet-stream",
    )

    cache.set(_terms_cache_key(measurement), data, NO_EXPIRY)
    return terms


def load_boxes(measurement: ActiveMeasurement) -> Optional[PlacedBoxes]:
    """Returns the detector's boxes placed on the ground, or None when none are stored."""
    if (boxes := _boxes.get(measurement.uuid)) is not None:
        return boxes

    try:
        obj = s3.get_object(Bucket=current_app.config["BUCKET_NAME"], Key=_boxes_key(measurement))
    except ClientError as error:
        if error.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        raise

    try:
        boxes = PlacedBoxes.from_bytes(obj["Body"].read())
    except (KeyError, TypeError, ValueError):  # stored in an older layout
        return None
    return _remember(measurement, boxes)


def save_boxes(measurement: ActiveMeasurement, boxes: PlacedBoxes) -> PlacedBoxes:
    """Stores the placed boxes in S3, replacing any stored before."""
    s3.put_object(
        Bucket=current_app.config["BUCKET_NAME"],
        Key=_boxes_key(measurement),
        Body=boxes.to_bytes(),
        ContentType="application/octet-stream",
    )
    return _remember(measurement, boxes)


def _remember(measurement: ActiveMeasurement, boxes: PlacedBoxes) -> PlacedBoxes:
    _boxes.pop(measurement.uuid, None)
    _boxes[measurement.uuid] = boxes
    while len(_boxes) > MEASUREMENTS_IN_PROCESS:
        _boxes.pop(next(iter(_boxes)))
    return boxes


def release(measurement: ActiveMeasurement) -> None:
    """Drops the serving state and this process's generations once the measurement has finished."""
    cache.delete(_cache_key(measurement))
    cache.delete(_terms_cache_key(measurement))
    _proposals.pop(measurement.uuid, None)
    _boxes.pop(measurement.uuid, None)
