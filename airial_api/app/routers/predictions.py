# Endpoints for managing predictions in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.object_models.core import (
    PredictionQuery,
    CreatePredictionReq,
)

predBp = Blueprint("predictions", __name__, url_prefix="/api/v1/predictions")

# ---------------------------------------------------------------------------------------------------------------------------#
# GET


@predBp.get("")
@login_required
@permission_required("access")
@validate()
def get_predictions(query: PredictionQuery):
    """ """

    predictions = base.get_predictions(query)

    return [pred.to_dict() for pred in predictions], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@predBp.get("/<string:prediction_id>")
@permission_required("access")
@login_required
def get_prediction_by_id(prediction_id: str):
    """ """

    return base.get_prediction(UUID(prediction_id)).to_dict(), 200


# ---------------------------------------------------------------------------------------------------------------------------#
# POST


@predBp.post("")
@login_required
@permission_required("access")
@validate()
def create_prediction(body: CreatePredictionReq):
    """ """

    return base.create_prediction(body).to_dict(), 200
