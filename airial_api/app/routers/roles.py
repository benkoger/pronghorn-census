# Endpoints for managing Roles in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID
from flask import Blueprint
from flask_login import login_required
from flask_pydantic import validate

from app.decorators import permission_required
from app.extensions import base
from database.object_models.base import BulkRequest
from database.object_models.user_management.roles import Role

roleBp = Blueprint("roles", __name__, url_prefix="/api/v1/roles")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@roleBp.get("")
@login_required
@permission_required("access")
@validate()
def get(query: BulkRequest):
    """ """
    roles = base.bulk_get(Role, query)

    return [role.serialize() for role in roles], 200


@roleBp.get("/<int:role_id>")
@roleBp.get("/<uuid:role_id>")
@login_required
@permission_required("access")
@validate()
def get_by_id(role_id: int | UUID):
    """ """

    return base.get(Role, role_id).serialize(), 200
