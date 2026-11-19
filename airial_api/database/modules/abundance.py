# Abundance Specialized Database Operations
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# The abundance of a survey and the terms it needs, read from what is stored:
#
#   place_boxes(measurement, threshold)    -> the detector's boxes on the ground
#   prepare_terms(measurement, boxes, ...) -> the survey's terms before review
#   set_terms(measurement, terms)          -> store them on the measurement
#   live_abundance(measurement, ...)       -> the abundance from the review so far
#
# abundance = overlap factor x estimated count / surveyed area x habitable area
#
# Two terms depend on where the animals are: the overlap factor (animals seen
# in more than one image) and the representation (how well the transects stand
# for the habitable area).
#
#   Before any review, the animals are the detector's boxes at the draft
#   threshold, whose number is the regressor's expected total. Both terms are
#   taken from those boxes, placed on the ground.
#
#   During review, both are taken from the animals the map shows: the
#   annotations on the reviewed tiles and the detector's boxes standing in for
#   the animals on the others (database.modules.surveymap).
#
# An image belongs to the transect in its metadata (image_metadata.transect_id).
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import replace
from typing import TYPE_CHECKING, Any

import numpy as np
import psycopg.sql as sql
import shapely
from psycopg import Cursor
from psycopg.rows import dict_row, tuple_row
from psycopg.types.json import Jsonb

from ais import MeasurementState, PlacedBoxes, SurveyTerms, overall_abundance
from ais.overlap import coverage_weights
from ais.representation import (
    representation,
    sampling_units,
    unit_areas,
    unit_totals,
)
from database.errors import MeasurementBlocked
from database.modules import surveymap
from database.modules.activemeasurement import AREA_SRID, AREA_TIMEOUT_MS
from database.object_models.core.image_metadata import NO_TRANSECT
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
)

if TYPE_CHECKING:
    from database.database import Database

# ---------------------------------------------------------------------------------------------------------------------------
# Frames and transects


