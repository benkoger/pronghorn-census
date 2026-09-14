# Endpoints for managing labels in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from app.decorators import permission_required
from uuid import UUID

from database.object_models.project_management import CreateLabelReq

from app.extensions import base
from database.object_models.project_management.labels import Label

labelBp = Blueprint("labels", __name__, url_prefix="/api/v1/labels")

# ---------------------------------------------------------------------------------------------------------------------------
# POST


@labelBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateLabelReq):
    """
    Create a new label object.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateLabelReq
        description: Label creation payload including label number, name, color, and schema_ids.
    responses:
      201:
        description: Label created successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized to create labels.
      409:
        description: Conflict or unique constraint violation.
      500:
        description: Database error.
    """

    return base.insert(Label, body).serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@labelBp.delete("/<int:label_id>")
@labelBp.delete("/<uuid:label_id>")
@login_required
@permission_required("access")
def delete(label_id: int | UUID):
    """
    Delete a label by its integer ID or UUID.
    ---
    parameters:
      - name: label_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the label to delete.
    responses:
      204:
        description: Label deleted successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized to delete this label.
      404:
        description: Label not found.
      500:
        description: Database error.
    """

    base.delete(Label, label_id)

    return "", 204
