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
    """ """

    return base.insert(Label, body).serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@labelBp.delete("/<int:label_id>")
@labelBp.delete("/<uuid:label_id>")
@login_required
@permission_required("access")
def delete(label_id: int | UUID):
    """ """

    base.delete(Label, label_id)

    return "", 204
