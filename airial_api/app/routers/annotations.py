# Endpoints for managing annotations in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from typing import cast

from flask import Blueprint
from flask_login import current_user, login_required
from flask_pydantic import validate
from app.decorators import permission_required
from app.extensions import base
from database.object_models.base import Keyring
from database.object_models.core import CreateAnnotationReq, UpdateAnnotationReq
from database.object_models.core.annotations import (
    Annotation,
    BulkCreateAnnotationReq,
    BulkUpdateAnnotationsReq,
    BulkDeleteAnnotationsReq,
)
from database.object_models.project_management import HerdUnit
from database.object_models.user_management import User
from uuid import UUID

annotBp = Blueprint("annotations", __name__, url_prefix="/api/v1/annotations")

# ---------------------------------------------------------------------------------------------------------------------------
# POST


@annotBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateAnnotationReq):
    """
    Create a new annotation object.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateAnnotationReq
        description: Annotation creation payload with box coordinates, label_id, image_id, and optional prediction_ids/reviewed_area_ids.
    responses:
      201:
        description: Annotation created successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized to perform this action.
      500:
        description: Database error.
    """
    herd_unit = base.get(HerdUnit, body.herd_unit_id)
    h_key = Keyring(herd_unit.herd_unit_id, herd_unit.uuid)
    u_key = Keyring(current_user.user_id, current_user.uuid)

    annotation = base.insert(Annotation, body, u_key, h_key)

    return annotation.serialize(), 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# This could be optimized pretty heavily
@annotBp.post("/bulk-import")
@validate()
@login_required
@permission_required("access")
def import_annotation(body: BulkCreateAnnotationReq):
    """
    Bulk import multiple annotation records.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: BulkCreateAnnotationReq
        description: Array of annotation creation requests.
    responses:
      201:
        description: List of created annotations.
      400:
        description: Validation error or invalid payload format.
      401:
        description: User not authorized.
      500:
        description: Database error.
    """

    if not body.requests:
        return [], 201

    u_key = Keyring(current_user.user_id, current_user.uuid)
    herd_unit = base.get(HerdUnit, body.requests[0].herd_unit_id)
    h_key = Keyring(herd_unit.herd_unit_id, herd_unit.uuid)

    annotations = []

    for req in body.requests:
        annotations.append(base.insert(Annotation, req, u_key, h_key))

    return [annot.serialize() for annot in annotations], 201


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@annotBp.patch("/<int:annotation_id>")
@annotBp.patch("/<uuid:annotation_id>")
@login_required
@permission_required("access")
@validate()
def update(body: UpdateAnnotationReq, annotation_id: int | UUID):
    """
    Update an annotation object in the database by its integer ID or UUID.
    ---
    parameters:
      - name: annotation_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the annotation to update.
      - name: body
        in: body
        required: true
        type: UpdateAnnotationReq
        description: Annotation update payload with modified coordinates or label.
    responses:
      200:
        description: Annotation updated successfully.
      400:
        description: Validation error or invalid ID format.
      401:
        description: User not authorized to modify this annotation.
      404:
        description: Annotation not found.
      500:
        description: Database error.
    """

    annotation = base.update(Annotation, annotation_id, body)

    return annotation.serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@annotBp.patch("/bulk-update")
@login_required
@permission_required("access")
@validate()
def bulk_update(body: BulkUpdateAnnotationsReq):
    """
    Update several annotation objects in the database in a batch.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: BulkUpdateAnnotationsReq
        description: Array of annotation update requests, each containing annotation_id.
    responses:
      200:
        description: List of updated annotations.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized.
      404:
        description: One or more annotations not found.
      500:
        description: Database error.
    """

    annotations = []

    for req in body.requests:
        if not req.annotation_id:
            continue

        annotations.append(base.update(Annotation, req.annotation_id, req))

    return [annot.serialize() for annot in annotations], 200


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@annotBp.delete("/<int:annotation_id>")
@annotBp.delete("/<uuid:annotation_id>")
@login_required
@permission_required("access")
def delete(annotation_id: int | UUID):
    """
    Delete an annotation by its integer ID or UUID.
    ---
    parameters:
      - name: annotation_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the annotation to delete.
    responses:
      204:
        description: Annotation deleted successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized to delete this annotation.
      404:
        description: Annotation not found.
      500:
        description: Database error.
    """

    base.delete(Annotation, annotation_id)

    return "", 204


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@annotBp.delete("/bulk-delete")
@login_required
@permission_required("access")
@validate()
def bulk_delete(body: BulkDeleteAnnotationsReq):
    """
    Delete multiple annotations in a batch.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: BulkDeleteAnnotationsReq
        description: Array of delete requests containing annotation IDs.
    responses:
      204:
        description: Annotations deleted successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized.
      500:
        description: Database error.
    """
    for req in body.requests:
        base.delete(Annotation, req.annotation_id)

    return "", 204
