# Endpoints for managing organizations in the api
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------#

from flask import Blueprint
from flask_login import login_required
from app.decorators import permission_required
from database.object_models.user_management import createOrganizationReq
from database.object_models.user_management import Organization

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
    """Create a new organization using the schema-driven base._insert"""
    org = base._insert(Organization, body)
    return org.serialize(), 201
