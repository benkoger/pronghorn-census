# Survey Map Specialized Database Operations
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# What the survey map draws, read from what is stored:
#
#   get_footprints(survey)   -> GeoJSON of the survey's image footprints
#   get_detections(...)      -> the detections the map shows, placed on the ground
#
# Only the abundance estimation workflow feeds the map, so it shows no detection until tiles have
# been reviewed. The detections shown are
#
#   annotated   the annotations on the measurement's reviewed tiles, and
#   estimated   N boxes of the survey's detector standing in for the animals on the tiles not
#               reviewed, where N = round(estimated count - animals annotated).
#
# The N boxes are placed where the proposal expects animals: unreviewed tiles are visited in
# descending expected count, each giving up to ceil(expected count) of its highest scoring
# boxes; if that does not place all N, the rest are the highest scoring boxes left. Boxes on
# reviewed tiles are never shown as estimated: the annotations carry those tiles' animals.
#   get_overlay_source(image) -> what is needed to draw an image onto the ground
#   set_overlay_key(...)     -> record where an image's overlay is stored
#
# An annotation is a box in image pixels. It is placed on the ground with the footprint's ground
# control points: a grid of (row, column, longitude, latitude) over the image.
# ---------------------------------------------------------------------------------------------------------------------------

from math import ceil
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import psycopg.sql as sql
from psycopg import Cursor
from psycopg.rows import dict_row, tuple_row
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator

from database.errors import ObjectNotFound
from database.object_models.base import Keyring
from database.modules.activemeasurement import get_detection_model
from database.object_models.core.activity import ActivityType
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
)

if TYPE_CHECKING:
    from database.database import Database

# ---------------------------------------------------------------------------------------------------------------------------

SIMPLIFY_DEGREES = 0.00001  # about one meter: footprint outlines are drawn, not measured
COORDINATE_DIGITS = 6
DETECTION_THRESHOLD = 0.05  # detector boxes below this score are never shown
STORED_OVERLAY = "images/%%"  # overlay_uri holds a bucket key once the overlay is stored there
IMAGES_PER_STATEMENT = 250  # ground control is read this many images at a time

# ---------------------------------------------------------------------------------------------------------------------------


