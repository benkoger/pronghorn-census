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
    Retrieve labels for a schema
    ---
    responses:
      200:
            description: List of labels.
      404:
            description: No labels / schema found.
      500:
            description: Database error.
    """

    labels = base.get_children(Label, Schema, schema_id)

    return [label.serialize() for label in labels], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@schemaBp.get("<int:schema_id>/models")
@schemaBp.get("<uuid:schema_id>/models")
@login_required
@permission_required("access")
def get_models(schema_id: int | UUID):
    """ """

    models = base.get_children(Model, Schema, schema_id)

    return [model.serialize() for model in models], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@schemaBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: createSchemaReq):
    """ """
    schema = base.insert(Schema, body)

    return schema.serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@schemaBp.delete("/<int:schema_id>")
@schemaBp.delete("/<uuid:schema_id>")
@login_required
@permission_required("access")
def delete_schema(schema_id: int | UUID):
    """ """

    base.delete(Schema, schema_id)

    return "", 204
