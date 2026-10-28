# Endpoints for managing image metadata in the API
# Authors: Michael B. Lance, Antigravity
# ---------------------------------------------------------------------------------------------------------------------------

"""Endpoints for managing image metadata in the API."""

from uuid import UUID

from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.object_models.core.image_metadata import (
    CreateImageMetadataReq,
    ImageMetadata,
    UpdateImageMetadataReq,
)

imageMetadataBp = Blueprint("image_metadata", __name__, url_prefix="/api/v1/image-metadata")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@imageMetadataBp.get("/<int:metadata_id>")
@imageMetadataBp.get("/<uuid:metadata_id>")
@login_required
@permission_required("access")
def get_by_id(metadata_id: int | UUID):
    """Retrieve image metadata by its integer ID or UUID.

    ---
    parameters:
      - name: metadata_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the metadata record (integer ID or UUID).
    responses:
      200:
        description: The requested image metadata was found.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this metadata.
      404:
        description: Metadata record not found.
      500:
        description: Database error.
    """
    return base.get(ImageMetadata, metadata_id).serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@imageMetadataBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateImageMetadataReq):
    """Create a new image metadata record.

    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateImageMetadataReq
        description: Image metadata creation payload with camera/telemetry values.
    responses:
      201:
        description: Metadata record created successfully.
      400:
        description: Validation error.
      401:
        description: User not authorized.
      500:
        description: Database error.
    """
    return base.insert(ImageMetadata, body).serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@imageMetadataBp.patch("/<int:metadata_id>")
@imageMetadataBp.patch("/<uuid:metadata_id>")
@login_required
@permission_required("access")
@validate()
def update(body: UpdateImageMetadataReq, metadata_id: int | UUID):
    """Update image metadata by integer ID or UUID.

    ---
    parameters:
      - name: metadata_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the metadata record to update.
      - name: body
        in: body
        required: true
        type: UpdateImageMetadataReq
        description: Metadata update payload.
    responses:
      200:
        description: Metadata updated successfully.
      400:
        description: Validation error.
      401:
        description: User not authorized.
      404:
        description: Metadata not found.
      500:
        description: Database error.
    """
    return base.update(ImageMetadata, metadata_id, body).serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@imageMetadataBp.delete("/<int:metadata_id>")
@imageMetadataBp.delete("/<uuid:metadata_id>")
@login_required
@permission_required("access")
def delete(metadata_id: int | UUID):
    """Delete image metadata by integer ID or UUID.

    ---
    parameters:
      - name: metadata_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the metadata record to delete.
    responses:
      204:
        description: Metadata deleted successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized.
      404:
        description: Metadata not found.
      500:
        description: Database error.
    """
    base.delete(ImageMetadata, metadata_id)
    return "", 204
