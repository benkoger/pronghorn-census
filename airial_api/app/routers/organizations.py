# Endpoints for managing organizations in the api
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------#

from flask import Blueprint, abort, current_app
from flask_login import login_required
from psycopg import DatabaseError
from app.decorators import permission_required
from database.object_models.user_management import createOrganizationReq

from flask_pydantic import validate

from app.extensions import base

orgBp = Blueprint("organizations", __name__, url_prefix="/api/v1/organizations")

# ---------------------------------------------------------------------------------------------------------------------------#
# POST


@orgBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: createOrganizationReq):
    """ """
    try:
        org = base.create_organizaztion(body)
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return org.to_dict(), 201
