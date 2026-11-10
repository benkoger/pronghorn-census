# Active Measurement Specialized Database Operations
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# The state of an active measurement is a pure function of what is stored: the
# seed on the measurement, the reviewed units with their annotation counts, and
# the proposal generations. The caller hands in the compact serving state and a
# way to load the generations' vectors.
#
#   get_active_measurement(survey)    -> the survey's current measurement
#   get_preparation(survey)           -> what has been prepared so far
#   next_unit(measurement, state, ...)     -> Keyring of the next reviewed area
#   live_estimate(measurement, state, ...) -> running count and interval so far
#   create_tiles(survey)              -> the tiles, as reviewed areas of type
#                                        'active measurement'
#
# Serving a unit is a lookup in the serving order. The estimator is rebuilt from
# the review log where its value is needed: at the stop-rule checks and for the
# live estimate. Nothing is held between requests, so every worker agrees.
#
# The review has two phases. Generation 0 is sharpened (the expected count to
# the fourth), so the first units are the ones most likely to hold animals and
# the reviewer confirms the detector's boxes: the detection check. The
# generation that follows is the expected count shaped g^0.5, under which every
# unit can be drawn and the reviewer looks for both false positives and false
# negatives: the full review. The estimator takes each change of proposal as it
# takes a refit.
#
# A unit is served with draft boxes: the detector's boxes on it, as annotations
# the reviewer keeps, moves or deletes, and adds to. What is on the unit when it
# is marked reviewed is its count, so a draft box left in place counts as
# confirmed.
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from math import ceil, isfinite
from typing import TYPE_CHECKING, Any, Callable
from uuid import UUID, uuid4

import numpy as np
import psycopg.sql as sql
from psycopg import Cursor
from psycopg.errors import UniqueViolation
from psycopg.rows import class_row, dict_row, tuple_row

from ais import Estimator, LogRow, MeasurementState, Proposal, check_next
from database.errors import MeasurementBlocked, ObjectNotFound
from database.object_models.base import Keyring, create_spice_update
from database.object_models.core.activity import ActivityType
from database.object_models.core.am_units import AmUnit, CreateAmUnitReq
from database.object_models.core.annotations import (
    Annotation,
    CreateAnnotationReq,
)
from database.object_models.core.proposal_generations import (
    CreateProposalGenerationReq,
    ProposalGeneration,
)
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
    UpdateActiveMeasurement,
)
from database.object_models.project_management.herd_units import HerdUnit
from database.object_models.project_management.models import Model
from database.object_models.user_management.users import User

if TYPE_CHECKING:
    from database.database import Database

# ---------------------------------------------------------------------------------------------------------------------------

# An image is cut into TILE_ROWS x TILE_COLS reviewed areas.
TILE_ROWS = 2
TILE_COLS = 4
# Folder of the tiles' crops in the bucket; a re-cut never serves a stale crop.
TILING = f"{TILE_ROWS}x{TILE_COLS}"
# Units between stop-rule checks when the proposal is frozen.
CHECK_EVERY = 50
# Units the interval must stay at or below target before stopping.
PERSISTENCE = 50
# Share of units reviewed before a stop is allowed.
MIN_FRACTION = 0.03
# Share of units reviewed before the count and interval are shown.
SHOW_FRACTION = 0.01
# Units the estimator needs left unreviewed.
LAST_UNITS = 2
# Equal-area projection the footprint areas are measured in.
AREA_SRID = 5072
# The footprint union's own statement timeout, in milliseconds.
AREA_TIMEOUT_MS = 120_000
SPICE_BATCH = 500
IMAGES_PER_STATEMENT = 250
NO_MODEL_ID = 0
# Detector boxes at or above the measurement's draft threshold are drafted
# onto a served unit. The threshold is the score at which the detector's box
# count over the units equals the regressor's expected total (`draft_threshold`
# below); it is kept per generation by `proposal_store.load_threshold`.
# A unit with no box at or above it is served clean.
NO_DRAFTS = 1.0
# The first units, drawn where the detector found animals.
DETECTION_CHECK = "detection check"
# Every unit after that.
FULL_REVIEW = "full review"
# The estimate's status for a survey that has no measurement yet.
NOT_PREPARED = "not prepared"
Z95 = 1.959963985

# The proposal vector of every generation, oldest first.
Vectors = Callable[[], list[np.ndarray]]

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class UnitState:
    """A served unit joined to its reviewed area and the annotations on it."""

    am_unit_id: int
    reviewed_area_id: int
    reviewed_area_uuid: UUID
    reviewed: bool
    human_count: int
    stored_human_count: int | None
    stored_count: float | None
    stored_ci_lower: float | None
    stored_ci_upper: float | None


# ---------------------------------------------------------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------------------------------------------------------


