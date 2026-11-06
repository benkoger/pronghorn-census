# Reset a survey's abundance estimation: its review, measurement and leftovers
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# Run INSIDE the API container, from /app:
#
#     .venv/bin/python -m tools.reset_measurement <survey name or uuid> \
#         --confirm <survey name>
#
# With --dry-run the database changes are rolled back and nothing outside it
# is touched; the output says what a real run would remove.
#
# In one transaction, it deletes the annotations of type 'active measurement'
# on the survey's tiles, deletes the survey's active measurement(s) (their
# units and proposal generations go with them), marks the survey's tiles
# unreviewed and sets the survey back to 'preparing'. Annotations and reviewed
# areas of every other type are counted before and after; a change rolls
# everything back.
#
# With --drop-tiles the survey's tiles themselves are deleted too, with their
# crops in the bucket and their permission records, so that the next
# preparation cuts them afresh (needed whenever the tile grid changes). Refused
# when a tile carries an annotation of another type or a training row, since
# those would go with it. This option is for the TEST stack only; it refuses to
# run unless the bucket is a test bucket.
#
# It then removes what is stored outside the database: the measurement's
# serving state and terms in the cache, and its permission relationships and
# those of its units.
#
# It refuses to run unless --confirm repeats the survey's name, and warns when
# the bucket does not look like a test bucket.
# ---------------------------------------------------------------------------------------------------------------------------

import argparse
import os
import sys
from typing import Any

from authzed.api.v1 import (
    Consistency,
    DeleteRelationshipsRequest,
    ReadRelationshipsRequest,
    RelationshipFilter,
)
from botocore.exceptions import ClientError
from flask import current_app
from psycopg import Cursor
from psycopg.rows import dict_row, tuple_row

from app import create_app
from app.extensions import base, cache, s3
from database.database import Database
from database.object_models.core.activity import ActivityType

# ---------------------------------------------------------------------------------------------------------------------------

# Permission record types whose rows the reset removes.
STORED = ("am_unit", "active_measurement")
# Tiles are dropped one batch of images per statement.
IMAGES_PER_STATEMENT = 250
# Cache keys of a measurement, by uuid.
CACHE_KEYS = ("am_state_{uuid}", "am_terms_{uuid}", "am_area_{uuid}")


class Refused(Exception):
    pass


class DryRun(Exception):
    """Raised at the end of a dry run so that the transaction rolls back."""

    def __init__(self, removed: dict[str, Any]):
        self.removed = removed


def _counts(cursor: Cursor[Any]) -> tuple[int, int, int]:
    """Other-type annotations, other-type reviewed areas reviewed, and tiles."""
    cursor.row_factory = tuple_row
    cursor.execute(
        """
        SELECT
            (SELECT count(*) FROM core.annotations WHERE type <> %(type)s),
            (SELECT count(*) FROM core.reviewed_area
             WHERE type <> %(type)s AND reviewed_by_user_id <> 0),
            (SELECT count(*) FROM core.reviewed_area WHERE type = %(type)s);
        """,
        {"type": ActivityType.ACTIVE_MEASUREMENT},
    )
    return cursor.fetchone()  # type: ignore[return-value]


