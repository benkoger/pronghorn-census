# Survey Map Specialized Database Operations
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# What the survey map draws, read from what is stored:
#
#   get_footprints(survey)            -> GeoJSON of the survey's image footprints
#   get_detections(measurement, ...)  -> the detections the map shows, on the ground
#   get_overlay_source(image)         -> what drawing an image onto the ground needs
#   set_overlay_key(footprint, key)   -> where an image's overlay is stored
#
# The detections come from the abundance estimation, so the map shows none
# before a measurement has a proposal. They are
#
#   annotated   the annotations of the measurement's label on its reviewed
#               tiles, and
#   estimated   N of the detector's boxes standing in for the animals on the
#               tiles not reviewed, where N = round(estimated count - annotated).
#
# The candidates for the N are the detector's boxes at or above the draft
# threshold, the score at which the box count over the tiles equals the
# regressor's expected total. They are placed where the proposal expects
# animals: unreviewed tiles are visited in descending expected count, each
# giving up to ceil(expected count) of its highest scoring boxes, and any left
# to place are the highest scoring boxes remaining. A reviewed tile's boxes are
# never estimated: its annotations carry its animals. The boxes are placed on
# the ground once per generation (proposal_store.load_boxes), and the
# abundance takes its overlap and representation from the same animals the map
# shows (`shown`).
#
# A box is in image pixels. It is placed on the ground through its image's
# ground control points, a grid of (row, column, longitude, latitude).
# ---------------------------------------------------------------------------------------------------------------------------

from math import ceil
from typing import TYPE_CHECKING, Any, Callable, NamedTuple

import numpy as np
import psycopg.sql as sql
from psycopg import Cursor
from psycopg.rows import dict_row, tuple_row
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
import shapely

from ais import MeasurementState, PlacedBoxes
from ais.overlap import coverage_weights
from database.errors import ObjectNotFound
from database.modules.activemeasurement import get_detection_model
from database.object_models.core.activity import ActivityType
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
)

if TYPE_CHECKING:
    from database.database import Database

# ---------------------------------------------------------------------------------------------------------------------------

# About a meter: footprint outlines are drawn, not measured.
SIMPLIFY_DEGREES = 0.00001
COORDINATE_DIGITS = 6
# A box in image pixels: left, top, right, bottom.
PIXELS = ("box_tx", "box_ty", "box_bx", "box_by")
# Ground control is read this many images at a time.
IMAGES_PER_STATEMENT = 250

# (column, row) in image pixels -> (longitude, latitude)
Locator = Callable[[float, float], tuple[float, float]]

# ---------------------------------------------------------------------------------------------------------------------------


def get_footprints(
    cursor: Cursor[Any],
    db: "Database",
    survey_id: int,
) -> dict[str, Any]:
    """Returns the survey's footprints as a GeoJSON FeatureCollection.

    Each feature carries its image, its area, the box its overlay covers and
    how many of its tiles have been reviewed.

    Args:
        cursor: Active database cursor.
        db: The database.
        survey_id: Primary key of the survey.

    Returns:
        The FeatureCollection, with no features when nothing is georeferenced.
    """
    stmt = sql.SQL("""
        WITH tiles AS (
            SELECT ra.image_id,
                   COUNT(*) AS tiles,
                   COUNT(*) FILTER (
                       WHERE ra.reviewed_by_user_id <> 0
                   ) AS tiles_reviewed
            FROM core.reviewed_area ra
            JOIN core.images i ON i.image_id = ra.image_id
            WHERE i.survey_id = %(survey_id)s
              AND ra.type = %(tile_type)s
            GROUP BY ra.image_id
        )
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(feature), '[]'::json)
        )
        FROM (
            SELECT json_build_object(
                'type', 'Feature',
                'id', i.image_id,
                'geometry', ST_AsGeoJSON(
                    ST_SimplifyPreserveTopology(f.footprint, %(tolerance)s),
                    %(digits)s
                )::json,
                'properties', json_build_object(
                    'image_id', i.image_id,
                    'image_uuid', i.uuid,
                    'name', i.name,
                    'area_m2', f.area_m2,
                    'bbox_wsen', f.bbox_wsen,
                    'tiles', COALESCE(t.tiles, 0),
                    'tiles_reviewed', COALESCE(t.tiles_reviewed, 0)
                )
            ) AS feature
            FROM core.image_footprints f
            JOIN core.images i ON i.image_id = f.image_id
            LEFT JOIN tiles t ON t.image_id = i.image_id
            WHERE i.survey_id = %(survey_id)s
              AND f.footprint IS NOT NULL
            ORDER BY i.image_id ASC
        ) features;
    """)

    cursor.row_factory = tuple_row
    cursor.execute(
        stmt,
        {
            "survey_id": survey_id,
            "tile_type": ActivityType.ACTIVE_MEASUREMENT,
            "tolerance": SIMPLIFY_DEGREES,
            "digits": COORDINATE_DIGITS,
        },
    )
    row = cursor.fetchone()
    return row[0] if row else {"type": "FeatureCollection", "features": []}


