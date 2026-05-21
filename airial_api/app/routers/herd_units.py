# Endpoints for managing herd units in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from flask import Blueprint
from flask_login import login_required
from app.decorators import permission_required
from flask_pydantic import validate

from app.extensions import base
from database.object_models.project_management import CreateHerdUnitReq

herdunitBp = Blueprint("herd_units", __name__, url_prefix="/api/v1/herd-units")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@herdunitBp.get("/<string:herd_unit_id>")
@login_required
@permission_required("access")
def get_by_id(herd_unit_id: str):
    """ """
    return base.get_herd_unit(UUID(herd_unit_id)).to_dict(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@herdunitBp.get("/<string:herd_unit_id>/surveys")
@login_required
@permission_required("access")
def get_surveys(herd_unit_id: str):
    """
    Retrieve all surveys associated with a herd unit.
    ---
    parameters:
            - name: survey_id
            in: path
            type: string
            required: true
    responses:
            200:
                    description: List of surveys.
            400:
                    description: Invalid UUID format.
            404:
                    description: No surveys found.
            500:
                    description: Database error.
    """

    surveys = base.get_herd_unit_surveys(
        UUID(herd_unit_id),
    )

    return [survey.to_dict() for survey in surveys], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@herdunitBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateHerdUnitReq):
    """ """
    return base.create_herd_unit(body).to_dict(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@herdunitBp.delete("/<string:herd_unit_id>")
@login_required
@permission_required("access")
def delete(herd_unit_id: str):
    """ """
    base.delete_herd_unit(UUID(herd_unit_id))

    return "", 204