def get_active_measurement(
    cursor: Cursor[Any],
    db: "Database",
    survey_ids: Keyring,
) -> ActiveMeasurement:
    """Returns the survey's current (most recent) active measurement."""
    stmt = sql.SQL("""
        SELECT *
        FROM projectmanagement.active_measurements
        WHERE survey_id = %(survey_id)s
        ORDER BY active_measurement_id DESC
        LIMIT 1;
    """)

    cursor.row_factory = class_row(ActiveMeasurement)
    cursor.execute(stmt, {"survey_id": survey_ids.pkey})

    if not (measurement := cursor.fetchone()):
        raise ObjectNotFound("ActiveMeasurement", f"survey {survey_ids.uuid}")

    return measurement


def get_generations(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
) -> list[ProposalGeneration]:
    """Returns the measurement's stored proposal generations, oldest first."""
    stmt = sql.SQL("""
        SELECT *
        FROM core.proposal_generations
        WHERE active_measurement_id = %(active_measurement_id)s
        ORDER BY generation ASC;
    """)

    cursor.row_factory = class_row(ProposalGeneration)
    cursor.execute(
        stmt, {"active_measurement_id": measurement.active_measurement_id}
    )
    return cursor.fetchall()


def _proposal(row: ProposalGeneration) -> Proposal:
    """The stored row as the sampler's proposal."""
    return Proposal(
        generation=row.generation,
        n_labels=row.n_labels,
        reviewed_area_ids=list(row.reviewed_area_ids),
        raw=np.asarray(row.raw, dtype=float),
        proposal=np.asarray(row.proposal, dtype=float),
        model_id=row.model_id,
        alpha=row.alpha,
    )


def get_proposals(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
) -> list[Proposal]:
    """Returns the stored generations as proposals, oldest first."""
    return [_proposal(row) for row in get_generations(cursor, db, measurement)]


def detector_expectation(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    reviewed_area_id: int,
    threshold: float,
) -> tuple[float, int]:
    """The detector's expected count of a unit: the sum of its boxes' scores
    at or above `threshold`, and the number of those boxes.

    A box belongs to the unit its center lies on, as when it is drafted.
    """
    detector = get_detection_model(cursor, db, measurement.survey_id)
    stmt = sql.SQL("""
        SELECT COALESCE(SUM(p.score), 0.0), COUNT(*)
        FROM core.reviewed_area t
        JOIN core.predictions p ON p.image_id = t.image_id
        JOIN projectmanagement.labels l ON l.label = p.label
        WHERE t.reviewed_area_id = %(reviewed_area_id)s
          AND p.model_id = %(model_id)s
          AND l.label_id = %(label_id)s
          AND p.score >= %(threshold)s
          AND (p.box_tx + p.box_bx) / 2.0 >= t.area_tx
          AND (p.box_tx + p.box_bx) / 2.0 < t.area_bx
          AND (p.box_ty + p.box_by) / 2.0 >= t.area_ty
          AND (p.box_ty + p.box_by) / 2.0 < t.area_by;
    """)
    cursor.row_factory = tuple_row
    cursor.execute(
        stmt,
        {
            "reviewed_area_id": reviewed_area_id,
            "model_id": detector.model_id,
            "label_id": measurement.label_id,
            "threshold": threshold,
        },
    )
    total, n_boxes = cursor.fetchone() or (0.0, 0)
    return float(total), int(n_boxes)


def draft_threshold(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    expected_total: float,
) -> float:
    """The detector score at which its box count over the measurement's units
    equals the regressor's expected total.

    With `k` the expected total rounded to a count, the threshold is the k-th
    highest score among the detector's boxes of the measurement's label on
    the units' images, so exactly k boxes score at or above it (ties aside).
    `NO_DRAFTS` when k is zero; the lowest score when k exceeds the boxes.
    """
    k = int(round(expected_total))
    if k <= 0:
        return NO_DRAFTS

    detector = get_detection_model(cursor, db, measurement.survey_id)
    stmt = sql.SQL("""
        WITH scores AS (
            SELECT p.score
            FROM core.predictions p
            JOIN projectmanagement.labels l ON l.label = p.label
            WHERE p.model_id = %(model_id)s
              AND l.label_id = %(label_id)s
              AND p.image_id IN (
                  SELECT DISTINCT ra.image_id
                  FROM core.reviewed_area ra
                  JOIN core.images i ON i.image_id = ra.image_id
                  WHERE i.survey_id = %(survey_id)s AND ra.type = %(type)s
              )
        )
        SELECT COALESCE(
            (SELECT score FROM scores ORDER BY score DESC OFFSET %(offset)s LIMIT 1),
            (SELECT MIN(score) FROM scores)
        );
    """)
    cursor.row_factory = tuple_row
    cursor.execute(
        stmt,
        {
            "model_id": detector.model_id,
            "label_id": measurement.label_id,
            "survey_id": measurement.survey_id,
            "type": ActivityType.ACTIVE_MEASUREMENT,
            "offset": k - 1,
        },
    )
    row = cursor.fetchone()
    return float(row[0]) if row and row[0] is not None else NO_DRAFTS