def clear_review(
    cursor: Cursor[Any],
    db: Database,
    survey: str,
    confirm: str,
    dry_run: bool = False,
    drop_tiles: bool = False,
) -> dict[str, Any]:
    """The database part, in the caller's transaction.

    Returns:
        What was removed.
    """
    cursor.row_factory = dict_row
    cursor.execute(
        """
        SELECT survey_id, name, uuid FROM projectmanagement.surveys
        WHERE name = %(s)s OR uuid::text = %(s)s;
        """,
        {"s": survey},
    )
    if (row := cursor.fetchone()) is None:
        raise Refused(f"no survey named {survey}")
    if confirm != row["name"]:
        raise Refused(f"--confirm must repeat the survey's name: {row['name']}")

    before = _counts(cursor)
    cursor.row_factory = tuple_row
    cursor.execute(
        """
        SELECT uuid FROM projectmanagement.active_measurements
        WHERE survey_id = %(survey_id)s;
        """,
        {"survey_id": row["survey_id"]},
    )
    measurements = [str(m[0]) for m in cursor.fetchall()]

    params = {
        "survey_id": row["survey_id"],
        "type": ActivityType.ACTIVE_MEASUREMENT,
    }

    cursor.execute(
        """
        DELETE FROM core.annotations a
        USING core.annotations_reviewed_area x, core.reviewed_area t,
              core.images i
        WHERE x.annotation_id = a.annotation_id
          AND t.reviewed_area_id = x.reviewed_area_id
          AND i.image_id = t.image_id
          AND i.survey_id = %(survey_id)s
          AND a.type = %(type)s
          AND t.type = %(type)s;
        """,
        params,
    )
    annotations = cursor.rowcount

    cursor.execute(
        """
        DELETE FROM projectmanagement.active_measurements
        WHERE survey_id = %(survey_id)s;
        """,
        params,
    )
    cursor.execute(
        """
        UPDATE core.reviewed_area t SET reviewed_by_user_id = 0
        FROM core.images i
        WHERE i.image_id = t.image_id
          AND i.survey_id = %(survey_id)s
          AND t.type = %(type)s
          AND t.reviewed_by_user_id <> 0;
        """,
        params,
    )
    tiles = cursor.rowcount

    dropped: list[tuple[str, str]] = []
    if drop_tiles:
        dropped = _drop_tiles(cursor, params)

    cursor.execute(
        """
        UPDATE projectmanagement.surveys SET status = 'preparing'
        WHERE survey_id = %(survey_id)s;
        """,
        params,
    )

    after = _counts(cursor)
    kept = slice(0, 2) if drop_tiles else slice(0, 3)
    if after[kept] != before[kept]:
        raise Refused(
            "annotations or reviewed areas of another type changed; rolled back"
        )

    removed = {
        "survey": row["name"],
        "measurements": measurements,
        "annotations": annotations,
        "tiles": tiles,
        "dropped": dropped,
    }
    if dry_run:
        raise DryRun(removed)
    return removed


def _drop_tiles(
    cursor: Cursor[Any], params: dict[str, Any]
) -> list[tuple[str, str]]:
    """Deletes the survey's tiles; returns their uuids and crop keys."""
    cursor.execute(
        """
        SELECT
            (SELECT count(*) FROM core.annotations_reviewed_area x
             JOIN core.annotations a ON a.annotation_id = x.annotation_id
             JOIN core.reviewed_area t
               ON t.reviewed_area_id = x.reviewed_area_id
             JOIN core.images i ON i.image_id = t.image_id
             WHERE i.survey_id = %(survey_id)s AND t.type = %(type)s
               AND a.type <> %(type)s),
            (SELECT count(*) FROM core.training tr
             JOIN core.reviewed_area t
               ON t.reviewed_area_id = tr.reviewed_area_id
             JOIN core.images i ON i.image_id = t.image_id
             WHERE i.survey_id = %(survey_id)s AND t.type = %(type)s);
        """,
        params,
    )
    other_annotations, training = cursor.fetchone()
    if other_annotations or training:
        raise Refused(
            f"{other_annotations} annotation(s) of another type and "
            f"{training} training row(s) sit on the survey's tiles; not "
            "dropping them"
        )

    # One statement per batch of images: the foreign-key checks on every tile
    # row outlast the statement timeout when a survey's worth of tiles goes in
    # one statement.
    cursor.execute(
        """
        SELECT image_id FROM core.images WHERE survey_id = %(survey_id)s
        ORDER BY image_id;
        """,
        params,
    )
    image_ids = [r[0] for r in cursor.fetchall()]

    dropped: list[tuple[str, str]] = []
    for start in range(0, len(image_ids), IMAGES_PER_STATEMENT):
        cursor.execute(
            """
            DELETE FROM core.reviewed_area t
            WHERE t.image_id = ANY(%(image_ids)s)
              AND t.type = %(type)s
            RETURNING t.uuid, t.ra_key;
            """,
            {
                "image_ids": image_ids[start : start + IMAGES_PER_STATEMENT],
                "type": params["type"],
            },
        )
        dropped.extend((str(u), k) for u, k in cursor.fetchall())
    return dropped


