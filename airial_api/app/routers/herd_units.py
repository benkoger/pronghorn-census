# Endpoints for managing herd units in the API
# Author: Michael B. Lance

"""Endpoints for managing herd units in the API."""

# ---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.object_models.project_management import CreateHerdUnitReq
from database.object_models.project_management.herd_units import HerdUnit
from database.object_models.project_management.projectmanagement_bindings import (
    SurveysHerdUnits,
)
from database.object_models.project_management.surveys import Survey

herdunitBp = Blueprint("herd_units", __name__, url_prefix="/api/v1/herd-units")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@herdunitBp.get("/<int:herd_unit_id>")
@herdunitBp.get("/<uuid:herd_unit_id>")
@login_required
@permission_required("access")
def get_by_id(herd_unit_id: int | UUID):
    """Request a herd unit object from the database using its integer PK or UUID.

    ---
    parameters:
      - name: herd_unit_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the herd unit (integer ID or UUID).
    responses:
      200:
        description: The requested herd unit was found.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this herd unit.
      404:
        description: No herd unit record found for the provided ID.
      500:
        description: Database error.
    """
    return base.get(HerdUnit, herd_unit_id).serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@herdunitBp.get("/<string:herd_unit_id>/surveys")
@herdunitBp.get("/<uuid:herd_unit_id>/surveys")
@login_required
@permission_required("access")
def get_surveys(herd_unit_id: int | UUID):
    """Retrieve all surveys associated with a herd unit.

    ---
    parameters:
      - name: herd_unit_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the herd unit (integer ID or UUID).
    responses:
      200:
        description: List of surveys (returns empty list if none exist).
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this herd unit.
      404:
        description: Herd unit not found.
      500:
        description: Database error.
    """
    if isinstance(herd_unit_id, UUID):
        herd_unit = base.get(HerdUnit, herd_unit_id)
        herd_unit_id = herd_unit.herd_unit_id

    surveys = base.get_related(
        SurveysHerdUnits,
        Survey,
        {"herd_unit_id": herd_unit_id},
    )

    return [survey.serialize() for survey in surveys], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@herdunitBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateHerdUnitReq):
    """Create a new herd unit object.

    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateHerdUnitReq
        description: Herd unit creation payload containing name and associated project IDs.
    responses:
      201:
        description: Herd unit created successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized to perform this action.
      409:
        description: Conflict or unique constraint violation.
      500:
        description: Database error.
    """
    return base.insert(HerdUnit, body).serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@herdunitBp.delete("/<int:herd_unit_id>")
@herdunitBp.delete("/<uuid:herd_unit_id>")
@login_required
@permission_required("access")
def delete(herd_unit_id: int | UUID):
    """Delete a herd unit by its integer ID or UUID.

    ---
    parameters:
      - name: herd_unit_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the herd unit to delete.
    responses:
      204:
        description: Herd unit deleted successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized to delete this herd unit.
      404:
        description: Herd unit not found.
      500:
        description: Database error.
    """
    base.delete(HerdUnit, herd_unit_id)

    return "", 204