def get_unit_states(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
) -> list[UnitState]:
    """Returns the served units in serving order, each with its count.

    The count is the number of annotations of the measurement's label on the
    unit's reviewed area.
    """
    stmt = sql.SQL("""
        SELECT
            u.am_unit_id,
            u.reviewed_area_id,
            ra.uuid AS reviewed_area_uuid,
            ra.reviewed_by_user_id <> 0 AS reviewed,
            (
                SELECT COUNT(*)
                FROM core.annotations_reviewed_area ara
                JOIN core.annotations a ON a.annotation_id = ara.annotation_id
                WHERE ara.reviewed_area_id = u.reviewed_area_id
                  AND a.label_id = %(label_id)s
            ) AS human_count,
            u.human_count AS stored_human_count,
            u.current_count AS stored_count,
            u.current_ci_lower AS stored_ci_lower,
            u.current_ci_upper AS stored_ci_upper
        FROM core.am_units u
        JOIN core.reviewed_area ra ON ra.reviewed_area_id = u.reviewed_area_id
        WHERE u.active_measurement_id = %(active_measurement_id)s
        ORDER BY u.relative_position ASC NULLS LAST, u.am_unit_id ASC;
    """)

    cursor.row_factory = dict_row
    cursor.execute(
        stmt,
        {
            "active_measurement_id": measurement.active_measurement_id,
            "label_id": measurement.label_id,
        },
    )
    return [UnitState(**row) for row in cursor.fetchall()]


def preparation_steps(status: dict) -> list[dict]:
    """The preparation steps of a survey, each with whether it is done.

    A step is done when its process has run; the sentences do not say how
    many images succeeded.
    """
    steps = [
        (
            "detections",
            "Detections",
            status["images_with_predictions"] > 0,
            "Predictions generated",
            "Predictions have not been generated yet",
        ),
        (
            "footprints",
            "Footprints",
            status["images_with_footprints"] > 0,
            "Images georeferenced",
            "Images have not been georeferenced yet",
        ),
        (
            "tiles",
            "Tiles",
            status["tiles"] > 0
            and status["georeferenced_images_without_tiles"] == 0,
            "Tiles cut",
            "Tiles have not been cut yet",
        ),
        (
            "measurement",
            "Measurement",
            status["measurement"] is not None,
            "Measurement created",
            "Measurement has not been created yet",
        ),
        (
            "proposal",
            "Sampling proposal",
            status["proposal_generations"] > 0,
            "Sampling proposal ready",
            "Waiting for the sampling proposal",
        ),
    ]

    return [
        {
            "key": key,
            "label": label,
            "done": done,
            "detail": said if done else unsaid,
        }
        for key, label, done, said, unsaid in steps
    ]


def get_preparation(
    cursor: Cursor[Any],
    db: "Database",
    survey_ids: Keyring,
) -> dict[str, Any]:
    """Returns what has been prepared for the survey.

    Its images and how many of them have predictions, footprints and tiles,
    and its current measurement if one exists. Counts only; the estimator is
    not run.
    """
    stmt = sql.SQL("""
        SELECT
            s.status,
            (
                SELECT COUNT(*) FROM core.images i
                WHERE i.survey_id = s.survey_id
            ) AS images,
            (
                SELECT COUNT(DISTINCT p.image_id)
                FROM core.predictions p
                JOIN core.images i ON i.image_id = p.image_id
                WHERE i.survey_id = s.survey_id
            ) AS images_with_predictions,
            (
                SELECT COUNT(DISTINCT f.image_id)
                FROM core.image_footprints f
                JOIN core.images i ON i.image_id = f.image_id
                WHERE i.survey_id = s.survey_id
            ) AS images_with_footprints,
            (
                SELECT COUNT(*)
                FROM core.reviewed_area ra
                JOIN core.images i ON i.image_id = ra.image_id
                WHERE i.survey_id = s.survey_id AND ra.type = %(type)s
            ) AS tiles,
            (
                SELECT COUNT(DISTINCT f.image_id)
                FROM core.image_footprints f
                JOIN core.images i ON i.image_id = f.image_id
                WHERE i.survey_id = s.survey_id
                  AND NOT EXISTS (
                      SELECT 1 FROM core.reviewed_area ra
                      WHERE ra.image_id = f.image_id AND ra.type = %(type)s
                  )
            ) AS georeferenced_images_without_tiles,
            (
                SELECT COUNT(*)
                FROM core.reviewed_area ra
                JOIN core.images i ON i.image_id = ra.image_id
                WHERE i.survey_id = s.survey_id AND ra.type = %(type)s
                  AND ra.reviewed_by_user_id <> 0
            ) AS tiles_reviewed
        FROM projectmanagement.surveys s
        WHERE s.survey_id = %(survey_id)s;
    """)

    cursor.row_factory = dict_row
    cursor.execute(
        stmt,
        {"survey_id": survey_ids.pkey, "type": ActivityType.ACTIVE_MEASUREMENT},
    )
    if not (preparation := cursor.fetchone()):
        raise ObjectNotFound("Survey", str(survey_ids.uuid))

    try:
        measurement = get_active_measurement(cursor, db, survey_ids)
    except ObjectNotFound:
        measurement = None

    preparation["measurement"] = (
        measurement.serialize() if measurement else None
    )
    return preparation


