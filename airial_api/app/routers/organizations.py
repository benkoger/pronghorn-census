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
    """
    Create a new organization using the schema-driven base._insert.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: createOrganizationReq
        description: Organization creation payload containing the organization name.
    responses:
      201:
        description: Organization created successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized to create organizations.
      409:
        description: Organization name already exists.
      500:
        description: Database error.
    """
    org = base._insert(Organization, body)
    return org.serialize(), 201