# ---------------------------------------------------------------------------------------------------------------------------
# Placing boxes on the ground


def ground_position(gcps: list[list[float]]) -> Locator | None:
    """Returns a function from image pixels to longitude and latitude.

    It interpolates the ground control points and falls back to the nearest
    one outside their hull.

    Args:
        gcps: Ground control points as (row, column, longitude, latitude).

    Returns:
        The function, or None with fewer than three finite points.
    """
    points = np.asarray(gcps, dtype=float).reshape(-1, 4)
    points = points[np.isfinite(points).all(axis=1)]
    if len(points) < 3:
        return None

    pixels, ground = points[:, [1, 0]], points[:, [2, 3]]
    linear = LinearNDInterpolator(pixels, ground)
    nearest = NearestNDInterpolator(pixels, ground)

    def position(column: float, row: float) -> tuple[float, float]:
        lon, lat = linear(column, row)
        if not (np.isfinite(lon) and np.isfinite(lat)):
            lon, lat = nearest(column, row)
        return float(lon), float(lat)

    return position


def locators(
    cursor: Cursor[Any],
    image_ids: list[int],
) -> dict[int, Locator | None]:
    """Returns each image's function from pixels to longitude and latitude.

    Args:
        cursor: Active database cursor.
        image_ids: Primary keys of the images.

    Returns:
        The function of each image's latest footprint (`ground_position`),
        None or missing where it has no ground control.
    """
    image_ids = sorted(set(image_ids))
    found: dict[int, Locator | None] = {}

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
            found[row["image_id"]] = ground_position(row["gcps"])
    return found


def locate(
    rows: list[dict[str, Any]],
    found: dict[int, Locator | None],
) -> list[tuple[float, float] | None]:
    """Returns the longitude and latitude of each row's box center.

    Args:
        rows: Boxes with image_id, center_x and center_y in image pixels.
        found: The `locators` of the rows' images.

    Returns:
        One position per row, None where its image has no ground control.
    """
    positions: list[tuple[float, float] | None] = []
    for row in rows:
        if (position := found.get(row["image_id"])) is None:
            positions.append(None)
            continue
        positions.append(
            position(float(row["center_x"]), float(row["center_y"]))
        )
    return positions


def outline(
    rows: list[dict[str, Any]],
    found: dict[int, Locator | None],
) -> list[list[float] | None]:
    """Returns the corners of each row's box on the ground.

    The corners are placed through the image's ground control points, the
    mapping its overlay is drawn with, so they lie on the drawn image.

    Args:
        rows: Boxes with image_id and box_tx, box_ty, box_bx and box_by in
            image pixels.
        found: The `locators` of the rows' images.

    Returns:
        One box per row as the longitude and latitude of its top left, top
        right, bottom right and bottom left corners, flattened; None where its
        image has no ground control.
    """
    corners: list[list[float] | None] = []
    for row in rows:
        if (position := found.get(row["image_id"])) is None:
            corners.append(None)
            continue
        left, right = sorted((float(row["box_tx"]), float(row["box_bx"])))
        top, bottom = sorted((float(row["box_ty"]), float(row["box_by"])))
        around = ((left, top), (right, top), (right, bottom), (left, bottom))
        corners.append([value for x, y in around for value in position(x, y)])
    return corners


# ---------------------------------------------------------------------------------------------------------------------------
# Detections


