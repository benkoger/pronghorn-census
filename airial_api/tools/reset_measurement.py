# Reset a survey's abundance estimation: its review, its measurement and what they left behind
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# Run INSIDE the API container, from /app:
#
#     .venv/bin/python -m tools.reset_measurement <survey name or uuid> --confirm <survey name>
#
# With --dry-run the database changes are rolled back and nothing outside it is touched; the
# output says what a real run would remove.
#
# In one transaction, it deletes the annotations of type 'active measurement' on the survey's
# tiles, deletes the survey's active measurement(s) (their units go with them), marks the
# survey's tiles unreviewed and sets the survey back to 'preparing'. Annotations and reviewed
# areas of every other type are counted before and after; a change rolls everything back.
#
# It then removes what is stored outside the database: the measurement's proposals, terms and
# placed boxes in the bucket, its serving state and terms in the cache, and its permission
# relationships and those of its units. Nothing else in the bucket is touched.
#
# It refuses to run unless --confirm repeats the survey's name, and warns when the bucket does
# not look like a test bucket.
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
from psycopg import Cursor
from psycopg.rows import dict_row, tuple_row

from app import create_app, proposal_store
from app.extensions import base, cache, s3
from database.database import Database
from database.object_models.core.activity import ActivityType
from flask import current_app

# ---------------------------------------------------------------------------------------------------------------------------

STORED = ("am_unit", "active_measurement")  # permission record types whose rows the reset removes
MAX_GENERATIONS = 1000


class Refused(Exception):
    pass


class DryRun(Exception):
    """Raised at the end of a dry run so that the transaction rolls back."""

    def __init__(self, removed: dict[str, Any]):
        self.removed = removed


def _counts(cursor: Cursor[Any]) -> tuple[int, int, int]:
    """Annotations of other types, reviewed areas of other types reviewed, and tiles in all."""
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
    cursor: Cursor[Any], db: Database, survey: str, confirm: str, dry_run: bool = False
) -> dict[str, Any]:
    """The database part, in the caller's transaction. Returns what was removed."""
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
        "SELECT uuid FROM projectmanagement.active_measurements WHERE survey_id = %(survey_id)s;",
        {"survey_id": row["survey_id"]},
    )
    measurements = [str(m[0]) for m in cursor.fetchall()]

    cursor.execute(
        """
        DELETE FROM core.annotations a
        USING core.annotations_reviewed_area x, core.reviewed_area t, core.images i
        WHERE x.annotation_id = a.annotation_id
          AND t.reviewed_area_id = x.reviewed_area_id
          AND i.image_id = t.image_id
          AND i.survey_id = %(survey_id)s
          AND a.type = %(type)s
          AND t.type = %(type)s;
        """,
        {"survey_id": row["survey_id"], "type": ActivityType.ACTIVE_MEASUREMENT},
    )
    annotations = cursor.rowcount

    cursor.execute(
        "DELETE FROM projectmanagement.active_measurements WHERE survey_id = %(survey_id)s;",
        {"survey_id": row["survey_id"]},
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
        {"survey_id": row["survey_id"], "type": ActivityType.ACTIVE_MEASUREMENT},
    )
    tiles = cursor.rowcount
    cursor.execute(
        "UPDATE projectmanagement.surveys SET status = 'preparing' "
        "WHERE survey_id = %(survey_id)s;",
        {"survey_id": row["survey_id"]},
    )

    if _counts(cursor) != before:
        raise Refused("annotations or reviewed areas of another type changed; rolled back")

    removed = {
        "survey": row["name"],
        "measurements": measurements,
        "annotations": annotations,
        "tiles": tiles,
    }
    if dry_run:
        raise DryRun(removed)
    return removed


def clear_storage(measurements: list[str]) -> dict[str, int]:
    """The bucket, the cache and the permission records of the removed measurements."""
    bucket = current_app.config["BUCKET_NAME"]
    files = 0
    for uuid in measurements:
        keys = [f"proposals/{g:04d}.npz" for g in range(MAX_GENERATIONS)]
        keys += ["terms.npz", "boxes.npz"]
        for key in keys:
            full = f"{proposal_store.S3_PREFIX}/{uuid}/{key}"
            try:
                s3.head_object(Bucket=bucket, Key=full)
            except ClientError:
                if key.startswith("proposals"):
                    break  # generations are numbered without gaps
                continue
            s3.delete_object(Bucket=bucket, Key=full)
            files += 1
        for version in range(1, proposal_store.STATE_VERSION + 1):
            cache.delete(f"am_state_{version}_{uuid}")
        for version in range(1, proposal_store.TERMS_VERSION + 1):
            cache.delete(f"am_terms_{version}_{uuid}")

    def stored(cursor: Cursor[Any], db: Database) -> dict[str, set[str]]:
        cursor.row_factory = tuple_row
        out = {}
        for kind, table in (("am_unit", "core.am_units"),
                            ("active_measurement", "projectmanagement.active_measurements")):
            cursor.execute(f"SELECT uuid FROM {table};")
            out[kind] = {str(r[0]) for r in cursor.fetchall()}
        return out

    client, full = base._spice_client, Consistency(fully_consistent=True)
    relationships = 0
    for kind, keep in base.execute(stored).items():
        ids = {
            r.relationship.resource.object_id
            for r in client.ReadRelationships(ReadRelationshipsRequest(
                consistency=full, relationship_filter=RelationshipFilter(resource_type=kind)))
        }
        for uid in ids - keep:
            client.DeleteRelationships(DeleteRelationshipsRequest(
                relationship_filter=RelationshipFilter(
                    resource_type=kind, optional_resource_id=uid
                )
            ))
            relationships += 1

    return {"files": files, "relationships": relationships}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("survey", help="the survey's name or uuid")
    parser.add_argument("--confirm", required=True, help="the survey's name, repeated")
    parser.add_argument("--dry-run", action="store_true", help="report only; change nothing")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        bucket = current_app.config["BUCKET_NAME"]
        print(f"database {os.environ.get('DB_NAME', '?')}, bucket {bucket}")
        if "test" not in bucket:
            print("WARNING: the bucket does not look like a test bucket", file=sys.stderr)
        try:
            removed = base.execute(clear_review, args.survey, args.confirm, args.dry_run)
        except Refused as error:
            print(f"refused: {error}", file=sys.stderr)
            return 1
        except DryRun as dry:
            removed = dry.removed
            print(f"dry run, {removed['survey']}: would remove {len(removed['measurements'])} "
                  f"measurement(s), {removed['annotations']} review annotations, "
                  f"{removed['tiles']} reviewed tiles, and their bucket files, cache entries "
                  f"and permission records")
            return 0
        print(f"{removed['survey']}: removed {len(removed['measurements'])} measurement(s), "
              f"{removed['annotations']} review annotations, {removed['tiles']} reviewed tiles")
        storage = clear_storage(removed["measurements"])
        print(f"removed {storage['files']} bucket files "
              f"and {storage['relationships']} permission records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
