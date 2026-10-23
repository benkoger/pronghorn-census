# Endpoints for managing schemas in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.object_models.project_management.labels import Label
from database.object_models.project_management.models import Model
from database.object_models.project_management.schemas import Schema, createSchemaReq

schemaBp = Blueprint("schemas", __name__, url_prefix="/api/v1/schemas")


# ---------------------------------------------------------------------------------------------------------------------------
# GET


@schemaBp.get("/<int:schema_id>/labels")
@schemaBp.get("/<uuid:schema_id>/labels")
@login_required
@permission_required("access")
def get_labels(schema_id: int | UUID):
    """
    Retrieve all labels associated with a specific schema.
    ---
    parameters:
      - name: schema_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the schema (integer ID or UUID).
    responses:
      200:
        description: List of labels (returns empty list if none exist).
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this schema.
      404:
        description: Schema not found.
      500:
        description: Database error.
    """

    labels = base.get_children(Label, Schema, schema_id)

    return [label.serialize() for label in labels], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@schemaBp.get("/<int:schema_id>/models")
@schemaBp.get("/<uuid:schema_id>/models")
@login_required
@permission_required("access")
def get_models(schema_id: int | UUID):
    """
    Retrieve all models associated with a specific schema.
    ---
    parameters:
      - name: schema_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the schema (integer ID or UUID).
    responses:
      200:
        description: List of models (returns empty list if none exist).
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this schema.
      404:
        description: Schema not found.
      500:
        description: Database error.
    """

    models = base.get_children(Model, Schema, schema_id)

    return [model.serialize() for model in models], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@schemaBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: createSchemaReq):
    """
    Create a new schema object.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: createSchemaReq
        description: Schema creation payload including name and associated project IDs.
    responses:
      201:
        description: Schema created successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized to create schemas.
      409:
        description: Conflict or unique constraint violation.
      500:
        description: Database error.
    """
    schema = base.insert(Schema, body)

    return schema.serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@schemaBp.delete("/<int:schema_id>")
@schemaBp.delete("/<uuid:schema_id>")
@login_required
@permission_required("access")
def delete_schema(schema_id: int | UUID):
    """
    Delete a schema by its integer ID or UUID.
    ---
    parameters:
      - name: schema_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the schema to delete.
    responses:
      204:
        description: Schema deleted successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized to delete this schema.
      404:
        description: Schema not found.
      500:
        description: Database error.
    """

    base.delete(Schema, schema_id)

    return "", 204
