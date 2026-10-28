# Endpoints for managing reviewed areas in the API
# Author: Michael B. Lance

"""Endpoints for managing reviewed areas in the API."""

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

import psycopg.sql as sql
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
from database.object_models.project_management.herd_units import HerdUnit
from database.object_models.project_management.surveys import Survey

raBp = Blueprint("reviewed-area", __name__, url_prefix="/api/v1/reviewed-area")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@raBp.get("")
@login_required
@permission_required("access")
@validate()
def get(query: RAQuery):
    """Retrieve reviewed areas filtered by query criteria with optional pagination.

    ---
    parameters:
      - name: herd_unit_id
        in: query
        required: false
        type: array
        items:
          type: string
          format: uuid
        description: Herd unit ID filter.
      - name: survey_id
        in: query
        required: false
        type: array
        items:
          type: string
          format: uuid
        description: Survey ID filter.
      - name: page
        in: query
        required: false
        type: integer
        description: Page number for pagination.
      - name: per_page
        in: query
        required: false
        type: integer
        description: Number of items per page.
      - name: search
        in: query
        required: false
        type: string
        description: Search term for reviewed area name.
    responses:
      200:
        description: List of reviewed areas or paginated reviewed areas object.
      400:
        description: Invalid query parameters.
      401:
        description: User not authorized.
      500:
        description: Database error.
    """
    parent_cls = None
    parent_pk = None
    if query.survey_id:
        parent_cls = Survey
        parent_pk = query.survey_id[0]
    elif query.herd_unit_id:
        parent_cls = HerdUnit
        parent_pk = query.herd_unit_id[0]

    scope = None if query.include_reviewed else {"reviewed_by_user_id": 0}

    where_clauses = []
    placeholders = {}
    if query.search:
        where_clauses.append(
            sql.SQL("{table}.name ILIKE {ph}").format(
                table=ReviewedArea.__table__,
                ph=sql.Placeholder("search_term"),
            )
        )
        placeholders["search_term"] = f"%{query.search}%"

    crops, total = base.get_paginated(
        ReviewedArea,
        page=query.page,
        per_page=query.per_page or 20,
        limit=query.num,
        parent_cls=parent_cls,
        parent_pk=parent_pk,
        scope=scope,
        where_clauses=where_clauses if where_clauses else None,
        placeholders=placeholders if placeholders else None,
    )

    if query.page is not None:
        page = max(1, query.page)
        per_page = max(1, query.per_page or 20)
        return {
            "crops": [c.serialize() for c in crops],
            "total": total,
            "page": page,
            "per_page": per_page,
        }, 200

    return [c.serialize() for c in crops], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@raBp.get("/<int:reviewed_area_id>")
@raBp.get("/<uuid:reviewed_area_id>")
@login_required
@permission_required("access")
def get_by_id(reviewed_area_id: int | UUID):
    """Request a reviewed area object from the database using its integer PK or UUID.

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
    """Retrieve all annotations associated with a specific reviewed area.

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

    annotations = base.get_related(AnnotationsReviewedArea, Annotation, {"reviewed_area_id": reviewed_area_id})

    return [annot.serialize() for annot in annotations], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@raBp.post("/presigned-get-url")
@login_required
@permission_required("access")
@validate()
def create_ra_presigned_get(body: CrateReviewedAreaPresignedGetReq):
    """Generate a presigned GET URL for downloading a reviewed area crop.

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
    """Update a reviewed area in the database.

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
    """Mark a reviewed area as reviewed by the currently authenticated user.

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
