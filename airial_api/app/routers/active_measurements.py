# Endpoints for managing active measurements in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.object_models.core.am_units import AmUnit
from database.object_models.project_management.active_measurements import (
    ActiveMeasurement,
    CreateActiveMeasurment,
    UpdateActiveMeasurement,
)

activeMeasBp = Blueprint("active_measurements", __name__, url_prefix="/api/v1/active-measurements")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@activeMeasBp.get("/<int:active_measurement_id>")
@activeMeasBp.get("/<uuid:active_measurement_id>")
@login_required
@permission_required("access")
def get_by_id(active_measurement_id: int | UUID):
    """
    Retrieve an active measurement by its integer ID or UUID.
    ---
    parameters:
      - name: active_measurement_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the active measurement (integer ID or UUID).
    responses:
      200:
        description: Active measurement found and returned.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this active measurement.
      404:
        description: No active measurement found for the provided ID.
      500:
        description: Database error.
    """
    return base.get(ActiveMeasurement, active_measurement_id).serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@activeMeasBp.get("/<int:active_measurement_id>/am-units")
@activeMeasBp.get("/<uuid:active_measurement_id>/am-units")
@login_required
@permission_required("access")
def get_am_units(active_measurement_id: int | UUID):
    """
    Retrieve all AM units associated with an active measurement.
    ---
    parameters:
      - name: active_measurement_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the parent active measurement (integer ID or UUID).
    responses:
      200:
        description: List of AM units (returns empty list if none exist).
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this active measurement.
      404:
        description: Parent active measurement not found.
      500:
        description: Database error.
    """
    am_units = base.get_children(AmUnit, ActiveMeasurement, active_measurement_id)
    return [unit.serialize() for unit in am_units], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@activeMeasBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateActiveMeasurment):
    """
    Create a new active measurement.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateActiveMeasurment
        description: Active measurement creation payload including survey_ids, label_ids, random_seed, and frozen flag.
    responses:
      201:
        description: Active measurement created successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized to perform this action.
      409:
        description: Conflict or constraint violation.
      500:
        description: Database error.
    """
    return base.insert(ActiveMeasurement, body).serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@activeMeasBp.patch("/<int:active_measurement_id>")
@activeMeasBp.patch("/<uuid:active_measurement_id>")
@login_required
@permission_required("access")
@validate()
def update(body: UpdateActiveMeasurement, active_measurement_id: int | UUID):
    """
    Update an active measurement by integer ID or UUID (e.g., freezing or unfreezing).
    ---
    parameters:
      - name: active_measurement_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the active measurement to update.
      - name: body
        in: body
        required: true
        type: UpdateActiveMeasurement
        description: Active measurement update payload.
    responses:
      200:
        description: Active measurement updated successfully.
      400:
        description: Validation error or invalid ID format.
      401:
        description: User not authorized to modify this active measurement.
      404:
        description: Active measurement record not found.
      500:
        description: Database error.
    """
    return base.update(ActiveMeasurement, active_measurement_id, body).serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@activeMeasBp.delete("/<int:active_measurement_id>")
@activeMeasBp.delete("/<uuid:active_measurement_id>")
@login_required
@permission_required("access")
def delete(active_measurement_id: int | UUID):
    """
    Delete an active measurement by integer ID or UUID.
    ---
    parameters:
      - name: active_measurement_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the active measurement to delete.
    responses:
      204:
        description: Active measurement deleted successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized to delete this active measurement.
      404:
        description: Active measurement not found.
      500:
        description: Database error.
    """
    base.delete(ActiveMeasurement, active_measurement_id)
    return "", 204