def get_tiles(
    cursor: Cursor[Any],
    db: "Database",
    survey_ids: Keyring,
) -> list[dict[str, Any]]:
    """Returns the survey's measurement tiles, in image then grid order, with
    their bounds in image pixels."""
    stmt = sql.SQL("""
        SELECT ra.reviewed_area_id, ra.uuid, ra.image_id, ra.name,
               ra.area_tx, ra.area_ty, ra.area_bx, ra.area_by
        FROM core.reviewed_area ra
        JOIN core.images i ON i.image_id = ra.image_id
        WHERE i.survey_id = %(survey_id)s
          AND ra.type = %(type)s
        ORDER BY ra.image_id ASC, ra.area_ty ASC, ra.area_tx ASC;
    """)

    cursor.row_factory = dict_row
    cursor.execute(
        stmt,
        {"survey_id": survey_ids.pkey, "type": ActivityType.ACTIVE_MEASUREMENT},
    )
    return cursor.fetchall()


def get_measured_area(
    cursor: Cursor[Any],
    db: "Database",
    survey_id: int,
    reviewed_area_ids: list[int],
) -> float | None:
    """Returns the ground area in square meters the units were cut from.

    The union of the images' footprints, or the survey's stored area when no
    footprints exist. The union of a survey's thousands of footprints takes
    seconds, past the connection's statement timeout, so the statement is
    given its own; callers keep the result (`proposal_store.load_area`).
    """
    # SET takes no parameters; the value is a module constant.
    cursor.execute(
        sql.SQL("SET LOCAL statement_timeout = {ms};").format(
            ms=sql.Literal(AREA_TIMEOUT_MS)
        )
    )
    stmt = sql.SQL("""
        SELECT ST_Area(ST_Transform(ST_Union(f.footprint), %(srid)s))
        FROM core.image_footprints f
        WHERE f.footprint IS NOT NULL
          AND f.image_id IN (
              SELECT DISTINCT ra.image_id
              FROM core.reviewed_area ra
              WHERE ra.reviewed_area_id = ANY(%(reviewed_area_ids)s)
          );
    """)

    cursor.row_factory = tuple_row
    cursor.execute(
        stmt, {"srid": AREA_SRID, "reviewed_area_ids": reviewed_area_ids}
    )
    res = cursor.fetchone()

    if res and res[0]:
        return float(res[0])

    cursor.execute(
        sql.SQL("""
            SELECT survey_area FROM projectmanagement.surveys
            WHERE survey_id = %(survey_id)s;
        """),
        {"survey_id": survey_id},
    )
    res = cursor.fetchone()
    return float(res[0]) if res and res[0] else None


# ---------------------------------------------------------------------------------------------------------------------------
# Estimator state
# ---------------------------------------------------------------------------------------------------------------------------


def _estimator(
    measurement: ActiveMeasurement,
    state: MeasurementState,
    vectors: Vectors,
    units: list[UnitState],
) -> Estimator:
    """The estimator after the measurement's reviewed units.

    Replayed from the stored proposals and the review log on every call, so
    the result does not depend on which worker serves the request.
    """
    log = [
        LogRow(
            step=step,
            unit_id=str(unit.reviewed_area_id),
            generation=state.generation_at(step).generation,
            human_count=float(unit.human_count),
            model_count=0.0,
            count=0.0,
            ci95_half=0.0,
        )
        for step, unit in enumerate(
            (u for u in units if u.reviewed), start=1
        )
    ]

    return Estimator.replay(
        [str(i) for i in state.reviewed_area_ids],
        vectors(),
        log,
        seed=measurement.random_seed,
    )


def _target_fraction(measurement: ActiveMeasurement) -> float | None:
    """The target interval half-width over the count.

    Stored values above 1 are read as percent.
    """
    target = measurement.target_percentage
    if target is None or target <= 0:
        return None
    return target / 100.0 if target > 1 else target


def check_units(
    measurement: ActiveMeasurement, state: MeasurementState
) -> int | None:
    """Returns the number of units of the detection check.

    Those served under generation 0's sharpened proposal before a differently
    shaped generation takes over. A refitting measurement still on generation
    0 switches at its first refit. None when generation 0 is not sharpened.
    """
    first = state.generations[0].alpha
    if first is None or first <= 1.0:
        return None
    if state.switch_at is not None:
        return state.switch_at
    cadence = measurement.retraining_cadence
    return cadence if cadence > 0 else None


