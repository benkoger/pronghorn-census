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

labelBp = Blueprint("labels", __name__, url_prefix="/api/v1/labels")

# ---------------------------------------------------------------------------------------------------------------------------
# POST


@labelBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateLabelReq):
    """ """

    return base.create_label(body).to_dict(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@labelBp.delete("/<string:label_id>")
@login_required
@permission_required("access")
def delete(label_id: str):
    """ """

    base.delete_label(UUID(label_id))

    return "", 204
