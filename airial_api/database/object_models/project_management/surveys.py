# Class definition for Survey objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
"""Survey database models and schemas."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Self
from uuid import UUID

import psycopg.sql as sql
from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict

from ..base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class SurveyStatus(StrEnum):
    """Enumeration of survey statuses."""

    UPLOADED = "uploaded"
    PREPARING = "preparing"
    READY_FOR_MEASUREMENT = "ready for measurement"
    MEASURING = "measuring"
    FINISHED = "finished"


# ---------------------------------------------------------------------------------------------------------------------------


class CreateSurveyReq(BaseModel):
    """Request schema for creating a survey."""

    project_ids: Keyring
    herd_unit_ids: Keyring
    survey_date: datetime
    name: str
    additional_info: str | None = None
    status: SurveyStatus | None = None
    survey_area: float | None = None


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateSurveyReq(BaseModel):
    """Request schema for updating a survey."""

    survey_date: datetime | None = None
    name: str | None = None
    additional_info: str | None = None
    status: SurveyStatus | None = None
    survey_area: float | None = None


class SurveyImageQuery(BaseModel):
    """Query parameters for survey images pagination."""

    page: int | None = None
    per_page: int | None = None


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Survey(DBbase):
    """Dataclass for representing surveys from the database."""

    survey_id: int
    survey_date: datetime
    name: str
    additional_info: str | None
    created: datetime
    modified: datetime
    uuid: UUID
    status: SurveyStatus | None = None
    survey_area: float | None = None

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "surveys")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("survey_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for a survey."""

        model_config = ConfigDict(from_attributes=True)

        survey_id: int
        survey_date: datetime
        name: str
        status: SurveyStatus | None = None
        survey_area: float | None = None
        additional_info: str | None
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, cursor: Cursor[Self], req: CreateSurveyReq) -> tuple[Self, list[RelationshipUpdate]] | None:
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            WITH new_survey AS (
                INSERT INTO projectmanagement.surveys (
                    survey_date, name, additional_info, status, survey_area
                )
                VALUES (
                    %(survey_date)s, %(name)s, %(additional_info)s, %(status)s, %(survey_area)s
                )
                RETURNING *
            ),
            inserted_project AS (
                INSERT INTO projectmanagement.projects_surveys (
                    project_id, survey_id
                )
                SELECT %(project_id)s, survey_id FROM new_survey
            ),
            inserted_herd_unit AS (
                INSERT INTO projectmanagement.surveys_herd_units (
                    herd_unit_id, survey_id
                )
                SELECT %(herd_unit_id)s, survey_id FROM new_survey
            )
            SELECT * FROM new_survey;
        """)

        cursor.execute(
            query,
            {
                **req.model_dump(),
                "project_id": req.project_ids.pkey,
                "herd_unit_id": req.herd_unit_ids.pkey,
            },
        )

        if not (survey := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "survey",
                survey.uuid,
                "herd_unit",
                req.herd_unit_ids.uuid,
                "parent",
            )
        ]

        return survey, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict:
        """Serialize survey model to a dictionary."""
        return Survey.Response.model_validate(self).model_dump(mode="json")
