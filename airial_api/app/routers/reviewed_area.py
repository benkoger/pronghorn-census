# Endpoints for managing reviewed areas in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

from flask import Blueprint, current_app
from flask_login import current_user, login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base, s3
from database.object_models.base import PrimaryKey
from database.object_models.core import UpdateReviewedAreaReq
from database.object_models.core.annotations import Annotation
from database.object_models.core.core_bindings import AnnotationsReviewedArea
from database.object_models.core.images import (
    CrateReviewedAreaPresignedGetReq,
    RAQuery,
    ReviewedArea,
)

raBp = Blueprint("reviewed-area", __name__, url_prefix="/api/v1/reviewed-area")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


# TODO: Replace with composable generics
@raBp.get("")
@login_required
@permission_required("access")
@validate()
def get(query: RAQuery):
    """
    Retrieve all reviewed areas filtered by query criteria.
    ---
    parameters:
      - name: herd_unit_id
        in: query
        required: false
        type: integer
        description: Herd unit ID filter.
      - name: survey_id
        in: query
        required: false
        type: integer
        description: Survey ID filter.
      - name: image_id
        in: query
        required: false
        type: integer
        description: Image ID filter.
    responses:
      200:
        description: List of reviewed areas.
      400:
        description: Invalid query parameters.
      401:
        description: User not authorized.
      500:
        description: Database error.
    """

    reviewed_areas = base.get_reviewed_areas(query)

    return [ra.serialize() for ra in reviewed_areas]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@raBp.get("/<int:reviewed_area_id>")
@raBp.get("/<uuid:reviewed_area_id>")
@login_required
@permission_required("access")
def get_by_id(reviewed_area_id: int | UUID):
    """
    Request a reviewed area object from the database using its integer PK or UUID.
    ---
    parameters:
      - name: reviewed_area_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the reviewed area (integer ID or UUID).
    responses:
      200:
        description: The requested reviewed area was found.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this reviewed area.
      404:
        description: No reviewed area record found for the provided ID.
      500:
        description: Database error.
    """
    return base.get(ReviewedArea, reviewed_area_id).serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@raBp.get("/<int:reviewed_area_id>/annotations")
@raBp.get("/<uuid:reviewed_area_id>/annotations")
@login_required
@permission_required("access")
def get_annotations(reviewed_area_id: int | UUID):
    """
    Retrieve all annotations associated with a specific reviewed area.
    ---
    parameters:
      - name: reviewed_area_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the reviewed area (integer ID or UUID).
    responses:
      200:
        description: List of annotations (returns empty list if none exist).
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this reviewed area.
      404:
        description: Reviewed area not found.
      500:
        description: Database error.
    """

    if isinstance(reviewed_area_id, UUID):
        reviewed_area = base.get(ReviewedArea, reviewed_area_id)
        reviewed_area_id = reviewed_area.reviewed_area_id

    annotations = base.get_related(
        AnnotationsReviewedArea, Annotation, {"reviewed_area_id": reviewed_area_id}
    )

    return [annot.serialize() for annot in annotations], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@raBp.post("/presigned-get-url")
@login_required
@permission_required("access")
@validate()
def create_ra_presigned_get(body: CrateReviewedAreaPresignedGetReq):
    """
    Generate a presigned GET URL for downloading a reviewed area crop.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CrateReviewedAreaPresignedGetReq
        description: Payload containing the reviewed_area_id.
    responses:
      201:
        description: Presigned URL generated successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized.
      404:
        description: Reviewed area record not found.
      500:
        description: Storage or database error.
    """
    ra = base.get(ReviewedArea, body.reviewed_area_id)

    response = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": current_app.config["BUCKET_NAME"], "Key": ra.ra_key},
        ExpiresIn=3600,
    )

    return response, 201


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@raBp.patch("/<int:reviewed_area_id>")
@raBp.patch("/<uuid:reviewed_area_id>")
@login_required
@permission_required("access")
@validate()
def update_reviewed_area(body: UpdateReviewedAreaReq, reviewed_area_id: int | UUID):
    """
    Update a reviewed area in the database.
    ---
    parameters:
      - name: reviewed_area_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the reviewed area to update.
      - name: body
        in: body
        required: true
        type: UpdateReviewedAreaReq
        description: Reviewed area update payload.
    responses:
      200:
        description: The reviewed area was updated successfully.
      400:
        description: Invalid ID format or malformed request body.
      401:
        description: User not authorized to modify the reviewed area.
      404:
        description: Reviewed area not found.
      500:
        description: Unexpected error.
    """

    return base.update(ReviewedArea, reviewed_area_id, body).serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@raBp.patch("/<int:reviewed_area_id>/set-reviewed")
@raBp.patch("/<uuid:reviewed_area_id>/set-reviewed")
@login_required
@permission_required("access")
@validate()
def set_reviewed(reviewed_area_id: PrimaryKey):
    """
    Mark a reviewed area as reviewed by the currently authenticated user.
    ---
    parameters:
      - name: reviewed_area_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the reviewed area.
    responses:
      200:
        description: Reviewed area successfully marked as reviewed.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized.
      404:
        description: Reviewed area not found.
      500:
        description: Database error.
    """
    req = UpdateReviewedAreaReq(reviewed_by_user_id=current_user.user_id)

    return base.update(ReviewedArea, reviewed_area_id, req).serialize(), 200