def annotated(
    cursor: Cursor[Any],
    measurement: ActiveMeasurement,
) -> list[dict[str, Any]]:
    """Returns the annotations of the measurement's label on its reviewed tiles.

    Args:
        cursor: Active database cursor.
        measurement: The active measurement.

    Returns:
        Each annotation's image, tile, box center and box in image pixels.
    """
    stmt = sql.SQL("""
        SELECT DISTINCT ON (a.annotation_id)
            a.image_id,
            t.reviewed_area_id,
            (a.box_tx + a.box_bx) / 2.0 AS center_x,
            (a.box_ty + a.box_by) / 2.0 AS center_y,
            a.box_tx, a.box_ty, a.box_bx, a.box_by
        FROM core.annotations a
        JOIN core.annotations_reviewed_area x
            ON x.annotation_id = a.annotation_id
        JOIN core.reviewed_area t ON t.reviewed_area_id = x.reviewed_area_id
        JOIN core.am_units u ON u.reviewed_area_id = t.reviewed_area_id
        WHERE u.active_measurement_id = %(active_measurement_id)s
          AND t.reviewed_by_user_id <> 0
          AND a.label_id = %(label_id)s
        ORDER BY a.annotation_id ASC, t.reviewed_area_id ASC;
    """)

    cursor.row_factory = dict_row
    cursor.execute(
        stmt,
        {
            "active_measurement_id": measurement.active_measurement_id,
            "label_id": measurement.label_id,
        },
    )
    return cursor.fetchall()


def get_annotated_boxes(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    image_id: int,
) -> list[list[int]]:
    """Returns the boxes of an image's annotated animals.

    Args:
        cursor: Active database cursor.
        db: The database.
        measurement: The active measurement.
        image_id: Primary key of the image.

    Returns:
        The boxes of the measurement's label on its reviewed tiles of the
        image, in image pixels (left, top, right, bottom).
    """
    return [
        [int(row[key]) for key in PIXELS]
        for row in annotated(cursor, measurement)
        if row["image_id"] == image_id
    ]


def reviewed_tiles(
    cursor: Cursor[Any],
    measurement: ActiveMeasurement,
) -> set[int]:
    """Returns the reviewed areas of the measurement's reviewed units.

    Args:
        cursor: Active database cursor.
        measurement: The active measurement.

    Returns:
        Their primary keys.
    """
    cursor.row_factory = tuple_row
    cursor.execute(
        sql.SQL("""
            SELECT u.reviewed_area_id
            FROM core.am_units u
            JOIN core.reviewed_area ra
                ON ra.reviewed_area_id = u.reviewed_area_id
            WHERE u.active_measurement_id = %(active_measurement_id)s
              AND ra.reviewed_by_user_id <> 0;
        """),
        {"active_measurement_id": measurement.active_measurement_id},
    )
    return {row[0] for row in cursor.fetchall()}


def candidates(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    threshold: float,
) -> list[dict[str, Any]]:
    """Returns the detector's boxes that may stand in for unseen animals.

    The boxes of the survey's detector, of the measurement's label and at or
    above `threshold`, whose center lies on one of the survey's tiles.

    Args:
        cursor: Active database cursor.
        db: The database.
        measurement: The active measurement.
        threshold: The lowest score kept, the measurement's draft threshold.

    Returns:
        Each box's prediction, image, tile, score, box and center in
        pixels, highest score first.
    """
    detector = get_detection_model(cursor, db, measurement.survey_id)

    stmt = sql.SQL("""
        SELECT p.uuid AS prediction_uuid, p.image_id, p.score,
               t.reviewed_area_id,
               p.box_tx, p.box_ty, p.box_bx, p.box_by,
               (p.box_tx + p.box_bx) / 2.0 AS center_x,
               (p.box_ty + p.box_by) / 2.0 AS center_y
        FROM core.predictions p
        JOIN core.images i ON i.image_id = p.image_id
        JOIN projectmanagement.labels l ON l.label = p.label
        JOIN core.reviewed_area t ON t.image_id = p.image_id
            AND t.type = %(tile_type)s
            AND (p.box_tx + p.box_bx) / 2.0 >= t.area_tx
            AND (p.box_tx + p.box_bx) / 2.0 < t.area_bx
            AND (p.box_ty + p.box_by) / 2.0 >= t.area_ty
            AND (p.box_ty + p.box_by) / 2.0 < t.area_by
        WHERE i.survey_id = %(survey_id)s
          AND p.model_id = %(model_id)s
          AND l.label_id = %(label_id)s
          AND p.score >= %(threshold)s
        ORDER BY p.score DESC, p.pred_id ASC;
    """)

    cursor.row_factory = dict_row
    cursor.execute(
        stmt,
        {
            "survey_id": measurement.survey_id,
            "model_id": detector.model_id,
            "label_id": measurement.label_id,
            "tile_type": ActivityType.ACTIVE_MEASUREMENT,
            "threshold": threshold,
        },
    )
    return cursor.fetchall()


