# Endpoints for managing Roles in the API
# Author: Michael B. Lance

"""Endpoints for managing user roles in the API."""

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
    """Retrieve multiple roles by a list of integer IDs or UUIDs.

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
        description: List of role primary keys (integer IDs or UUIDs).
    responses:
      200:
        description: List of roles found.
      400:
        description: Invalid query format.
      401:
        description: User not authorized.
      500:
        description: Database error.
    """
    roles = base.bulk_get(Role, query)

    return [role.serialize() for role in roles], 200


@roleBp.get("/<int:role_id>")
@roleBp.get("/<uuid:role_id>")
@login_required
@permission_required("access")
@validate()
def get_by_id(role_id: int | UUID):
    """Request a role object from the database using its integer PK or UUID.

    ---
    parameters:
      - name: role_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the role (integer ID or UUID).
    responses:
      200:
        description: The requested role was found.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this role.
      404:
        description: No role record found for the provided ID.
      500:
        description: Database error.
    """
    return base.get(Role, role_id).serialize(), 200
