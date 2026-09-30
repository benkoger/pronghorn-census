# Abundance Specialized Database Operations
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# The abundance of a survey and the terms it needs, read from what is stored:
#
#   place_boxes(measurement)                -> the detector's boxes placed on the ground
#   prepare_terms(measurement, state, ...)  -> the survey's terms before any review
#   live_abundance(measurement, state, ...) -> the abundance from the review so far
#   apply_overlap(estimate, abundance)      -> the estimate as animals, after the overlap factor
#
# Two terms depend on where the animals are: the overlap factor (animals seen in more than one
# image) and the representation (how well the transects stand for the habitable area).
#
#   Before any review, the animals are the detector's boxes at PREPARED_THRESHOLD or above,
#   placed on the ground and overlap-weighted: both terms are taken from those. The proposal's
#   expected counts are too smooth to show how animals clump between transects.
#
#   During review, both are taken from the animals the map shows: the annotations on the
#   reviewed tiles and the detector's boxes standing in for the animals on the others.
#
# An image belongs to the transect in its metadata (image_metadata.transect_id).
#
# The detector's boxes and their positions do not change during a measurement. They are placed
# once, when the survey is prepared, so that an estimate only has to place the annotations.
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import replace
from math import sqrt
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import psycopg.sql as sql
import shapely
from psycopg import Cursor
from psycopg.rows import dict_row, tuple_row
from pyproj import Transformer

from ais import MeasurementState, PlacedBoxes, SurveyTerms, overall_abundance
from ais.overlap import image_sigma, overlap_weights
from ais.representation import representation, sampling_units, unit_areas, unit_totals
from database.errors import MeasurementBlocked
from database.modules import surveymap
from database.object_models.core.image_metadata import NO_TRANSECT
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
)

if TYPE_CHECKING:
    from database.database import Database

# ---------------------------------------------------------------------------------------------------------------------------

AREA_SRID = 5072
NOT_MEASURED = 0.0  # a position accuracy at or below this was not measured
IMAGES_PER_STATEMENT = 250
PREPARED_THRESHOLD = 0.7  # boxes at or above this score stand for the animals before review

_to_meters = Transformer.from_crs(4326, AREA_SRID, always_xy=True)

# ---------------------------------------------------------------------------------------------------------------------------
# Frames and transects


def get_frames(
    cursor: Cursor[Any],
    db: "Database",
    survey_id: int,
) -> list[dict[str, Any]]:
    """
    Returns the survey's images that have a footprint, each with its key, its transect and the
    accuracy of positions placed through it, in meters (NaN when none is known).
    """
    stmt = sql.SQL("""
        SELECT DISTINCT ON (i.image_id)
            i.image_id, i.img_key, f.rmse_h_m, f.pose_sigma,
            COALESCE(m.transect_id, %(no_transect)s) AS transect_id
        FROM core.images i
        JOIN core.image_footprints f ON f.image_id = i.image_id
        LEFT JOIN core.image_metadata m ON m.image_id = i.image_id
        WHERE i.survey_id = %(survey_id)s
          AND f.footprint IS NOT NULL
        ORDER BY i.image_id ASC, f.footprint_id DESC, m.metadata_id DESC;
    """)

    cursor.row_factory = dict_row
    cursor.execute(stmt, {"survey_id": survey_id, "no_transect": NO_TRANSECT})

    frames = []
    for row in cursor.fetchall():
        sigma = float(row["rmse_h_m"])
        if not sigma > NOT_MEASURED:
            east, north = (list(row["pose_sigma"]) + [0.0, 0.0])[:2]
            sigma = sqrt(0.5 * (east * east + north * north))

        frames.append(
            {
                "image_id": row["image_id"],
                "img_key": row["img_key"],
                "transect": str(row["transect_id"]),
                "position_sigma_m": sigma if sigma > NOT_MEASURED else np.nan,
            }
        )

    return frames