def _check_every(measurement: ActiveMeasurement) -> int:
    cadence = measurement.retraining_cadence
    return min(cadence, 100) if cadence > 0 else CHECK_EVERY


def _exhausted(state: MeasurementState, n_reviewed: int) -> bool:
    return n_reviewed >= state.n_units - LAST_UNITS


def _refit_due(state: MeasurementState, n_reviewed: int) -> bool:
    return n_reviewed >= len(state.order) and not _exhausted(state, n_reviewed)


def _min_samples(measurement: ActiveMeasurement) -> int:
    """Reviewed units before the stop rule considers the interval."""
    return max(100, 2 * max(measurement.retraining_cadence, 1))


def _target_met(measurement: ActiveMeasurement, estimator: Estimator) -> bool:
    """True once the interval has stayed at or below target for PERSISTENCE."""
    if (target := _target_fraction(measurement)) is None:
        return False

    check_every = _check_every(measurement)
    min_samples = _min_samples(measurement)

    first_below = None
    for row in estimator.log():
        if row.step % check_every != 0 or row.step < min_samples:
            continue

        met = (
            row.count > 0
            and row.ci95_half / row.count <= target
            and row.step >= MIN_FRACTION * estimator.n_units
        )
        if not met:
            first_below = None
            continue

        first_below = row.step if first_below is None else first_below
        if row.step - first_below >= PERSISTENCE:
            return True

    return False


def _finite(value: float | None) -> float:
    return float(value) if value is not None and isfinite(value) else 0.0


# ---------------------------------------------------------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------------------------------------------------------


def _close_units(
    cursor: Cursor[Any], units: list[UnitState], estimator: Estimator
) -> None:
    """Writes the count and running estimate onto units that lack them."""
    reviewed = [u for u in units if u.reviewed]
    rows = [
        {
            "am_unit_id": unit.am_unit_id,
            "human_count": int(row.human_count),
            "current_count": _finite(row.count),
            "current_ci_lower": _finite(row.count - row.ci95_half),
            "current_ci_upper": _finite(row.count + row.ci95_half),
        }
        for unit, row in zip(reviewed, estimator.log())
        if unit.stored_human_count != int(row.human_count)
        or unit.stored_count is None
        or abs(unit.stored_count - _finite(row.count)) > 1e-9
    ]

    if not rows:
        return

    cursor.executemany(
        sql.SQL("""
            UPDATE core.am_units
            SET human_count = %(human_count)s,
                current_count = %(current_count)s,
                current_ci_lower = %(current_ci_lower)s,
                current_ci_upper = %(current_ci_upper)s,
                modified = CURRENT_TIMESTAMP
            WHERE am_unit_id = %(am_unit_id)s;
        """),
        rows,
    )


def get_detection_model(
    cursor: Cursor[Any], db: "Database", survey_id: int
) -> Model:
    """Returns the survey's detector.

    The newest detection model with predictions on the survey's images, or the
    placeholder model when there are none.
    """
    stmt = sql.SQL("""
        SELECT m.model_id
        FROM projectmanagement.models m
        WHERE m.model_id <> %(no_model)s
          AND EXISTS (
              SELECT 1
              FROM core.predictions p
              JOIN core.images i ON i.image_id = p.image_id
              WHERE p.model_id = m.model_id AND i.survey_id = %(survey_id)s
          )
        ORDER BY m.created DESC, m.model_id DESC
        LIMIT 1;
    """)

    cursor.row_factory = tuple_row
    cursor.execute(stmt, {"survey_id": survey_id, "no_model": NO_MODEL_ID})
    res = cursor.fetchone()
    return db._get(cursor, Model, int(res[0]) if res else NO_MODEL_ID)