def get_frames(
    cursor: Cursor[Any],
    db: "Database",
    survey_id: int,
) -> list[dict[str, Any]]:
    """Returns the survey's georeferenced images.

    Args:
        cursor: Active database cursor.
        db: The database.
        survey_id: Primary key of the survey.

    Returns:
        Each image with a footprint: its id, key and transect.
    """
    stmt = sql.SQL("""
        SELECT DISTINCT ON (i.image_id)
            i.image_id, i.img_key,
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

    return [
        {
            "image_id": row["image_id"],
            "img_key": row["img_key"],
            "transect": str(row["transect_id"]),
        }
        for row in cursor.fetchall()
    ]


def get_transect_areas(
    cursor: Cursor[Any],
    db: "Database",
    survey_id: int,
) -> tuple[list[str], list[float], float]:
    """Returns the ground covered by each transect's images and by all of them.

    The union of a survey's footprints takes seconds, so the statement is
    given its own timeout, as the measured area's is.

    Args:
        cursor: Active database cursor.
        db: The database.
        survey_id: Primary key of the survey.

    Returns:
        The transects, the area of each in square meters, and the area of
        their union.
    """
    # SET takes no parameters; the value is a module constant.
    cursor.execute(
        sql.SQL("SET LOCAL statement_timeout = {ms};").format(
            ms=sql.Literal(AREA_TIMEOUT_MS)
        )
    )
    stmt = sql.SQL("""
        WITH frames AS (
            SELECT DISTINCT ON (i.image_id)
                COALESCE(m.transect_id, %(no_transect)s) AS transect_id,
                ST_Transform(f.footprint, %(srid)s) AS footprint
            FROM core.images i
            JOIN core.image_footprints f ON f.image_id = i.image_id
            LEFT JOIN core.image_metadata m ON m.image_id = i.image_id
            WHERE i.survey_id = %(survey_id)s
              AND f.footprint IS NOT NULL
            ORDER BY i.image_id ASC, f.footprint_id DESC, m.metadata_id DESC
        ),
        transects AS (
            SELECT transect_id, ST_Union(footprint) AS covered
            FROM frames
            GROUP BY transect_id
        )
        SELECT transect_id, ST_Area(covered),
               (SELECT ST_Area(ST_Union(covered)) FROM transects)
        FROM transects
        ORDER BY transect_id ASC;
    """)

    cursor.row_factory = tuple_row
    cursor.execute(
        stmt,
        {
            "srid": AREA_SRID,
            "survey_id": survey_id,
            "no_transect": NO_TRANSECT,
        },
    )
    rows = cursor.fetchall()
    if not rows:
        return [], [], 0.0
    return (
        [str(row[0]) for row in rows],
        [float(row[1]) for row in rows],
        float(rows[0][2]),
    )


# ---------------------------------------------------------------------------------------------------------------------------
# Animals on the ground


def place_boxes(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    threshold: float,
) -> PlacedBoxes:
    """Returns the detector's boxes at `threshold` or above, on the ground.

    Args:
        cursor: Active database cursor.
        db: The database.
        measurement: The active measurement.
        threshold: Its draft threshold.

    Returns:
        The boxes placed in longitude and latitude, highest score first. A
        box on an image with no ground control is left out.
    """
    boxes = surveymap.candidates(cursor, db, measurement, threshold)
    lonlat = surveymap.locate(cursor, boxes)
    placed = [(box, at) for box, at in zip(boxes, lonlat) if at is not None]

    return PlacedBoxes(
        image_ids=[box["image_id"] for box, _ in placed],
        reviewed_area_ids=[box["reviewed_area_id"] for box, _ in placed],
        prediction_uuids=[str(box["prediction_uuid"]) for box, _ in placed],
        scores=[float(box["score"]) for box, _ in placed],
        lon=[at[0] for _, at in placed],
        lat=[at[1] for _, at in placed],
    )


def _animals(
    cursor: Cursor[Any],
    measurement: ActiveMeasurement,
    state: MeasurementState,
    boxes: PlacedBoxes,
    count: float,
) -> tuple[list[int], list[tuple[float, float]]]:
    """Returns the image and longitude and latitude of each animal the map shows.

    The annotations on the reviewed tiles, then the placed boxes standing in
    for the animals on the others at an estimated count of `count`.
    """
    on_map = surveymap.shown(cursor, measurement, state, boxes, count)
    seen = [row for row in on_map.annotated if row["lon"] is not None]

    image_of = [row["image_id"] for row in seen]
    positions = [(row["lon"], row["lat"]) for row in seen]
    for at in on_map.picked:
        image_of.append(int(boxes.image_ids[at]))
        positions.append((float(boxes.lon[at]), float(boxes.lat[at])))
    return image_of, positions


# ---------------------------------------------------------------------------------------------------------------------------
# The two terms that depend on where the animals are


def _covering(
    cursor: Cursor[Any],
    survey_id: int,
    image_of: list[int],
    positions: list[tuple[float, float]],
) -> np.ndarray:
    """Returns how many images other than its own cover each animal.

    An image covers an animal when its latest footprint contains the
    animal's longitude and latitude. The footprints have no spatial index,
    so they are read once and searched with a tree here.
    """
    stmt = sql.SQL("""
        SELECT DISTINCT ON (f.image_id) f.image_id, ST_AsBinary(f.footprint)
        FROM core.image_footprints f
        JOIN core.images i ON i.image_id = f.image_id
        WHERE i.survey_id = %(survey_id)s
          AND f.footprint IS NOT NULL
        ORDER BY f.image_id ASC, f.footprint_id DESC;
    """)

    cursor.row_factory = tuple_row
    cursor.execute(stmt, {"survey_id": survey_id})
    rows = cursor.fetchall()

    footprint_of = np.asarray([row[0] for row in rows])
    tree = shapely.STRtree(shapely.from_wkb([bytes(row[1]) for row in rows]))
    animal, footprint = tree.query(shapely.points(positions), predicate="within")

    others = np.zeros(len(positions))
    other = footprint_of[footprint] != np.asarray(image_of)[animal]
    np.add.at(others, animal[other], 1)
    return others


def _weighted(
    cursor: Cursor[Any],
    survey_id: int,
    frames: list[dict[str, Any]],
    image_of: list[int],
    positions: list[tuple[float, float]],
) -> tuple[dict[int, float], float] | None:
    """Returns the animals on each image after the overlap weights.

    Args:
        cursor: Active database cursor.
        survey_id: Primary key of the survey.
        frames: The survey's georeferenced images (`get_frames`).
        image_of: The image each animal was placed from.
        positions: Each animal's longitude and latitude.

    Returns:
        The weighted animals per image and the mean weight, the overlap
        factor; None when no animal is on a georeferenced image.
    """
    georeferenced = {frame["image_id"] for frame in frames}
    shown = [(i, at) for i, at in zip(image_of, positions) if i in georeferenced]
    if not shown:
        return None

    images = [i for i, _ in shown]
    weights = coverage_weights(
        _covering(cursor, survey_id, images, [at for _, at in shown])
    )

    per_image: dict[int, float] = {}
    for image_id, weight in zip(images, weights.tolist()):
        per_image[image_id] = per_image.get(image_id, 0.0) + weight
    return per_image, float(weights.mean())


def _terms_from(
    terms: SurveyTerms,
    frames: list[dict[str, Any]],
    animals: dict[int, float],
    overlap_factor: float,
) -> SurveyTerms:
    """Returns `terms` with the representation and overlap of `animals`.

    The representation is left as it is when it cannot be computed.
    """
    units = sampling_units(
        [frame["transect"] for frame in frames],
        [frame["img_key"] for frame in frames],
    )
    labels, totals = unit_totals(
        units, [animals.get(frame["image_id"], 0.0) for frame in frames]
    )
    areas = unit_areas(
        labels, dict(zip(terms.transects, terms.transect_areas_m2.tolist()))
    )
    spread = representation(
        totals, areas, terms.surveyed_area_m2, terms.habitable_area_m2
    )

    terms = replace(terms, overlap_factor=overlap_factor)
    if spread is not None:
        terms = replace(
            terms,
            representation_sigma=spread.sigma,
            representation_draws=spread.draws,
            n_units=spread.n_units,
        )
    return terms


# ---------------------------------------------------------------------------------------------------------------------------


def prepare_terms(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    boxes: PlacedBoxes,
    habitable_area_m2: float,
    area_sigma_m2: float,
    area_draws: list[float],
) -> SurveyTerms:
    """Returns the survey's terms before any review.

    Args:
        cursor: Active database cursor.
        db: The database.
        measurement: The active measurement.
        boxes: The detector's boxes at the draft threshold, on the ground.
        habitable_area_m2: Habitable area of the herd unit.
        area_sigma_m2: Standard deviation of the surveyed area.
        area_draws: Draws of the surveyed area.

    Returns:
        The surveyed area and each transect's, and the representation and
        overlap factor of the placed boxes.

    Raises:
        MeasurementBlocked: The images have no transect, or a term is out of
            range.
    """
    transects, areas, surveyed = get_transect_areas(
        cursor, db, measurement.survey_id
    )
    if not any(transect != str(NO_TRANSECT) for transect in transects):
        raise MeasurementBlocked("the survey's images have no transect")

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
        raise MeasurementBlocked(str(error)) from error

    frames = get_frames(cursor, db, measurement.survey_id)
    positions = list(zip(boxes.lon.tolist(), boxes.lat.tolist()))
    weighted = _weighted(
        cursor, measurement.survey_id, frames, boxes.image_ids.tolist(), positions
    )
    if weighted is None:
        return terms
    return _terms_from(terms, frames, *weighted)


def set_terms(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    terms: SurveyTerms,
) -> None:
    """Stores the survey terms on the measurement, replacing any before.

    Args:
        cursor: Active database cursor.
        db: The database.
        measurement: The active measurement.
        terms: The terms.
    """
    cursor.execute(
        sql.SQL("""
            UPDATE projectmanagement.active_measurements
            SET terms = %(terms)s, modified = CURRENT_TIMESTAMP
            WHERE active_measurement_id = %(active_measurement_id)s;
        """),
        {
            "terms": Jsonb(terms.as_dict()),
            "active_measurement_id": measurement.active_measurement_id,
        },
    )


def live_abundance(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    state: MeasurementState,
    estimate: dict[str, Any],
    terms: SurveyTerms,
    boxes: PlacedBoxes,
) -> dict[str, Any] | None:
    """Returns the abundance over the habitable area for the running estimate.

    The overlap factor and the representation are taken from the animals the
    map shows at the estimated count.

    Args:
        cursor: Active database cursor.
        db: The database.
        measurement: The active measurement.
        state: Its serving state.
        estimate: The running estimate (`live_estimate`).
        terms: The terms prepared before review.
        boxes: The detector's boxes at the draft threshold, on the ground.

    Returns:
        The abundance and its uncertainty by source (`overall_abundance`), or
        None before the first reviewed unit.
    """
    if estimate["count"] is None:
        return None

    frames = get_frames(cursor, db, measurement.survey_id)
    weighted = _weighted(
        cursor,
        measurement.survey_id,
        frames,
        *_animals(cursor, measurement, state, boxes, estimate["count"]),
    )
    live = terms if weighted is None else _terms_from(terms, frames, *weighted)

    return overall_abundance(
        estimate["count"], estimate["std_error"], live, prepared=terms
    )