def get_transect_areas(
    cursor: Cursor[Any],
    db: "Database",
    survey_id: int,
    transects: list[str],
) -> tuple[list[float], float]:
    """
    Returns the ground area in square meters covered by each transect's images, and the area
    covered by all of them together.
    """
    stmt = sql.SQL("""
        SELECT ST_AsBinary(ST_Transform(ST_Union(f.footprint), %(srid)s))
        FROM core.image_footprints f
        JOIN core.images i ON i.image_id = f.image_id
        LEFT JOIN core.image_metadata m ON m.image_id = i.image_id
        WHERE i.survey_id = %(survey_id)s
          AND f.footprint IS NOT NULL
          AND COALESCE(m.transect_id, %(no_transect)s) = %(transect_id)s;
    """)

    cursor.row_factory = tuple_row
    covered = []
    for transect in transects:
        cursor.execute(
            stmt,
            {
                "srid": AREA_SRID,
                "survey_id": survey_id,
                "no_transect": NO_TRANSECT,
                "transect_id": int(transect),
            },
        )
        res = cursor.fetchone()
        covered.append(shapely.from_wkb(bytes(res[0])) if res and res[0] else shapely.Polygon())

    return [float(area.area) for area in covered], float(shapely.union_all(covered).area)

# ---------------------------------------------------------------------------------------------------------------------------
# Animals on the ground


def _positions(
    cursor: Cursor[Any],
    rows: list[dict[str, Any]],
) -> list[Optional[tuple[float, float]]]:
    """
    Returns the position in meters of each row's center (image_id, center_x, center_y), or
    None for a row whose image has no ground control.
    """
    image_ids = sorted({row["image_id"] for row in rows})
    locate = {}

    cursor.row_factory = dict_row
    for start in range(0, len(image_ids), IMAGES_PER_STATEMENT):
        cursor.execute(
            sql.SQL("""
                SELECT DISTINCT ON (f.image_id) f.image_id, f.gcps
                FROM core.image_footprints f
                WHERE f.image_id = ANY(%(image_ids)s)
                ORDER BY f.image_id ASC, f.footprint_id DESC;
            """),
            {"image_ids": image_ids[start : start + IMAGES_PER_STATEMENT]},
        )
        for row in cursor.fetchall():
            locate[row["image_id"]] = surveymap._ground_position(row["gcps"])

    positions: list[Optional[tuple[float, float]]] = []
    for row in rows:
        if (position := locate.get(row["image_id"])) is None:
            positions.append(None)
            continue
        lon, lat = position(float(row["center_x"]), float(row["center_y"]))
        positions.append(_to_meters.transform(lon, lat))

    return positions


def place_boxes(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
) -> PlacedBoxes:
    """
    Returns the boxes of the survey's detector that the map can show, placed on the ground,
    highest score first. A box on an image with no ground control is left out.
    """
    boxes = surveymap._candidates(cursor, db, measurement, reviewed=False)
    placed = [
        (box, position)
        for box, position in zip(boxes, _positions(cursor, boxes))
        if position is not None
    ]

    return PlacedBoxes(
        image_ids=np.asarray([box["image_id"] for box, _ in placed]),
        reviewed_area_ids=np.asarray([box["reviewed_area_id"] for box, _ in placed]),
        scores=np.asarray([float(box["score"]) for box, _ in placed]),
        east_m=np.asarray([position[0] for _, position in placed]),
        north_m=np.asarray([position[1] for _, position in placed]),
    )


def _reviewed_units(cursor: Cursor[Any], measurement: ActiveMeasurement) -> set[int]:
    """The measurement's units that have been reviewed."""
    cursor.row_factory = tuple_row
    cursor.execute(
        sql.SQL("""
            SELECT u.reviewed_area_id
            FROM core.am_units u
            JOIN core.reviewed_area ra ON ra.reviewed_area_id = u.reviewed_area_id
            WHERE u.active_measurement_id = %(active_measurement_id)s
              AND ra.reviewed_by_user_id <> 0;
        """),
        {"active_measurement_id": measurement.active_measurement_id},
    )
    return {row[0] for row in cursor.fetchall()}


