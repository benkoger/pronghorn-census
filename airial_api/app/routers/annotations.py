# Endpoints for managing annotations in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from typing import cast, List

from flask import Blueprint, abort
from flask_login import current_user, login_required
from flask_pydantic import validate
from app.decorators import permission_required
from app.extensions import base
from database.object_models.core import CreateAnnotationReq, UpdateAnnotationReq
from database.object_models.core.annotations import (
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
    annotation = base.create_annotation(body, cast(User, current_user))

    return annotation.to_dict(), 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@annotBp.post("/bulk-import")
@validate()
@login_required
@permission_required("access")
def import_annotation(body: BulkCreateAnnotationReq):
    """ """

    annotations = []

    for req in body.requests:
        annotations.append(base.create_annotation(req, cast(User, current_user)))

    return [annot.to_dict() for annot in annotations], 201


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@annotBp.patch("/<string:annotation_id>")
@login_required
@permission_required("access")
@validate()
def update(body: UpdateAnnotationReq, annotation_id: str):
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

    annotation = base.update_annotation(
        UUID(annotation_id), body, cast(User, current_user)
    )

    return annotation.to_dict(), 200


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
        annotations.append(
            base.update_annotation(req.annotation_id, req, cast(User, current_user))
        )

    return [annot.to_dict() for annot in annotations], 200


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@annotBp.delete("/<string:annotation_id>")
@login_required
@permission_required("access")
def delete(annotation_id: str):
    """ """

    res = base.delete_annotation(UUID(annotation_id))

    return "", 200 if res else abort(500)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@annotBp.delete("/bulk-delete")
@login_required
@permission_required("acccess")
@validate()
def bulk_delete(body: BulkDeleteAnnotationsReq):
    """ """
    results: List[bool] = []

    for req in body.requests:
        results.append(base.delete_annotation(req.annotation_id))

    return "", 200 if all(results) else abort(500)
