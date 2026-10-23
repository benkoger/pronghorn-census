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
    Retrieve multiple prediction objects by a list of integer IDs or UUIDs.
    ---
    parameters:
      - name: object_ids
        in: query
        required: true
        type: array
        items:
          oneOf:
            - type: integer
            - type: string
              format: uuid
        description: List of prediction primary keys (integer IDs or UUIDs).
    responses:
      200:
        description: List of predictions found.
      400:
        description: Invalid query format.
      401:
        description: User not authorized.
      500:
        description: Database error.
    """

    predictions = base.bulk_get(Prediction, query)

    return [pred.serialize() for pred in predictions], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@predBp.get("/<int:prediction_id>")
@predBp.get("/<uuid:prediction_id>")
@permission_required("access")
@login_required
def get_prediction_by_id(prediction_id: int | UUID):
    """
    Retrieve a single prediction by its integer ID or UUID.
    ---
    parameters:
      - name: prediction_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the prediction (integer ID or UUID).
    responses:
      200:
        description: Prediction record found and returned.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized to access this prediction.
      404:
        description: Prediction not found.
      500:
        description: Database error.
    """

    return base.get(Prediction, prediction_id).serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------#
# POST


@predBp.post("")
@login_required
@permission_required("access")
@validate()
def create_prediction(body: CreatePredictionReq):
    """
    Create a new prediction record.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreatePredictionReq
        description: Prediction creation payload with bounding box coordinates, label, score, model_ids, and image_ids.
    responses:
      200:
        description: Prediction created successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized to create predictions.
      500:
        description: Database error.
    """

    return base.insert(Prediction, body).serialize(), 200
