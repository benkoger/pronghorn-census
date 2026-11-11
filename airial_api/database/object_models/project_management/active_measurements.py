"""Active measurement database models and schemas."""

# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor, sql
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict

from database.object_models.base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class CreateActiveMeasurement(BaseModel):
    """Request schema for creating an active measurement."""

    survey_ids: Keyring
    label_ids: Keyring
    random_seed: int
    # Reviewed units between refits of the proposal; 0 freezes the proposal
    # posted at preparation, so serving never waits on a refit.
    retraining_cadence: int = 0
    target_percentage: float | None = None
    final_count: float | None = None
    final_ci_upper: float | None = None
    final_ci_lower: float | None = None


# ---------------------------------------------------------------------------------------------------------------------------


class ActiveMeasurementQuery(BaseModel):
    """The survey whose current measurement a request is about."""

    survey_id: UUID


# ---------------------------------------------------------------------------------------------------------------------------


class CreateTilesReq(BaseModel):
    """The survey to cut into tiles and, optionally, which of its images.

    Attributes:
        survey_id: The survey.
        image_ids: Images to cut; every image of the survey when None.
    """

    survey_id: UUID
    image_ids: list[int] | None = None


# ---------------------------------------------------------------------------------------------------------------------------


class CreateProposalReq(BaseModel):
    """A proposal generation as the fitting service posts it.

    The generation number is assigned by the server: the next one after
    those stored.

    Attributes:
        reviewed_area_ids: Unit order the sampler indexes.
        raw: Expected count per unit, in reviewed_area_ids order.
        proposal: Shaped vector the sampler draws from, in the same order.
        n_labels: Reviewed units the generation was fitted on; 0 at first.
        model_id: Regression model that produced it, when registered.
        alpha: Exponent that shaped the proposal from the expected counts.
    """

    reviewed_area_ids: list[int]
    raw: list[float]
    proposal: list[float]
    n_labels: int = 0
    model_id: int | None = None
    alpha: float | None = None


# ---------------------------------------------------------------------------------------------------------------------------


class UpdateActiveMeasurement(BaseModel):
    """Request schema for updating an active measurement."""

    retraining_cadence: int | None = None
    target_percentage: float | None = None
    final_count: float | None = None
    final_ci_upper: float | None = None
    final_ci_lower: float | None = None


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class ActiveMeasurement(DBbase):
    """Database representation of an active measurement."""

    active_measurement_id: int
    survey_id: int
    label_id: int
    random_seed: int
    retraining_cadence: int
    created: datetime
    modified: datetime
    uuid: UUID
    target_percentage: float | None = None
    final_count: float | None = None
    final_ci_upper: float | None = None
    final_ci_lower: float | None = None

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "active_measurements")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("active_measurement_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for an active measurement."""

        model_config = ConfigDict(from_attributes=True)
        active_measurement_id: int
        survey_id: int
        label_id: int
        random_seed: int
        retraining_cadence: int
        target_percentage: float | None = None
        final_count: float | None = None
        final_ci_upper: float | None = None
        final_ci_lower: float | None = None
        created: datetime
        modified: datetime
        uuid: UUID

    Response: ClassVar[type[BaseModel]] = Response

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(cls, cursor: Cursor[Self], req: CreateActiveMeasurement) -> tuple[Self, list[RelationshipUpdate]] | None:

        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            INSERT INTO projectmanagement.active_measurements (
                survey_id, label_id, random_seed, retraining_cadence,
                target_percentage, final_count, final_ci_upper, final_ci_lower
            )
            VALUES (
                %(survey_id)s, %(label_id)s, %(random_seed)s,
                %(retraining_cadence)s, %(target_percentage)s, %(final_count)s,
                %(final_ci_upper)s, %(final_ci_lower)s
            )
            RETURNING *;
        """)

        cursor.execute(
            query,
            {
                **req.model_dump(),
                "survey_id": req.survey_ids.pkey,
                "label_id": req.label_ids.pkey,
            },
        )

        if not (active_measurement := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "active_measurement",
                active_measurement.uuid,
                "survey",
                req.survey_ids.uuid,
                "parent",
            )
        ]

        return active_measurement, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict[str, Any]:
        """Serialize active measurement model to a dictionary.

        Returns:
            Dictionary representation conforming to ActiveMeasurement.Response schema.
        """
        return ActiveMeasurement.Response.model_validate(self).model_dump(mode="json")