def get_footprints(
    cursor: Cursor[Any],
    db: "Database",
    survey_ids: Keyring,
) -> dict[str, Any]:
    """
    Returns the survey's footprints as a GeoJSON FeatureCollection. Each feature carries the
    image it belongs to, its area, the box its overlay covers, and how many of its tiles have
    been reviewed.
    """
    stmt = sql.SQL("""
        WITH tiles AS (
            SELECT ra.image_id,
                   COUNT(*) AS tiles,
                   COUNT(*) FILTER (WHERE ra.reviewed_by_user_id <> 0) AS tiles_reviewed
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
                    ST_SimplifyPreserveTopology(f.footprint, %(tolerance)s), %(digits)s
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
            "survey_id": survey_ids.pkey,
            "tile_type": ActivityType.ACTIVE_MEASUREMENT,
            "tolerance": SIMPLIFY_DEGREES,
            "digits": COORDINATE_DIGITS,
        },
    )
    res = cursor.fetchone()
    return res[0] if res else {"type": "FeatureCollection", "features": []}


# ---------------------------------------------------------------------------------------------------------------------------


def _ground_position(gcps: list[list[float]]):
    """
    Returns a function from image pixels (column, row) to (longitude, latitude), interpolating
    the ground control points and falling back to the nearest one outside their hull.
    """
    points = np.asarray(gcps, dtype=float)
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


def _annotated(
    cursor: Cursor[Any],
    measurement: ActiveMeasurement,
) -> list[dict[str, Any]]:
    """The annotations of the measurement's label on its reviewed tiles."""
    stmt = sql.SQL("""
        SELECT DISTINCT ON (a.annotation_id)
            a.image_id,
            (a.box_tx + a.box_bx) / 2.0 AS center_x,
            (a.box_ty + a.box_by) / 2.0 AS center_y,
            a.box_tx, a.box_ty, a.box_bx, a.box_by
        FROM core.annotations a
        JOIN core.annotations_reviewed_area x ON x.annotation_id = a.annotation_id
        JOIN core.reviewed_area t ON t.reviewed_area_id = x.reviewed_area_id
        JOIN core.am_units u ON u.reviewed_area_id = t.reviewed_area_id
        WHERE u.active_measurement_id = %(active_measurement_id)s
          AND t.reviewed_by_user_id <> 0
          AND a.label_id = %(label_id)s
        ORDER BY a.annotation_id ASC;
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


def _candidates(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    reviewed: bool = True,
) -> list[dict[str, Any]]:
    """
    The boxes of the survey's detector, of the measurement's label and at or above
    DETECTION_THRESHOLD, whose center lies on a tile that the measurement has not reviewed.
    With `reviewed` False the review is ignored and every tile's boxes are returned.
    """
    detector = get_detection_model(cursor, db, measurement.survey_id)

    stmt = sql.SQL("""
        SELECT p.image_id, p.score, t.reviewed_area_id,
               (p.box_tx + p.box_bx) / 2.0 AS center_x,
               (p.box_ty + p.box_by) / 2.0 AS center_y,
               p.box_tx, p.box_ty, p.box_bx, p.box_by
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
          AND NOT (
              %(reviewed)s
              AND t.reviewed_by_user_id <> 0
              AND EXISTS (
                  SELECT 1 FROM core.am_units u
                  WHERE u.active_measurement_id = %(active_measurement_id)s
                    AND u.reviewed_area_id = t.reviewed_area_id
              )
          )
        ORDER BY p.score DESC, p.pred_id ASC;
    """)

    cursor.row_factory = dict_row
    cursor.execute(
        stmt,
        {
            "survey_id": measurement.survey_id,
            "model_id": detector.model_id,
            "label_id": measurement.label_id,
            "active_measurement_id": measurement.active_measurement_id,
            "tile_type": ActivityType.ACTIVE_MEASUREMENT,
            "threshold": DETECTION_THRESHOLD,
            "reviewed": reviewed,
        },
    )
    return cursor.fetchall()


def place_estimated(
    candidates: list[dict[str, Any]],
    expected: dict[int, float],
    n: int,
) -> list[dict[str, Any]]:
    """
    Picks the `n` candidates that stand in for the animals on the tiles not reviewed.
    `candidates` are ordered by descending score; `expected` is the proposal's expected count
    per tile.
    """
    n = max(0, min(n, len(candidates)))
    if n == 0:
        return []

    by_tile: dict[int, list[dict[str, Any]]] = {}
    for candidate in candidates:
        by_tile.setdefault(candidate["reviewed_area_id"], []).append(candidate)

    order = sorted(
        by_tile,
        key=lambda tile: (-expected.get(tile, 0.0), -by_tile[tile][0]["score"]),
    )

    picked: list[dict[str, Any]] = []
    for tile in order:
        room = max(1, ceil(expected.get(tile, 0.0)))
        for candidate in by_tile[tile][:room]:
            if len(picked) >= n:
                break
            picked.append(candidate)
        if len(picked) >= n:
            break

    if len(picked) < n:
        taken = {id(candidate) for candidate in picked}
        rest = [candidate for candidate in candidates if id(candidate) not in taken]
        picked += rest[: n - len(picked)]

    return picked


def get_detections(
    cursor: Cursor[Any],
    db: "Database",
    measurement: ActiveMeasurement,
    expected: dict[int, float],
    estimated_count: Optional[float],
    reviewed: bool = True,
) -> dict[str, Any]:
    """
    Returns the detections the map shows for the measurement, each with the image it is on,
    whether it is annotated or estimated, its score (estimated only), its box in image pixels
    and its position on the ground. `expected` is the proposal's expected count per tile;
    `estimated_count` is the running estimate, or None before any tile has been reviewed. With
    `reviewed` False the review is ignored, so every detection is an estimated one.
    """
    annotated = _annotated(cursor, measurement) if reviewed else []

    mass = max(0.0, (estimated_count or 0.0) - len(annotated))
    n_estimated = int(round(mass))
    estimated = (
        place_estimated(_candidates(cursor, db, measurement, reviewed), expected, n_estimated)
        if n_estimated > 0
        else []
    )

    shown = [{**row, "kind": "annotated", "score": None} for row in annotated]
    shown += [{**row, "kind": "estimated", "score": float(row["score"])} for row in estimated]

    position = {}
    image_ids = sorted({row["image_id"] for row in shown})
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
            position[row["image_id"]] = _ground_position(row["gcps"])

    detections = []
    for row in shown:
        if (locate := position.get(row["image_id"])) is None:
            continue
        lon, lat = locate(float(row["center_x"]), float(row["center_y"]))
        detections.append(
            {
                "image_id": row["image_id"],
                "kind": row["kind"],
                "score": row["score"],
                "box": [int(row[key]) for key in ("box_tx", "box_ty", "box_bx", "box_by")],
                "lon": lon,
                "lat": lat,
            }
        )

    return {
        "annotated": len(annotated),
        "estimated": len(estimated),
        "unplaced": max(0, n_estimated - len(estimated)),
        "detections": detections,
    }


# ---------------------------------------------------------------------------------------------------------------------------


def get_overlay_source(
    cursor: Cursor[Any],
    db: "Database",
    image_id: int,
) -> Optional[dict[str, Any]]:
    """
    Returns what drawing an image onto the ground needs: its latest footprint's bounding box
    (west, south, east, north) and ground control points. None when it has no footprint.
    """
    stmt = sql.SQL("""
        SELECT f.footprint_id, f.bbox_wsen, f.gcps, f.overlay_uri
        FROM core.image_footprints f
        WHERE f.image_id = %(image_id)s
        ORDER BY f.footprint_id DESC
        LIMIT 1;
    """)

    cursor.row_factory = dict_row
    cursor.execute(stmt, {"image_id": image_id})

    if not (source := cursor.fetchone()):
        raise ObjectNotFound("ImageFootprint", f"image {image_id}")

    return source if source["gcps"] and len(source["bbox_wsen"]) == 4 else None


def set_overlay_key(
    cursor: Cursor[Any],
    db: "Database",
    footprint_id: int,
    key: str,
) -> None:
    """Records the bucket key an image's overlay is stored under."""
    cursor.execute(
        sql.SQL("""
            UPDATE core.image_footprints
            SET overlay_uri = %(key)s, modified = CURRENT_TIMESTAMP
            WHERE footprint_id = %(footprint_id)s;
        """),
        {"key": key, "footprint_id": footprint_id},
    )

