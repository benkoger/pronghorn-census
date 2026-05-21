# Endpoints for managing reviewed areas in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from typing import cast
from uuid import UUID

from flask import Blueprint, current_app
from flask_login import current_user, login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base, s3
from database.object_models.core import RAQuery, UpdateReviewedAreaReq
from database.object_models.core.images import CrateReviewedAreaPresignedGetReq
from database.object_models.user_management import User

raBp = Blueprint("reviewed-area", __name__, url_prefix="/api/v1/reviewed-area")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


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

    return [ra.to_dict() for ra in reviewed_areas]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@raBp.get("/<string:reviewed_area_id>/annotations")
@login_required
@permission_required("access")
def get_annotations(reviewed_area_id: str):
    """ """

    annotations = base.get_reviewed_area_annotations(UUID(reviewed_area_id))

    return [annot.to_dict() for annot in annotations], 200


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
    ra = base.get_reviewed_area(body.reviewed_area_id)

    response = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": current_app.config["BUCKET_NAME"], "Key": ra.ra_key},
        ExpiresIn=3600,
    )

    return response, 201


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@raBp.patch("/<string:reviewed_area_id>")
@login_required
@permission_required("access")
@validate()
def update_reviewed_area(body: UpdateReviewedAreaReq, reviewed_area_id: str):
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

    return (
        base.update_reviewed_area(
            UUID(reviewed_area_id), body, cast(User, current_user)
        ).to_dict(),
        200,
    )