def create_draft_annotations(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    detector: Model,
    threshold: float,
    reviewed_area_ids: Keyring,
    user: User,
) -> int:
    """Drafts the detector's boxes at or above `threshold` on a unit as
    annotations.

    The annotations carry the measurement's label and link to the boxes they
    came from. A box belongs to the unit its center lies on.

    Returns:
        The number of boxes drafted.
    """
    stmt = sql.SQL("""
        SELECT p.pred_id, p.uuid AS pred_uuid,
               p.box_tx, p.box_ty, p.box_bx, p.box_by,
               i.image_id, i.uuid AS image_uuid, i.herd_unit_id
        FROM core.reviewed_area t
        JOIN core.images i ON i.image_id = t.image_id
        JOIN core.predictions p ON p.image_id = t.image_id
        JOIN projectmanagement.labels l ON l.label = p.label
        WHERE t.reviewed_area_id = %(reviewed_area_id)s
          AND p.model_id = %(model_id)s
          AND l.label_id = %(label_id)s
          AND p.score >= %(threshold)s
          AND (p.box_tx + p.box_bx) / 2.0 >= t.area_tx
          AND (p.box_tx + p.box_bx) / 2.0 < t.area_bx
          AND (p.box_ty + p.box_by) / 2.0 >= t.area_ty
          AND (p.box_ty + p.box_by) / 2.0 < t.area_by
        ORDER BY p.score DESC, p.pred_id ASC;
    """)

    cursor.row_factory = dict_row
    cursor.execute(
        stmt,
        {
            "reviewed_area_id": reviewed_area_ids.pkey,
            "model_id": detector.model_id,
            "label_id": measurement.label_id,
            "threshold": threshold,
        },
    )
    boxes = cursor.fetchall()

    if not boxes:
        return 0

    herd_unit = db._get(cursor, HerdUnit, boxes[0]["herd_unit_id"])
    herd_unit_ids = Keyring(herd_unit.herd_unit_id, herd_unit.uuid)
    user_ids = Keyring(user.user_id, user.uuid)

    for box in boxes:
        db._insert(
            cursor,
            Annotation,
            CreateAnnotationReq(
                label_id=measurement.label_id,
                image_ids=Keyring(box["image_id"], box["image_uuid"]),
                herd_unit_id=herd_unit.herd_unit_id,
                box_tx=box["box_tx"],
                box_ty=box["box_ty"],
                box_bx=box["box_bx"],
                box_by=box["box_by"],
                uuid=uuid4(),
                type=ActivityType.ACTIVE_MEASUREMENT,
                prediction_ids=Keyring(box["pred_id"], box["pred_uuid"]),
                reviewed_area_ids=reviewed_area_ids,
            ),
            user_ids,
            herd_unit_ids,
        )

    return len(boxes)


def create_generation(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    proposal: Proposal,
) -> ProposalGeneration:
    """Stores the next proposal generation of the measurement.

    Raises:
        MeasurementBlocked: When the generation does not follow the stored
            ones, or one with its number is stored already.
    """
    try:
        check_next(get_proposals(cursor, db, measurement), proposal)
    except ValueError as error:
        raise MeasurementBlocked(str(error))

    req = CreateProposalGenerationReq(
        active_measurement_ids=Keyring(
            measurement.active_measurement_id, measurement.uuid
        ),
        generation=proposal.generation,
        n_labels=proposal.n_labels,
        reviewed_area_ids=list(proposal.reviewed_area_ids),
        raw=proposal.raw.tolist(),
        proposal=proposal.proposal.tolist(),
        model_id=proposal.model_id,
        alpha=proposal.alpha,
    )

    try:
        return db._insert(cursor, ProposalGeneration, req)
    except UniqueViolation:
        raise MeasurementBlocked(
            f"Generation {proposal.generation} of active measurement "
            f"{measurement.uuid} is stored already."
        )


def next_unit(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    state: MeasurementState | None,
    user: User,
    vectors: Vectors,
    threshold: float,
) -> Keyring | None:
    """Returns the Keyring of the next reviewed area to annotate.

    Units are served in the measurement's serving order: drawn without
    replacement with probability proportional to the proposal in force. A unit
    that has been served but not yet marked reviewed is returned again, so the
    call is safe to repeat. Serving a new unit records it in core.am_units,
    linked to the unit served before it, and drafts the detector's boxes at
    or above `threshold` onto it.

    Returns:
        The next unit, or None when the measurement is finished.

    Raises:
        MeasurementBlocked: Without a proposal, while a refit is pending, or
            when the stored units do not follow the serving order.
    """
    # One unit at a time per measurement: a concurrent request waits, then
    # sees the pending unit.
    cursor.execute(
        sql.SQL("SELECT pg_advisory_xact_lock(%(key)s);"),
        {"key": measurement.active_measurement_id},
    )

    if measurement.final_count is not None:
        return None

    if state is None:
        raise MeasurementBlocked(
            f"Active measurement {measurement.uuid} has no proposal; post "
            "generation 0 first."
        )

    units = get_unit_states(cursor, db, measurement)

    if pending := [unit for unit in units if not unit.reviewed]:
        return Keyring(
            pending[0].reviewed_area_id, pending[0].reviewed_area_uuid
        )

    n_reviewed = len(units)

    if [unit.reviewed_area_id for unit in units] != state.order[:n_reviewed]:
        raise MeasurementBlocked(
            f"The units of active measurement {measurement.uuid} do not "
            "follow its serving order."
        )

    if n_reviewed > 0 and (
        n_reviewed % _check_every(measurement) == 0
        or _exhausted(state, n_reviewed)
    ):
        estimator = _estimator(measurement, state, vectors, units)
        _close_units(cursor, units, estimator)

        if _exhausted(state, n_reviewed) or _target_met(measurement, estimator):
            finish(cursor, db, measurement, estimator)
            return None

    if _refit_due(state, n_reviewed):
        raise MeasurementBlocked(
            f"Active measurement {measurement.uuid} is waiting for the "
            f"proposal refit on {n_reviewed} reviewed units."
        )

    reviewed_area_id = state.order[n_reviewed]
    generation = state.generation_at(n_reviewed + 1)

    cursor.row_factory = tuple_row
    cursor.execute(
        sql.SQL("""
            SELECT uuid FROM core.reviewed_area
            WHERE reviewed_area_id = %(id)s;
        """),
        {"id": reviewed_area_id},
    )
    if not (res := cursor.fetchone()):
        raise ObjectNotFound("ReviewedArea", str(reviewed_area_id))
    reviewed_area_ids = Keyring(reviewed_area_id, res[0])

    regressor = db._get(cursor, Model, generation.model_id or NO_MODEL_ID)
    detector = get_detection_model(cursor, db, measurement.survey_id)
    previous = units[-1] if units else None

    unit = db._insert(
        cursor,
        AmUnit,
        CreateAmUnitReq(
            previous_unit_id=previous.am_unit_id if previous else None,
            relative_position=n_reviewed + 1,
            active_measurement_ids=Keyring(
                measurement.active_measurement_id, measurement.uuid
            ),
            reviewed_area_ids=reviewed_area_ids,
            reg_model_ids=Keyring(regressor.model_id, regressor.uuid),
            dect_model_ids=Keyring(detector.model_id, detector.uuid),
            model_count=state.model_count(reviewed_area_id),
            human_count=0,
            current_count=_finite(previous.stored_count if previous else None),
            current_ci_lower=_finite(
                previous.stored_ci_lower if previous else None
            ),
            current_ci_upper=_finite(
                previous.stored_ci_upper if previous else None
            ),
        ),
        Keyring(user.user_id, user.uuid),
    )

    if previous is not None:
        cursor.execute(
            sql.SQL("""
                UPDATE core.am_units SET next_unit_id = %(next)s
                WHERE am_unit_id = %(previous)s;
            """),
            {"next": unit.am_unit_id, "previous": previous.am_unit_id},
        )

    create_draft_annotations(
        cursor, db, measurement, detector, threshold, reviewed_area_ids, user
    )

    return reviewed_area_ids