def place_estimated(
    boxes: list[dict[str, Any]],
    expected: dict[int, float],
    n: int,
) -> list[dict[str, Any]]:
    """Picks the `n` boxes that stand in for the animals on unreviewed tiles.

    Args:
        boxes: Candidates with reviewed_area_id and score, highest score
            first.
        expected: The proposal's expected count per tile.
        n: How many to pick.

    Returns:
        The picked boxes, at most `n` and at most all of them.
    """
    n = max(0, min(n, len(boxes)))
    if n == 0:
        return []

    by_tile: dict[int, list[dict[str, Any]]] = {}
    for box in boxes:
        by_tile.setdefault(box["reviewed_area_id"], []).append(box)

    order = sorted(
        by_tile,
        key=lambda tile: (-expected.get(tile, 0.0), -by_tile[tile][0]["score"]),
    )

    picked: list[dict[str, Any]] = []
    for tile in order:
        room = max(1, ceil(expected.get(tile, 0.0)))
        picked.extend(by_tile[tile][: min(room, n - len(picked))])
        if len(picked) >= n:
            return picked

    taken = {id(box) for box in picked}
    rest = [box for box in boxes if id(box) not in taken]
    return picked + rest[: n - len(picked)]


class Shown(NamedTuple):
    """The animals the map shows at an estimated count.

    Attributes:
        annotated: The annotations on the reviewed tiles, each with its
            position (None where its image has no ground control).
        picked: Indices of the placed boxes standing in for the animals on
            the tiles not reviewed.
        wanted: How many boxes the estimated count asked for.
    """

    annotated: list[dict[str, Any]]
    picked: list[int]
    wanted: int


def shown(
    cursor: Cursor[Any],
    measurement: ActiveMeasurement,
    state: MeasurementState,
    boxes: PlacedBoxes,
    count: float | None,
) -> Shown:
    """Returns the animals the map shows at an estimated count of `count`.

    Args:
        cursor: Active database cursor.
        measurement: The active measurement.
        state: Its serving state, for the expected count per tile.
        boxes: The detector's boxes at the draft threshold, on the ground.
        count: The running estimate, None before any review.

    Returns:
        The annotated animals and the boxes picked for the rest.
    """
    seen = annotated(cursor, measurement)
    found = locators(cursor, [row["image_id"] for row in seen])
    for row, at, corners in zip(
        seen, locate(seen, found), outline(seen, found)
    ):
        row["lon"], row["lat"] = at if at is not None else (None, None)
        row["corners"] = corners

    reviewed = reviewed_tiles(cursor, measurement)
    unseen = [
        {"at": at, "reviewed_area_id": int(unit), "score": float(score)}
        for at, (unit, score) in enumerate(
            zip(boxes.reviewed_area_ids, boxes.scores)
        )
        if int(unit) not in reviewed
    ]
    expected = dict(zip(state.reviewed_area_ids, map(float, state.raw)))
    wanted = int(round(max(0.0, (count or 0.0) - len(seen))))
    picked = place_estimated(unseen, expected, wanted)

    return Shown(seen, [box["at"] for box in picked], wanted)


def covering(
    cursor: Cursor[Any],
    survey_id: int,
    image_of: list[int],
    positions: list[tuple[float, float]],
) -> np.ndarray:
    """Returns how many images other than its own cover each animal.

    An image covers an animal when its latest footprint contains the
    animal's longitude and latitude. The footprints have no spatial index,
    so they are read once and searched with a tree here.

    Args:
        cursor: Active database cursor.
        survey_id: Primary key of the survey.
        image_of: The image each animal was placed from.
        positions: Each animal's longitude and latitude.

    Returns:
        The number of other images covering each animal.
    """
    if not positions:
        return np.zeros(0)

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


