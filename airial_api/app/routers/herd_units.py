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
from database.object_models.project_management.herd_units import HerdUnit
from database.object_models.project_management.projectmanagement_bindings import (
    SurveysHerdUnits,
)
from database.object_models.project_management.surveys import Survey

herdunitBp = Blueprint("herd_units", __name__, url_prefix="/api/v1/herd-units")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@herdunitBp.get("/<int:herd_unit_id>")
@herdunitBp.get("/<uuid:herd_unit_id>")
@login_required
@permission_required("access")
def get_by_id(herd_unit_id: int | UUID):
    """ """
    return base.get(HerdUnit, herd_unit_id).serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@herdunitBp.get("/<string:herd_unit_id>/surveys")
@herdunitBp.get("/<uuid:herd_unit_id>/surveys")
@login_required
@permission_required("access")
def get_surveys(herd_unit_id: int | UUID):
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

    if isinstance(herd_unit_id, UUID):
        herd_unit = base.get(HerdUnit, herd_unit_id)
        herd_unit_id = herd_unit.herd_unit_id

    surveys = base.get_related(
        SurveysHerdUnits,
        Survey,
        {"herd_unit_id": herd_unit_id},
    )

    return [survey.serialize() for survey in surveys], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@herdunitBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateHerdUnitReq):
    """ """
    return base.insert(HerdUnit, body).serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@herdunitBp.delete("/<int:herd_unit_id>")
@herdunitBp.delete("/<uuid:herd_unit_id>")
@login_required
@permission_required("access")
def delete(herd_unit_id: int | UUID):
    """ """
    base.delete(HerdUnit, herd_unit_id)

    return "", 204
