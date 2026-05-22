# Endpoints for managing projects in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

from database.object_models.project_management.projects import createProjectReq
from database.object_models.user_management import User, Organization
from flask import Blueprint, session
from flask_login import login_required, current_user
from flask_pydantic import validate
from msgpack import unpackb
from typing import cast

from app.decorators import permission_required

from app.extensions import base
from database.object_models.project_management import (
    ProjectQuery,
)

projectBp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@projectBp.get("")
@login_required
@permission_required("access")
@validate()
def get_all(query: ProjectQuery):
    """ """

    org_id = session.get("active_org_uuid")
    active_org = session.get(f"org_{org_id}")
    org = Organization(**unpackb(active_org))

    projects = base.get_projects(query, org)

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

    return base.get_project(UUID(project_id)).to_dict(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


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

    models = base.get_project_models(UUID(project_id))

    return [model.to_dict() for model in models], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


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

    herd_units = base.get_project_herd_units(UUID(project_id))

    return [herd_unit.to_dict() for herd_unit in herd_units], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@projectBp.get("/<string:project_id>/schemas")
@login_required
@permission_required("access")
def get_surveys(project_id: str):
    """ """

    schemas = base.get_project_schemas(UUID(project_id))

    return [schema.to_dict() for schema in schemas], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@projectBp.get("/<string:project_id>/image-count")
@login_required
@permission_required("access")
def image_count(project_id: str):
    """ """

    count = base.get_project_image_count(UUID(project_id))

    return {"count": count}, 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@projectBp.get("/<string:project_id>/prediction-count")
@login_required
@permission_required("access")
def prediction_count(project_id: str):
    """ """

    count = base.get_project_prediction_count(UUID(project_id))

    return {"count": count}, 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@projectBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: createProjectReq):
    """ """
    return base.create_project(body, cast(User, current_user)).to_dict(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@projectBp.delete("/<string:project_id>")
@login_required
@permission_required("access")
def delete(project_id: str):
    """ """

    base.delete_project(UUID(project_id))

    return "", 204
