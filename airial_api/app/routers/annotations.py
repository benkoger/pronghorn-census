# Endpoints for managing annotations in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from typing import cast, List

from flask import Blueprint, abort, current_app
from flask_login import current_user, login_required
from flask_pydantic import validate
from psycopg.errors import DatabaseError

from app.extensions import base
from database.errors import AuthorizationFailure, ObjectNotFound
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
@validate()
@login_required
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
    try:
        annotation = base.create_annotation(body, cast(User, current_user))

    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return annotation.to_dict(), 201


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@annotBp.post("/bulk-import")
@validate()
@login_required
def import_annotation(body: BulkCreateAnnotationReq):
    """ """
    try:
        annotations = []

        for req in body.requests:
            annotations.append(base.create_annotation(req, cast(User, current_user)))

    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return [annot.to_dict() for annot in annotations], 201


# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@annotBp.patch("/<string:annotation_id>")
@validate()
@login_required
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
    try:
        annotation = base.update_annotation(
            UUID(annotation_id), body, cast(User, current_user)
        )

    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return annotation.to_dict(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@annotBp.patch("/bulk-update")
@validate()
@login_required
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
    try:
        annotations = []

        for req, annot_id in zip(body.requests, body.ids):
            annotations.append(
                base.update_annotation(annot_id, req, cast(User, current_user))
            )

    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return [annot.to_dict() for annot in annotations], 200


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@annotBp.delete("/<string:annotation_id>")
@login_required
def delete(annotation_id: str):
    """ """
    try:
        res = base.delete_annotation(UUID(annotation_id), cast(User, current_user))

    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return "", 200 if res else abort(500)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@annotBp.delete("/bulk-delete")
@validate()
@login_required
def bulk_delete(body: BulkDeleteAnnotationsReq):
    """ """
    results: List[bool] = []

    try:
        for annot_id in body.ids:
            results.append(base.delete_annotation(annot_id, cast(User, current_user)))

    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return "", 200 if all(results) else abort(500)
