# Endpoints for managing projects in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from database.errors import AuthorizationFailure
from database.object_models.user_management import User, Organization
from flask import Blueprint, abort, current_app, session
from flask_login import login_required, current_user
from flask_pydantic import validate
from msgpack import unpackb
from psycopg.errors import DatabaseError
from typing import cast

from app.decorators import permission_required

from app.extensions import base
from database import ObjectNotFound
from database.object_models.project_management import (
    ProjectQuery,
)

projectBp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")

# ---------------------------------------------------------------------------------------------------------------------------#
# GET


@projectBp.get("")
@login_required
@permission_required("access")
@validate()
def get_all(query: ProjectQuery):
    """ """
    try:
        org_id = session.get("active_org_uuid")
        active_org = session.get(f"org_{org_id}")
        org = Organization(**unpackb(active_org))

        projects = base.get_projects(query, org, cast(User, current_user))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)
    return [proj.to_dict() for proj in projects], 200


@projectBp.get("/<string:project_id>")
@login_required
@permission_required("access")
def get_by_id(project_id: str):
    """
    Request a project object from the database using its UUID.
    ---
    parameters:
      - project_id
            in: path
            type: string
            required: true
    responses:
      200:
            description: The requested project was found.
      400:
            description: Invalid UUID format provided.
      404:
            description: No project record found for the provided ID.
      500:
            description: Database Error.
    """
    try:
        project = base.get_project(UUID(project_id))
    except ValueError as e:
        current_app.logger.exception(e)
        abort(400, str(e))
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return project.to_dict(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@projectBp.get("/<string:project_id>/models")
@permission_required("access")
@login_required
def get_models(project_id: str):
    """
    Retrieve models for a specific project
    ---
    parameters:
            - name: project_id
            in: path
            type: string
            required: true
    responses:
      200:
            description: List of models.
      404:
            description: No project found.
      500:
            description: Database error.
    """
    try:
        models = base.get_project_models(UUID(project_id))
    except ValueError as e:
        current_app.logger.exception(e)
        abort(400, str(e))
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401)
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return [model.to_dict() for model in models], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


@projectBp.get("/<string:project_id>/herd-units")
@login_required
@permission_required("access")
def get_herd_units(project_id: str):
    """
    Retrieve herd units for a specific project
    ---
    responses:
      200:
            description: List of herd units.
      404:
            description: No project found.
      500:
            description: Database error.
    """
    try:
        herd_units = base.get_project_herd_units(UUID(project_id))
    except ValueError as e:
        abort(400, str(e))
    except ObjectNotFound as e:
        abort(404, str(e))
    except (DatabaseError, Exception) as e:
        print(e)
        abort(500)

    return [herd_unit.to_dict() for herd_unit in herd_units], 200
