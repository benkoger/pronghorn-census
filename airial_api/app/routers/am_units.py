# Endpoints for managing AM units in the API
# Author: Michael B. Lance

"""Endpoints for managing AM units in the API."""

# ---------------------------------------------------------------------------------------------------------------------------

from typing import cast
from uuid import UUID

from flask import Blueprint
from flask_login import current_user, login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.object_models.base import Keyring
from database.object_models.core.am_units import (
    AmUnit,
    CreateAmUnitReq,
    UpdateAmUnitReq,
)
from database.object_models.user_management.users import User

amUnitBp = Blueprint("am_units", __name__, url_prefix="/api/v1/am-units")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@amUnitBp.get("/<int:am_unit_id>")
@amUnitBp.get("/<uuid:am_unit_id>")
@login_required
@permission_required("access")
def get_by_id(am_unit_id: int | UUID):
    """Retrieve an AM unit by its integer ID or UUID.

    ---
    parameters:
      - name: am_unit_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the AM unit (integer ID or UUID).
    responses:
      200:
        description: The requested AM unit was found.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this AM unit.
      404:
        description: No AM unit found for the provided ID.
      500:
        description: Database error.
    """
    return base.get(AmUnit, am_unit_id).serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@amUnitBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateAmUnitReq):
    """Create a new AM unit record.

    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateAmUnitReq
        description: AM unit creation payload with linked active measurement, reviewed area, model IDs, and metrics.
    responses:
      201:
        description: AM unit created successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized to perform this action.
      409:
        description: Conflict or constraint violation.
      500:
        description: Database error.
    """
    user = cast(User, current_user)
    user_key = Keyring(user.user_id, user.uuid)
    return base.insert(AmUnit, body, user_key).serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@amUnitBp.patch("/<int:am_unit_id>")
@amUnitBp.patch("/<uuid:am_unit_id>")
@login_required
@permission_required("access")
@validate()
def update(body: UpdateAmUnitReq, am_unit_id: int | UUID):
    """Update an AM unit by integer ID or UUID.

    ---
    parameters:
      - name: am_unit_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the AM unit to update.
      - name: body
        in: body
        required: true
        type: UpdateAmUnitReq
        description: AM unit update payload with revised counts, bounds, or sequence links.
    responses:
      200:
        description: AM unit updated successfully.
      400:
        description: Validation error or invalid ID format.
      401:
        description: User not authorized to modify this AM unit.
      404:
        description: AM unit record not found.
      500:
        description: Database error.
    """
    return base.update(AmUnit, am_unit_id, body).serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@amUnitBp.delete("/<int:am_unit_id>")
@amUnitBp.delete("/<uuid:am_unit_id>")
@login_required
@permission_required("access")
def delete(am_unit_id: int | UUID):
    """Delete an AM unit by integer ID or UUID.

    ---
    parameters:
      - name: am_unit_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the AM unit to delete.
    responses:
      204:
        description: AM unit deleted successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized to delete this AM unit.
      404:
        description: AM unit not found.
      500:
        description: Database error.
    """
    base.delete(AmUnit, am_unit_id)
    return "", 204
