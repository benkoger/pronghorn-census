# Class definition for ProposalGeneration objects in the database
# Author: Owen Martin
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Self
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict, model_validator
import psycopg.sql as sql

from database.object_models.base import DBbase, Keyring

# ---------------------------------------------------------------------------------------------------------------------------


class CreateProposalGenerationReq(BaseModel):
    """One generation of a measurement's sampling proposal, ready to store.

    Attributes:
        active_measurement_ids: Keys of the measurement the generation belongs
            to.
        generation: Index of the generation within the measurement, from 0.
        n_labels: Number of reviewed units the generation was fitted on; 0 for
            the initial generation.
        reviewed_area_ids: Unit order the sampler indexes. Identical in every
            generation of a measurement.
        raw: Expected count per unit, in reviewed_area_ids order.
        proposal: Shaped vector the sampler draws from, in the same order.
        model_id: Regression model that produced the generation, when one is
            registered.
        alpha: Exponent that shaped the proposal from the expected counts.
    """

    active_measurement_ids: Keyring
    generation: int
    reviewed_area_ids: list[int]
    raw: list[float]
    proposal: list[float]
    n_labels: int = 0
    model_id: int | None = None
    alpha: float | None = None

    @model_validator(mode="after")
    def _check_vector_lengths(self) -> Self:
        """Rejects empty vectors and vectors of differing lengths."""
        n = len(self.reviewed_area_ids)
        if n == 0 or len(self.raw) != n or len(self.proposal) != n:
            raise ValueError(
                "reviewed_area_ids, raw and proposal must be non-empty and"
                " the same length"
            )
        return self


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class ProposalGeneration(DBbase):
    """A stored generation of a measurement's sampling proposal."""

    proposal_generation_id: int
    active_measurement_id: int
    generation: int
    n_labels: int
    reviewed_area_ids: list[int]
    raw: list[float]
    proposal: list[float]
    created: datetime
    modified: datetime
    uuid: UUID
    model_id: int | None = None
    alpha: float | None = None

    __table__: ClassVar[sql.Identifier] = sql.Identifier(
        "core", "proposal_generations"
    )
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("proposal_generation_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        proposal_generation_id: int
        active_measurement_id: int
        generation: int
        n_labels: int
        model_id: int | None = None
        alpha: float | None = None
        reviewed_area_ids: list[int]
        raw: list[float]
        proposal: list[float]
        created: datetime
        modified: datetime
        uuid: UUID

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: CreateProposalGenerationReq
    ) -> tuple[Self, list[RelationshipUpdate]] | None:
        """Inserts the generation and returns the stored row.

        Generations are not SpiceDB objects: access to them is checked through
        their measurement, so no relationship update is returned.

        Args:
            cursor: Cursor to run the insert on.
            req: The generation to store.

        Returns:
            The stored row and an empty list of relationship updates, or None
            if nothing was returned by the insert.
        """
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            INSERT INTO core.proposal_generations (
                active_measurement_id, generation, n_labels, model_id, alpha,
                reviewed_area_ids, raw, proposal
            )
            VALUES (
                %(active_measurement_id)s, %(generation)s, %(n_labels)s,
                %(model_id)s, %(alpha)s,
                %(reviewed_area_ids)s::integer[],
                %(raw)s::double precision[],
                %(proposal)s::double precision[]
            )
            RETURNING *;
        """)

        cursor.execute(
            query,
            {
                **req.model_dump(exclude={"active_measurement_ids"}),
                "active_measurement_id": req.active_measurement_ids.pkey,
            },
        )

        if not (generation := cursor.fetchone()):
            return None

        return generation, []

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict[str, Any]:
        return ProposalGeneration.Response.model_validate(self).model_dump(
            mode="json"
        )