def finish(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    estimator: Estimator,
) -> ActiveMeasurement:
    """Writes the final count and interval onto the measurement.

    A measurement with a final count stops serving units.
    """
    estimate = estimator.estimate()

    return db._update(
        cursor,
        ActiveMeasurement,
        measurement.active_measurement_id,
        UpdateActiveMeasurement(
            final_count=_finite(estimate.count),
            final_ci_lower=_finite(estimate.count - estimate.ci95_half),
            final_ci_upper=_finite(estimate.count + estimate.ci95_half),
        ),
    )


def empty_estimate(survey_id: int) -> dict[str, Any]:
    """The estimate of a survey that has no measurement yet.

    The same shape as a live estimate, so the page reads one status field
    rather than telling a missing measurement from a failed request.
    """
    return {
        "active_measurement_id": None,
        "phase": None,
        "check_units": None,
        "min_samples": None,
        "figures_from": None,
        "show_fraction": SHOW_FRACTION,
        "uuid": None,
        "survey_id": survey_id,
        "status": NOT_PREPARED,
        "n_units": 0,
        "n_reviewed": 0,
        "n_pending": 0,
        "generation": None,
        "count": None,
        "std_error": None,
        "ci_lower": None,
        "ci_upper": None,
        "relative_ci": None,
        "target": None,
        "area_m2": None,
        "density_per_km2": None,
        "density_ci_lower_per_km2": None,
        "density_ci_upper_per_km2": None,
    }


def live_estimate(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    state: MeasurementState | None,
    vectors: Vectors,
    surveyed_area_m2: float | None = None,
) -> dict[str, Any]:
    """Returns the running estimate for the active measurement.

    From the annotations on its reviewed units: count, 95% interval, progress,
    and density over the measured area. The count is the estimated total of
    the measurement's label over every unit of the measurement, before any
    correction for animals seen in more than one image. The measured area is
    `surveyed_area_m2` when the survey's terms hold it, and is read from the
    footprints otherwise.
    """
    result = empty_estimate(measurement.survey_id)
    result.update(
        active_measurement_id=measurement.active_measurement_id,
        uuid=str(measurement.uuid),
        status="waiting for proposal",
        target=_target_fraction(measurement),
    )

    if state is None:
        return result

    units = get_unit_states(cursor, db, measurement)
    estimator = _estimator(measurement, state, vectors, units)
    estimate = estimator.estimate()
    n_reviewed = estimator.n_reviewed

    if measurement.final_count is not None:
        status = "finished"
    elif _exhausted(state, n_reviewed):
        status = "exhausted"
    elif _target_met(measurement, estimator):
        status = "target met"
    elif _refit_due(state, n_reviewed):
        status = "waiting for refit"
    else:
        status = "measuring"

    result.update(
        status=status,
        n_units=estimator.n_units,
        n_reviewed=n_reviewed,
        n_pending=sum(1 for unit in units if not unit.reviewed),
        generation=state.generation_at(n_reviewed + 1).generation,
    )
    check = check_units(measurement, state)
    result.update(
        check_units=check,
        phase=DETECTION_CHECK if check and n_reviewed < check else FULL_REVIEW,
        min_samples=_min_samples(measurement),
        # The interval is not worth reading before this many units: with a
        # handful of tiles across a sparse survey, one animal in a tile the
        # proposal thought empty moves the count by hundreds, as it should.
        figures_from=max(
            _min_samples(measurement),
            ceil(SHOW_FRACTION * estimator.n_units),
        ),
        show_fraction=SHOW_FRACTION,
    )

    if n_reviewed == 0 or not isfinite(estimate.count):
        return result

    half = Z95 * estimate.std_error
    result.update(
        count=estimate.count,
        std_error=estimate.std_error,
        # A count is never negative.
        ci_lower=max(0.0, estimate.count - half),
        ci_upper=estimate.count + half,
        relative_ci=half / estimate.count if estimate.count > 0 else None,
    )

    area = surveyed_area_m2 or get_measured_area(
        cursor, db, measurement.survey_id, state.reviewed_area_ids
    )

    if area:
        km2 = area / 1e6
        result.update(
            area_m2=area,
            density_per_km2=estimate.count / km2,
            density_ci_lower_per_km2=max(0.0, estimate.count - half) / km2,
            density_ci_upper_per_km2=(estimate.count + half) / km2,
        )

    return result


