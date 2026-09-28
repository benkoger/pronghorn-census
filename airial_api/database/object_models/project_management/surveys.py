# Class definition for Survey objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------#

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Optional, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from psycopg.rows import class_row
import psycopg.sql as sql

from enum import StrEnum
from pydantic import BaseModel, ConfigDict

from ..base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class SurveyStatus(StrEnum):
    UPLOADED = "uploaded"
    PREPARING = "preparing"
    READY_FOR_MEASUREMENT = "ready for measurement"
    MEASURING = "measuring"
    FINISHED = "finished"


# ---------------------------------------------------------------------------------------------------------------------------


class CreateSurveyReq(BaseModel):
    project_ids: Keyring
    herd_unit_ids: Keyring
    survey_date: datetime
    name: str
    additional_info: Optional[str] = None
    status: Optional[SurveyStatus] = None
    survey_area: Optional[float] = None


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateSurveyReq(BaseModel):
    survey_date: Optional[datetime] = None
    name: Optional[str] = None
    additional_info: Optional[str] = None
    status: Optional[SurveyStatus] = None
    survey_area: Optional[float] = None


class SurveyImageQuery(BaseModel):
    page: Optional[int] = None
    per_page: Optional[int] = None


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Survey(DBbase):
    """Dataclass for representing Surveys from the database"""

    survey_id: int
    survey_date: datetime
    name: str
    additional_info: str | None
    created: datetime
    modified: datetime
    uuid: UUID
    status: Optional[SurveyStatus] = None
    survey_area: Optional[float] = None

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "surveys")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("survey_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        survey_id: int
        survey_date: datetime
        name: str
        status: Optional[SurveyStatus] = None
        survey_area: Optional[float] = None
        additional_info: str | None
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreateSurveyReq
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:
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
        return Survey.Response.model_validate(self).model_dump(mode="json")
