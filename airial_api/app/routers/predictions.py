# Endpoints for managing predictions in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from flask import Blueprint, abort
from flask_login import current_user, login_required
from flask_pydantic import validate
from psycopg.errors import DatabaseError

from typing import cast
from app.decorators import permission_required
from app.extensions import base
from database.object_models.user_management import User
from database.errors import AuthorizationFailure, FailedToCreate, ObjectNotFound
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
    try:
        predictions = base.get_predictions(query)
    except AuthorizationFailure as e:
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        print(e)
        abort(500)

    return [pred.to_dict() for pred in predictions], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@predBp.get("/<string:prediction_id>")
@permission_required("access")
@login_required
def get_prediction_by_id(prediction_id: str):
    """ """
    try:
        prediciton = base.get_prediction(UUID(prediction_id))
    except AuthorizationFailure as e:
        abort(401, str(e))
    except ObjectNotFound as e:
        abort(404, str(e))
    except (DatabaseError, Exception) as e:
        print(e)
        abort(500)

    return prediciton.to_dict(), 200


# ---------------------------------------------------------------------------------------------------------------------------#
# POST


@predBp.post("")
@login_required
@permission_required("access")
@validate()
def create_prediction(body: CreatePredictionReq):
    """ """
    try:
        prediction = base.create_prediction(body)
    except AuthorizationFailure as e:
        abort(401, str(e))
    except FailedToCreate as e:
        abort(422, str(e))
    except (DatabaseError, Exception) as e:
        print(e)
        abort(500)

    return prediction.to_dict(), 201