def clear_storage(
    measurements: list[str], dropped: list[tuple[str, str]] = ()
) -> dict[str, int]:
    """The cache and permission records of the removed measurements.

    Also the crops and permission records of the dropped tiles.
    """
    bucket = current_app.config["BUCKET_NAME"]

    for uuid in measurements:
        for key in CACHE_KEYS:
            cache.delete(key.format(uuid=uuid))

    def stored(cursor: Cursor[Any], db: Database) -> dict[str, set[str]]:
        cursor.row_factory = tuple_row
        out = {}
        for kind, table in (
            ("am_unit", "core.am_units"),
            ("active_measurement", "projectmanagement.active_measurements"),
        ):
            cursor.execute(f"SELECT uuid FROM {table};")
            out[kind] = {str(r[0]) for r in cursor.fetchall()}
        return out

    client = base._spice_client
    full = Consistency(fully_consistent=True)
    files = 0
    relationships = 0

    for uid, key in dropped:
        if key:
            try:
                s3.head_object(Bucket=bucket, Key=key)
            except ClientError:
                pass
            else:
                s3.delete_object(Bucket=bucket, Key=key)
                files += 1
        client.DeleteRelationships(
            DeleteRelationshipsRequest(
                relationship_filter=RelationshipFilter(
                    resource_type="reviewed_area", optional_resource_id=uid
                )
            )
        )
        relationships += 1

    for kind, keep in base.execute(stored).items():
        ids = {
            r.relationship.resource.object_id
            for r in client.ReadRelationships(
                ReadRelationshipsRequest(
                    consistency=full,
                    relationship_filter=RelationshipFilter(resource_type=kind),
                )
            )
        }
        for uid in ids - keep:
            client.DeleteRelationships(
                DeleteRelationshipsRequest(
                    relationship_filter=RelationshipFilter(
                        resource_type=kind, optional_resource_id=uid
                    )
                )
            )
            relationships += 1

    return {"files": files, "relationships": relationships}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("survey", help="the survey's name or uuid")
    parser.add_argument(
        "--confirm", required=True, help="the survey's name, repeated"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="report only; change nothing"
    )
    parser.add_argument(
        "--drop-tiles",
        action="store_true",
        help="also delete the survey's tiles, crops and permission records",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        bucket = current_app.config["BUCKET_NAME"]
        print(f"database {os.environ.get('DB_NAME', '?')}, bucket {bucket}")
        if "test" not in bucket:
            print(
                "WARNING: the bucket does not look like a test bucket",
                file=sys.stderr,
            )
            if args.drop_tiles:
                print(
                    "refused: --drop-tiles runs against the test stack only",
                    file=sys.stderr,
                )
                return 1
        try:
            removed = base.execute(
                clear_review,
                args.survey,
                args.confirm,
                args.dry_run,
                args.drop_tiles,
            )
        except Refused as error:
            print(f"refused: {error}", file=sys.stderr)
            return 1
        except DryRun as dry:
            removed = dry.removed
            print(
                f"dry run, {removed['survey']}: would remove "
                f"{len(removed['measurements'])} measurement(s), "
                f"{removed['annotations']} review annotations, "
                f"{removed['tiles']} reviewed tiles, and their cache entries "
                "and permission records"
                + (
                    f"; would drop {len(removed['dropped'])} tiles with "
                    "their crops"
                    if args.drop_tiles
                    else ""
                )
            )
            return 0
        print(
            f"{removed['survey']}: removed {len(removed['measurements'])} "
            f"measurement(s), {removed['annotations']} review annotations, "
            f"{removed['tiles']} reviewed tiles"
            + (
                f", dropped {len(removed['dropped'])} tiles"
                if removed["dropped"]
                else ""
            )
        )
        storage = clear_storage(removed["measurements"], removed["dropped"])
        print(
            f"removed {storage['files']} bucket files and "
            f"{storage['relationships']} permission records"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
