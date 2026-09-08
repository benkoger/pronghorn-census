# Endpoints for managing annotations in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from typing import cast

from flask import Blueprint
from flask_login import current_user, login_required
from flask_pydantic import validate
from app.decorators import permission_required
from app.extensions import base
from database.object_models.core import CreateAnnotationReq, UpdateAnnotationReq
from database.object_models.core.annotations import (
    Annotation,
    BulkCreateAnnotationReq,
    BulkUpdateAnnotationsReq,
    BulkDeleteAnnotationsReq,
)
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
            - name: create annotation request
            in: body
            type: CreateAnnotationReq
            required: true
    responses:
            201:
                    description: Created successfuly.
            401:
                    description: User not authorized to perform this action.
            500:
                    description: Unexpected error.
    """
    annotation = base.insert(Annotation, body, cast(User, current_user))

    return annotation.serialize(), 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# This could be optimized pretty heavily
@annotBp.post("/bulk-import")
@validate()
@login_required
@permission_required("access")
def import_annotation(body: BulkCreateAnnotationReq):
    """ """

    annotations = []

    for req in body.requests:
        annotations.append(base.insert(Annotation, req, cast(User, current_user)))

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
    Update annotation objects in the database.
    ---
    parameters:
            - name: annotation_id
            in: path
            type: string
            required: true
    responses:
            200:
                    description: Annotation updated successfully.
            400:
                    description: Invalid UUID.
            404:
                    description: Annotation not found.
            500:
                    description: Unexpected error.
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
    Update several annotation objects in the database.
    ---
    responses:
            200:
                description: Request completed successfully.
            404:
                description: Annotation not found.
            401:
                description: User not authorized.
            500:
                description: Unexpected error.
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
    """ """

    base.delete(Annotation, annotation_id)

    return "", 204


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@annotBp.delete("/bulk-delete")
@login_required
@permission_required("acccess")
@validate()
def bulk_delete(body: BulkDeleteAnnotationsReq):
    """ """
    for req in body.requests:
        base.delete(Annotation, req.annotation_id)

    return "", 204
