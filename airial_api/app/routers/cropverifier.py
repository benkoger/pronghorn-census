# Endpoints for crop verification in the API
# Author: Michael B. Lance / Antigravity

"""Endpoints for crop verification in the API."""
# ---------------------------------------------------------------------------------------------------------------------------

from typing import cast

from flask import Blueprint
from flask_login import current_user, login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.modules import cropverifier
from database.object_models.base import Keyring
from database.object_models.core import RAQuery
from database.object_models.project_management.surveys import Survey
from database.object_models.user_management import User

verifierBp = Blueprint("verifier", __name__, url_prefix="/api/v1/verifier")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@verifierBp.get("/area-needing-reviewed")
@login_required
@permission_required("access")
@validate()
def get(query: RAQuery):
    """Retrieve crops for an available image in survey order, locking the image.

    ---
    parameters:
      - name: survey_id
        in: query
        required: true
        type: array
        items:
          type: string
          format: uuid
        description: Survey ID filter.
      - name: include_reviewed
        in: query
        required: false
        type: boolean
        description: Whether to include already reviewed crops.
    responses:
      200:
        description: List of reviewed areas on the locked image.
      204:
        description: No areas to review.
      400:
        description: Invalid query parameters.
      401:
        description: Unauthorized.
      500:
        description: Database error.
    """
    survey = base.get(Survey, query.survey_id[0])
    survey_ids = Keyring(survey.survey_id, survey.uuid)

    crops = base.execute(
        cropverifier.get_available_crops,
        survey_ids,
        query,
        cast(User, current_user),
    )

    if not crops:
        return "", 204

    return [crop.serialize() for crop in crops], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@verifierBp.get("/needing-reviewed")
@login_required
@permission_required("access")
@validate()
def get_selection_count(query: RAQuery):
    """Count of crops matching review criteria in the survey.

    ---
    parameters:
      - name: survey_id
        in: query
        required: true
        type: array
        items:
          type: string
          format: uuid
        description: Survey ID filter.
      - name: include_reviewed
        in: query
        required: false
        type: boolean
        description: Whether to include already reviewed crops.
      - name: include_opened
        in: query
        required: false
        type: boolean
        description: Whether to include currently opened images.
    responses:
      200:
        description: Count of reviewed areas needing review.
      400:
        description: Invalid query parameters.
      401:
        description: Unauthorized.
      500:
        description: Database error.
    """
    survey = base.get(Survey, query.survey_id[0])
    survey_ids = Keyring(survey.survey_id, survey.uuid)

    count = base.execute(
        cropverifier.get_selection_count,
        survey_ids,
        query,
    )

    return {"count": count}, 200
