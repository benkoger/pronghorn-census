# Endpoints for managing schemas in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.object_models.project_management.schemas import createSchemaReq

schemaBp = Blueprint("schemas", __name__, url_prefix="/api/v1/schemas")


# ---------------------------------------------------------------------------------------------------------------------------
# GET


@schemaBp.get("/<string:schema_id>/labels")
@login_required
@permission_required("access")
def get_labels(schema_id: str):
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

    labels = base.get_schema_labels(UUID(schema_id))

    return [label.to_dict() for label in labels], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@schemaBp.get("<string:schema_id>/models")
@login_required
@permission_required("access")
def get_models(schema_id: str):
    """ """

    models = base.get_schema_models(UUID(schema_id))

    return [model.to_dict() for model in models], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@schemaBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: createSchemaReq):
    """ """
    schema = base.create_schema(body)

    return schema.to_dict(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@schemaBp.delete("/<string:schema_id>")
@login_required
@permission_required("access")
def delete_schema(schema_id: str):
    """ """

    base.delete_schema(UUID(schema_id))

    return "", 204