def create_tiles(
    cursor: Cursor[Any],
    db: "Database",
    survey_ids: Keyring,
    image_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Cuts the survey's images into 'active measurement' reviewed areas.

    Each image (or only `image_ids`) becomes TILE_ROWS x TILE_COLS tiles;
    images that already have them are skipped. A tile is named
    '<image name>__r<row>c<col>'.

    Returns:
        The survey's tiles, in image then grid order.
    """
    select = sql.SQL("""
        SELECT i.image_id
        FROM core.images i
        WHERE i.survey_id = %(survey_id)s
          AND i.image_width_px > 0
          AND i.image_length_px > 0
          AND (%(all_images)s OR i.image_id = ANY(%(image_ids)s))
          AND NOT EXISTS (
              SELECT 1 FROM core.reviewed_area ra
              WHERE ra.image_id = i.image_id
                AND ra.type = %(type)s
          )
        ORDER BY i.image_id ASC;
    """)

    insert = sql.SQL("""
        INSERT INTO core.reviewed_area (
            image_id, type, name, ra_key, area_tx, area_ty, area_bx, area_by,
            reviewed_area_length_px, reviewed_area_width_px
        )
        SELECT
            i.image_id,
            %(type)s,
            i.name || '__r' || r || 'c' || c,
            'images/' || i.uuid || '/reviewed_area/' || %(tiling)s || '/'
                || i.name || '__r' || r || 'c' || c,
            (c * i.image_width_px) / %(cols)s,
            (r * i.image_length_px) / %(rows)s,
            ((c + 1) * i.image_width_px) / %(cols)s,
            ((r + 1) * i.image_length_px) / %(rows)s,
            ((r + 1) * i.image_length_px) / %(rows)s
                - (r * i.image_length_px) / %(rows)s,
            ((c + 1) * i.image_width_px) / %(cols)s
                - (c * i.image_width_px) / %(cols)s
        FROM core.images i
        CROSS JOIN generate_series(0, %(rows)s - 1) AS r
        CROSS JOIN generate_series(0, %(cols)s - 1) AS c
        WHERE i.image_id = ANY(%(image_ids)s)
        RETURNING uuid, (
            SELECT uuid FROM core.images
            WHERE image_id = reviewed_area.image_id
        );
    """)

    cursor.row_factory = tuple_row
    cursor.execute(
        select,
        {
            "type": ActivityType.ACTIVE_MEASUREMENT,
            "survey_id": survey_ids.pkey,
            "all_images": image_ids is None,
            "image_ids": image_ids or [],
        },
    )
    to_cut = [row[0] for row in cursor.fetchall()]

    # A survey's worth of tiles in one statement outlasts the statement
    # timeout.
    created = []
    for start in range(0, len(to_cut), IMAGES_PER_STATEMENT):
        cursor.execute(
            insert,
            {
                "type": ActivityType.ACTIVE_MEASUREMENT,
                "rows": TILE_ROWS,
                "cols": TILE_COLS,
                "tiling": TILING,
                "image_ids": to_cut[start : start + IMAGES_PER_STATEMENT],
            },
        )
        created.extend(cursor.fetchall())

    relations = [
        create_spice_update(
            "reviewed_area", tile_uuid, "image", image_uuid, "parent"
        )
        for tile_uuid, image_uuid in created
    ]
    for start in range(0, len(relations), SPICE_BATCH):
        db.write_spice_relationships(relations[start : start + SPICE_BATCH])

    return get_tiles(cursor, db, survey_ids)