def _pairs(corners: list[float]) -> list[list[float]]:
    """Returns flattened corners as [longitude, latitude] pairs."""
    return [corners[at : at + 2] for at in range(0, len(corners), 2)]


def get_detections(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    state: MeasurementState,
    boxes: PlacedBoxes,
    threshold: float,
    count: float | None,
) -> dict[str, Any]:
    """Returns the detections the map shows for the measurement.

    Args:
        cursor: Active database cursor.
        db: The database.
        measurement: The active measurement.
        state: Its serving state.
        boxes: The detector's boxes at the draft threshold, on the ground.
        threshold: The draft threshold.
        count: The running estimate, None before any review.

    Returns:
        How many are annotated, estimated and left unplaced (no box was left
        to stand in for them), the threshold, and each detection with its
        image, tile, kind, score and prediction (estimated only), box in
        pixels (annotated only), position, the box's corners on the ground
        and overlap weight.
    """
    on_map = shown(cursor, measurement, state, boxes, count)

    detections = [
        {
            "image_id": row["image_id"],
            "reviewed_area_id": row["reviewed_area_id"],
            "kind": "annotated",
            "score": None,
            "prediction_uuid": None,
            "box": [int(row[key]) for key in PIXELS],
            "lon": row["lon"],
            "lat": row["lat"],
            "corners": _pairs(row["corners"]),
        }
        for row in on_map.annotated
        if row["lon"] is not None
    ] + [
        {
            "image_id": int(boxes.image_ids[at]),
            "reviewed_area_id": int(boxes.reviewed_area_ids[at]),
            "kind": "estimated",
            "score": float(boxes.scores[at]),
            "prediction_uuid": boxes.prediction_uuids[at],
            "box": None,
            "lon": float(boxes.lon[at]),
            "lat": float(boxes.lat[at]),
            "corners": _pairs(boxes.corners[at].tolist()),
        }
        for at in on_map.picked
    ]

    # Each detection's overlap weight: 1 / the images covering it
    weights = coverage_weights(
        covering(
            cursor,
            measurement.survey_id,
            [d["image_id"] for d in detections],
            [(d["lon"], d["lat"]) for d in detections],
        )
    )
    for detection, weight in zip(detections, weights.tolist()):
        detection["weight"] = weight

    return {
        "annotated": len(on_map.annotated),
        "estimated": len(on_map.picked),
        "unplaced": max(0, on_map.wanted - len(on_map.picked)),
        "threshold": threshold,
        "detections": detections,
    }


# ---------------------------------------------------------------------------------------------------------------------------
# Overlays


def get_overlay_source(
    cursor: Cursor[Any],
    db: "Database",
    image_id: int,
) -> dict[str, Any] | None:
    """Returns what drawing an image onto the ground needs.

    Args:
        cursor: Active database cursor.
        db: The database.
        image_id: Primary key of the image.

    Returns:
        Its latest footprint's id, bounding box (west, south, east, north),
        ground control points, stored overlay key and outline (WKB), or None
        when the footprint has no ground control to draw with.

    Raises:
        ObjectNotFound: The image has no footprint.
    """
    stmt = sql.SQL("""
        SELECT f.footprint_id, f.bbox_wsen, f.gcps, f.overlay_uri,
               ST_AsBinary(f.footprint) AS footprint
        FROM core.image_footprints f
        WHERE f.image_id = %(image_id)s
        ORDER BY f.footprint_id DESC
        LIMIT 1;
    """)

    cursor.row_factory = dict_row
    cursor.execute(stmt, {"image_id": image_id})

    if not (source := cursor.fetchone()):
        raise ObjectNotFound("ImageFootprint", f"image {image_id}")

    if not source["gcps"] or len(source["bbox_wsen"]) != 4:
        return None
    return source


def set_overlay_key(
    cursor: Cursor[Any],
    db: "Database",
    footprint_id: int,
    key: str,
) -> None:
    """Records the bucket key an image's overlay is stored under.

    Args:
        cursor: Active database cursor.
        db: The database.
        footprint_id: Primary key of the footprint drawn.
        key: The overlay's bucket key.
    """
    cursor.execute(
        sql.SQL("""
            UPDATE core.image_footprints
            SET overlay_uri = %(key)s, modified = CURRENT_TIMESTAMP
            WHERE footprint_id = %(footprint_id)s;
        """),
        {"key": key, "footprint_id": footprint_id},
    )
