# Endpoints for managing schemas in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

from flask import Blueprint, abort, current_app
from flask_login import login_required
from flask_pydantic import validate
from psycopg.errors import DatabaseError

from app.decorators import permission_required
from app.extensions import base
from database.errors import ObjectNotFound, AuthorizationFailure
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
    try:
        labels = base.get_schema_labels(UUID(schema_id))
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return [label.to_dict() for label in labels], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@schemaBp.get("<string:schema_id>/models")
@login_required
@permission_required("access")
def get_models(schema_id: str):
    """ """
    try:
        models = base.get_schema_models(UUID(schema_id))
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return [model.to_dict() for model in models], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@schemaBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: createSchemaReq):
    """ """
    try:
        schema = base.create_schema(body)

    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return schema.to_dict(), 201