def _animals(
    cursor: Cursor[Any],
    measurement: ActiveMeasurement,
    state: MeasurementState,
    boxes: PlacedBoxes,
    count: float,
    reviewed: bool,
) -> tuple[list[int], list[tuple[float, float]]]:
    """
    Returns the image and the position in meters of each animal the map shows at an
    estimated count of `count`: the annotations on the reviewed units, then the placed boxes
    standing in for the animals on the others. `reviewed` False ignores the review.
    """
    annotated = surveymap._annotated(cursor, measurement) if reviewed else []
    done = _reviewed_units(cursor, measurement) if reviewed else set()

    candidates = [
        {"at": at, "reviewed_area_id": int(unit), "score": float(score)}
        for at, (unit, score) in enumerate(zip(boxes.reviewed_area_ids, boxes.scores))
        if int(unit) not in done
    ]
    expected = dict(zip(state.reviewed_area_ids, map(float, state.raw)))
    n_estimated = int(round(max(0.0, count - len(annotated))))
    picked = surveymap.place_estimated(candidates, expected, n_estimated)

    image_of, position = [], []
    for row, at in zip(annotated, _positions(cursor, annotated)):
        if at is not None:
            image_of.append(row["image_id"])
            position.append(at)
    for box in picked:
        image_of.append(int(boxes.image_ids[box["at"]]))
        position.append((float(boxes.east_m[box["at"]]), float(boxes.north_m[box["at"]])))

    return image_of, position


# ---------------------------------------------------------------------------------------------------------------------------
# The two terms that depend on where the animals are


def _weights_per_image(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    state: MeasurementState,
    frames: list[dict[str, Any]],
    boxes: PlacedBoxes,
    count: float,
    reviewed: bool,
) -> Optional[tuple[dict[int, float], float]]:
    """
    Returns the animals on each image after the overlap weights and the mean weight, for the
    animals the map shows at an estimated count of `count`. `reviewed` False ignores the
    review, so that every animal is one of the detector's boxes. None when no animal could be
    placed.
    """
    return _weighted(frames, *_animals(cursor, measurement, state, boxes, count, reviewed))


def _weighted(
    frames: list[dict[str, Any]],
    image_of: list[int],
    positions: list[tuple[float, float]],
) -> Optional[tuple[dict[int, float], float]]:
    """
    Returns the animals on each image after the overlap weights and the mean weight, for
    animals at `positions` (meters) placed from the images `image_of`. None when there are none
    on a frame with a position accuracy.
    """
    sigma_of = {frame["image_id"]: frame["position_sigma_m"] for frame in frames}
    shown = [(i, at) for i, at in zip(image_of, positions) if i in sigma_of]
    if not shown:
        return None

    images = np.asarray([i for i, _ in shown])
    sigma = image_sigma(np.asarray([sigma_of[i] for i in images], dtype=float))
    weights = overlap_weights(np.asarray([at for _, at in shown]), images, sigma)

    per_image: dict[int, float] = {}
    for image_id, weight in zip(images.tolist(), weights.tolist()):
        per_image[image_id] = per_image.get(image_id, 0.0) + weight

    return per_image, float(weights.mean())


def _confident(boxes: PlacedBoxes) -> tuple[list[int], list[tuple[float, float]]]:
    """The placed boxes at PREPARED_THRESHOLD or above: image and position of each."""
    keep = boxes.scores >= PREPARED_THRESHOLD
    return (
        boxes.image_ids[keep].tolist(),
        list(zip(boxes.east_m[keep].tolist(), boxes.north_m[keep].tolist())),
    )


