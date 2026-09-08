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
    Retrieve all reviewed areas
    ---
    paramaters:
      - in: query
            name: herd_unit_id
            type: number
      - in: query
            name: survey_id
            type: number
    responses:
            200:
                    description: List of reviewed areas.
            400:
                    description: Invalid UUID format.
            404:
                    description: No reviewed areas found.
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
    """ """
    return base.get(ReviewedArea, reviewed_area_id).serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@raBp.get("/<int:reviewed_area_id>/annotations")
@raBp.get("/<uuid:reviewed_area_id>/annotations")
@login_required
@permission_required("access")
def get_annotations(reviewed_area_id: int | UUID):
    """ """

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
    Generate a presigned GET URL for a reviewed area.
    ---
    responses:
            201:
                    description: Presigned URL generated.
            400:
                    description: Invalid ID format.
            404:
                    description: Image record not found.
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
    Update reviewed areas in the database.
    ---
    parameters:
            - name: reviewed_area_id
                    in: path
                    type: string
                    required: true
    responses:
        200:
                description: The reviewed area was updated successfully.
        400:
                description: Invalid UUID format or malformed request body.
        404:
                description: The reviewed area was  not found.
        401:
                description: The user is not authorized to modify the reviewed area.
        500:
                description: An unexpected error has occured.
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

    """
    req = UpdateReviewedAreaReq(reviewed_by_user_id=current_user.user_id)

    return base.update(ReviewedArea, reviewed_area_id, req).serialize(), 200
