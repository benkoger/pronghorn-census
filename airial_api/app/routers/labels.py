# Endpoints for managing labels in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from flask import Blueprint, abort, current_app
from flask_login import login_required
from flask_pydantic import validate
from psycopg.errors import DatabaseError
from app.decorators import permission_required
from uuid import UUID
from database.errors import ObjectNotFound
from database.object_models.project_management import CreateLabelReq

from app.extensions import base

labelBp = Blueprint("labels", __name__, url_prefix="/api/v1/labels")

# ---------------------------------------------------------------------------------------------------------------------------
# POST


@labelBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateLabelReq):
    """ """
    try:
        label = base.create_label(body)

    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return label.to_dict(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@labelBp.delete("/<string:label_id>")
@login_required
@permission_required("access")
def delete(label_id: str):
    """ """
    try:
        base.delete_label(UUID(label_id))
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return "", 204