def _terms_from(
    terms: SurveyTerms,
    frames: list[dict[str, Any]],
    animals: dict[int, float],
    overlap_factor: Optional[float],
) -> SurveyTerms:
    """
    Returns `terms` with the representation of `animals` (per image) over the transects, and
    with `overlap_factor` when one is given. A term that cannot be computed is left as it is.
    """
    units = sampling_units(
        [frame["transect"] for frame in frames],
        [frame["img_key"] for frame in frames],
    )
    labels, totals = unit_totals(units, [animals.get(frame["image_id"], 0.0) for frame in frames])
    areas = unit_areas(labels, dict(zip(terms.transects, terms.transect_areas_m2.tolist())))

    spread = representation(totals, areas, terms.surveyed_area_m2, terms.habitable_area_m2)

    if spread is not None:
        terms = replace(
            terms,
            representation_sigma=spread.sigma,
            representation_draws=spread.draws,
            n_units=spread.n_units,
        )
    if overlap_factor is not None:
        terms = replace(terms, overlap_factor=overlap_factor)

    return terms


# ---------------------------------------------------------------------------------------------------------------------------


def prepare_terms(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    state: MeasurementState,
    boxes: PlacedBoxes,
    habitable_area_m2: float,
    area_sigma_m2: float,
    area_draws: list[float],
) -> SurveyTerms:
    """
    Returns the survey's terms before any review: the surveyed area and the area of each
    transect, and the representation and overlap factor of the detector's confident boxes.
    """
    frames = get_frames(cursor, db, measurement.survey_id)
    transects = sorted({frame["transect"] for frame in frames})

    if not any(transect != str(NO_TRANSECT) for transect in transects):
        raise MeasurementBlocked("the survey's images have no transect")

    areas, surveyed = get_transect_areas(cursor, db, measurement.survey_id, transects)

    try:
        terms = SurveyTerms(
            habitable_area_m2=habitable_area_m2,
            surveyed_area_m2=surveyed,
            area_sigma_m2=area_sigma_m2,
            area_draws=np.asarray(area_draws, dtype=float),
            transects=transects,
            transect_areas_m2=np.asarray(areas, dtype=float),
        )
    except ValueError as error:
        raise MeasurementBlocked(str(error))

    if (confident := _weighted(frames, *_confident(boxes))) is None:
        return terms

    return _terms_from(terms, frames, confident[0], confident[1])


CORRECTED = (
    "count",
    "std_error",
    "ci_lower",
    "ci_upper",
    "density_per_km2",
    "density_ci_lower_per_km2",
    "density_ci_upper_per_km2",
)


def apply_overlap(estimate: dict[str, Any], abundance: Optional[dict[str, Any]]) -> dict[str, Any]:
    """
    Returns `estimate` with its count, interval and density scaled by the overlap factor of
    `abundance`, so that they count animals rather than sightings. The estimator's own count is
    kept as count_raw. Unchanged when there is no abundance.
    """
    estimate = {**estimate, "count_raw": estimate["count"], "overlap_factor": None}
    if abundance is None:
        return estimate

    factor = abundance["overlap_factor"]
    estimate["overlap_factor"] = factor
    for key in CORRECTED:
        if estimate.get(key) is not None:
            estimate[key] = estimate[key] * factor

    return estimate


def live_abundance(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    state: Optional[MeasurementState],
    estimate: dict[str, Any],
    terms: Optional[SurveyTerms],
    boxes: Optional[PlacedBoxes],
) -> Optional[dict[str, Any]]:
    """
    Returns the abundance over the habitable area for the running `estimate`, with the overlap
    factor and the representation taken from the review so far. None before the first
    reviewed unit, or when the survey has no terms.
    """
    if state is None or terms is None or boxes is None or estimate["count"] is None:
        return None

    frames = get_frames(cursor, db, measurement.survey_id)
    shown = _weights_per_image(
        cursor, db, measurement, state, frames, boxes, estimate["count"], reviewed=True
    )

    live = terms if shown is None else _terms_from(terms, frames, shown[0], shown[1])

    return overall_abundance(estimate["count"], estimate["std_error"], live, prepared=terms)
