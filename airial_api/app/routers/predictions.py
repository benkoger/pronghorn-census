# Endpoints for managing predictions in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.object_models.base import BulkRequest
from database.object_models.core import (
    CreatePredictionReq,
)
from database.object_models.core.predictions import Prediction

predBp = Blueprint("predictions", __name__, url_prefix="/api/v1/predictions")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@predBp.get("")
@login_required
@permission_required("access")
@validate()
def get_predictions(query: BulkRequest):
    """
     Request a prediction object from the database using its UUID.
    ---
    parameters:
      - name: pred_id
            in: path
            type: string
            required: true
    responses:
      200:
            description: The requested prediction was found.
      400:
            description: Invalid UUID format provided.
      404:
            description: No prediction record found for the provided ID.
    """

    predictions = base.bulk_get(Prediction, query)

    return [pred.serialize() for pred in predictions], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@predBp.get("/<int:prediction_id>")
@predBp.get("/<uuid:prediction_id>")
@permission_required("access")
@login_required
def get_prediction_by_id(prediction_id: int | UUID):
    """ """

    return base.get(Prediction, prediction_id).serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------#
# POST


@predBp.post("")
@login_required
@permission_required("access")
@validate()
def create_prediction(body: CreatePredictionReq):
    """ """

    return base.insert(Prediction, body).serialize(), 200
