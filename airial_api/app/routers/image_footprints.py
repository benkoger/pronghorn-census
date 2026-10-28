# Endpoints for managing image footprints in the API
# Authors: Michael B. Lance, Antigravity
# ---------------------------------------------------------------------------------------------------------------------------

"""Endpoints for managing image footprints in the API."""

from uuid import UUID

from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.object_models.core.image_footprints import (
    CreateImageFootprintReq,
    ImageFootprint,
    UpdateImageFootprintReq,
)

imageFootprintBp = Blueprint("image_footprints", __name__, url_prefix="/api/v1/image-footprints")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@imageFootprintBp.get("/<int:footprint_id>")
@imageFootprintBp.get("/<uuid:footprint_id>")
@login_required
@permission_required("access")
def get_by_id(footprint_id: int | UUID):
    """Retrieve an image footprint by its integer ID or UUID.

    ---
    parameters:
      - name: footprint_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the footprint record (integer ID or UUID).
    responses:
      200:
        description: The requested image footprint was found.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this footprint.
      404:
        description: Footprint record not found.
      500:
        description: Database error.
    """
    return base.get(ImageFootprint, footprint_id).serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@imageFootprintBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateImageFootprintReq):
    """Create a new image footprint record.

    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateImageFootprintReq
        description: Image footprint creation payload with spatial geometry and georeferencing metadata.
    responses:
      201:
        description: Footprint record created successfully.
      400:
        description: Validation error.
      401:
        description: User not authorized.
      500:
        description: Database error.
    """
    return base.insert(ImageFootprint, body).serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@imageFootprintBp.patch("/<int:footprint_id>")
@imageFootprintBp.patch("/<uuid:footprint_id>")
@login_required
@permission_required("access")
@validate()
def update(body: UpdateImageFootprintReq, footprint_id: int | UUID):
    """Update an image footprint by integer ID or UUID.

    ---
    parameters:
      - name: footprint_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the footprint record to update.
      - name: body
        in: body
        required: true
        type: UpdateImageFootprintReq
        description: Footprint update payload.
    responses:
      200:
        description: Footprint updated successfully.
      400:
        description: Validation error.
      401:
        description: User not authorized.
      404:
        description: Footprint not found.
      500:
        description: Database error.
    """
    return base.update(ImageFootprint, footprint_id, body).serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@imageFootprintBp.delete("/<int:footprint_id>")
@imageFootprintBp.delete("/<uuid:footprint_id>")
@login_required
@permission_required("access")
def delete(footprint_id: int | UUID):
    """Delete an image footprint by integer ID or UUID.

    ---
    parameters:
      - name: footprint_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the footprint record to delete.
    responses:
      204:
        description: Footprint deleted successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized.
      404:
        description: Footprint not found.
      500:
        description: Database error.
    """
    base.delete(ImageFootprint, footprint_id)
    return "", 204
