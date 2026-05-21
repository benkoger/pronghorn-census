# Endpoints for crop verification in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------#

from typing import cast

from flask import Blueprint
from flask_login import current_user, login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.object_models.core import RAQuery
from database.object_models.user_management import User

verifierBp = Blueprint("verifier", __name__, url_prefix="/api/v1/verifier")

# ---------------------------------------------------------------------------------------------------------------------------#
# GET


@verifierBp.get("/area-needing-reviewed")
@login_required
@permission_required("access")
@validate()
def get(query: RAQuery):
    """
    Retrieve a reviewed area
    ---
    paramaters:
      - in: query
            name: herd_unit_id
            type: number
      - in: query
            name: survey_id
            type: number
    responses:
            200:
                    description: List of reviewed areas.
            204:
                    description: No areas to review.
            400:
                    description: Invalid UUID format.
            500:
                    description: Database error.
    """

    query.num = 1
    reviewed_area = base.get_crop_to_review(query, cast(User, current_user))

    # Dont return 404, it is not an error for there to not be any crops needing reviewed
    if reviewed_area is None:
        return "", 204

    return reviewed_area.to_dict(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@verifierBp.get("/needing-reviewed")
@login_required
@permission_required("access")
@validate()
def get_selection_count(query: RAQuery):
    """ """
    count = base.get_crop_to_review_selection_count(query)

    return {"count": count}, 200
