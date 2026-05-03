# Endpoints for managing Roles in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------


from flask import Blueprint, abort, current_app
from flask_login import login_required
from flask_pydantic import validate
from psycopg import DatabaseError

from app.decorators import permission_required
from app.extensions import base
from database.object_models.user_management.roles import RoleQuery

roleBp = Blueprint("roles", __name__, url_prefix="/api/v1/roles")

# ---------------------------------------------------------------------------------------------------------------------------


@roleBp.get("")
@login_required
@permission_required("access")
@validate()
def get(query: RoleQuery):
    """ """
    try:
        roles = base.get_roles(query)
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return [role.to_dict() for role in roles], 200
