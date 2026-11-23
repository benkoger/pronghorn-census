"""Abundance specialized database operations."""

# Abundance Specialized Database Operations
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------
# The terms a survey's abundance needs, stored on its measurement:
#
#   set_terms(measurement, terms)          -> store them on the measurement
#
# abundance = overlap factor x estimated count / surveyed area x habitable area
#
# The row holds the terms as a plain object (ais.SurveyTerms.as_dict);
# app.proposal_store keeps them in Valkey in front of it.
# ---------------------------------------------------------------------------------------------------------------------------

from typing import TYPE_CHECKING, Any

from psycopg import Cursor, sql
from psycopg.types.json import Jsonb

from ais import SurveyTerms
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
)

if TYPE_CHECKING:
    from database.database import Database

# ---------------------------------------------------------------------------------------------------------------------------
# Terms


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
