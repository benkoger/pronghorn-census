# Crop Verifier Specialized Database Operations
# Author: Michael B. Lance / Antigravity
# ---------------------------------------------------------------------------------------------------------------------------

from typing import TYPE_CHECKING, Any
import psycopg.sql as sql
from psycopg import Cursor
from psycopg.rows import class_row, tuple_row

from database.object_models.base import Keyring
from database.object_models.core.images import RAQuery, ReviewedArea
from database.object_models.user_management.users import User

if TYPE_CHECKING:
    from database.database import Database


def get_available_crops(
    cursor: Cursor[Any],
    db: "Database",
    survey_ids: Keyring,
    query: RAQuery,
    user: User,
) -> list[ReviewedArea]:
    """
    Finds an available image with eligible crops in the survey, atomically locks it
    for the current user, and returns all candidate crops on that image in a single query.
    """
    stmt = sql.SQL("""
        WITH available_image AS (
            SELECT i.image_id
            FROM core.images i
            WHERE i.survey_id = %(survey_id)s
              AND i.opened_by_user_id = 0
              AND EXISTS (
                  SELECT 1 FROM core.reviewed_area ra
                  WHERE ra.image_id = i.image_id
                    AND (%(include_reviewed)s OR ra.reviewed_by_user_id = 0)
              )
            ORDER BY i.image_id ASC
            LIMIT 1
        ),
        locked_image AS (
            UPDATE core.images i
            SET opened_by_user_id = %(user_id)s
            FROM available_image
            WHERE i.image_id = available_image.image_id
            RETURNING i.image_id
        )
        SELECT ra.*
        FROM core.reviewed_area ra
        JOIN locked_image ON locked_image.image_id = ra.image_id
        WHERE (%(include_reviewed)s OR ra.reviewed_by_user_id = 0)
        ORDER BY ra.reviewed_area_id ASC;
    """)

    params: dict[str, Any] = {
        "survey_id": survey_ids.pkey,
        "user_id": user.user_id,
        "include_reviewed": bool(query.include_reviewed),
    }

    cursor.row_factory = class_row(ReviewedArea)
    cursor.execute(stmt, params)
    return cursor.fetchall()


def get_selection_count(
    cursor: Cursor[Any],
    db: "Database",
    survey_ids: Keyring,
    query: RAQuery,
) -> int:
    """Counts crops in the survey matching review and opened criteria."""
    stmt = sql.SQL("""
        SELECT COUNT(ra.reviewed_area_id)
        FROM core.reviewed_area ra
        JOIN core.images i ON i.image_id = ra.image_id
        WHERE i.survey_id = %(survey_id)s
          AND (%(include_reviewed)s OR ra.reviewed_by_user_id = 0)
          AND (%(include_opened)s OR i.opened_by_user_id = 0);
    """)

    params: dict[str, Any] = {
        "survey_id": survey_ids.pkey,
        "include_reviewed": bool(query.include_reviewed),
        "include_opened": bool(query.include_opened),
    }

    cursor.row_factory = tuple_row
    cursor.execute(stmt, params)
    res = cursor.fetchone()
    return int(res[0]) if res else 0
