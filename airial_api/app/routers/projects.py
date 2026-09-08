# Endpoints for managing projects in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from uuid import UUID

from database.object_models.core.images import Image
from database.object_models.project_management.herd_units import HerdUnit
from database.object_models.project_management.models import Model
from database.object_models.project_management.projectmanagement_bindings import (
    ProjectsModels,
    ProjectsSchemas,
    ProjectsSurveys,
)
from database.object_models.project_management.projects import createProjectReq
from database.object_models.project_management.schemas import Schema
from database.object_models.project_management.surveys import Survey
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
    Project,
    ProjectsHerdUnits,
)

from database.object_models.user_management import OrganizationProject
from database.object_models.core import Prediction

projectBp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@projectBp.get("")
@login_required
@permission_required("access")
@validate()
def get_all():
    """ """

    org_id = session.get("active_org_uuid")
    active_org = session.get(f"org_{org_id}")
    org = Organization(**unpackb(active_org))

    projects = base.get_related(
        OrganizationProject,
        Project,
        {"organization_id": org.organization_id},
    )

    return [proj.serialize() for proj in projects], 200


@projectBp.get("/<int:project_id>")
@projectBp.get("/<uuid:project_id>")
@login_required
@permission_required("access")
def get_by_id(project_id: int | UUID):
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

    return base.get(Project, project_id).serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@projectBp.get("/<int:project_id>/models")
@projectBp.get("/<uuid:project_id>/models")
@permission_required("access")
@login_required
def get_models(project_id: int | UUID):
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

    if isinstance(project_id, UUID):
        project = base.get(Project, project_id)
        project_id = project.project_id

    models = base.get_related(ProjectsModels, Model, {"project_id": project_id})

    return [model.serialize() for model in models], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@projectBp.get("/<int:project_id>/herd-units")
@projectBp.get("/<uuid:project_id>/herd-units")
@login_required
@permission_required("access")
def get_herd_units(project_id: int | UUID):
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

    if isinstance(project_id, UUID):
        project = base.get(Project, project_id)
        project_id = project.project_id

    herd_units = base.get_related(
        ProjectsHerdUnits, HerdUnit, {"project_id": project_id}
    )

    return [herd_unit.serialize() for herd_unit in herd_units], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@projectBp.get("/<int:project_id>/surveys")
@projectBp.get("/<uuid:project_id>/surveys")
@login_required
@permission_required("access")
def get_surveys(project_id: int | UUID):
    """ """

    surveys = base.get_related(ProjectsSurveys, Survey, {"project_id": project_id})

    return [survey.serialize() for survey in surveys], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@projectBp.get("/<int:project_id>/schemas")
@projectBp.get("/<uuid:project_id>/schemas")
@login_required
@permission_required("access")
def get_schemas(project_id: int | UUID):
    """ """

    schemas = base.get_related(ProjectsSchemas, Schema, {"project_id": project_id})

    return [schema.serialize() for schema in schemas], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@projectBp.get("/<int:project_id>/image-count")
@projectBp.get("/<uuid:project_id>/image-count")
@login_required
@permission_required("access")
def image_count(project_id: int | UUID):
    """ """

    count = base.count(
        Image,
        Project,
        project_id,
        ProjectsHerdUnits,
    )

    return {"count": count}, 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@projectBp.get("/<int:project_id>/prediction-count")
@projectBp.get("/<uuid:project_id>/prediction-count")
@login_required
@permission_required("access")
def prediction_count(project_id: int | UUID):
    """ """

    count = base.count(
        Prediction,
        Project,
        project_id,
        ProjectsHerdUnits,
        Image,
    )

    return {"count": count}, 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@projectBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: createProjectReq):
    """ """
    return base.insert(Project, body, cast(User, current_user)).serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@projectBp.delete("/<int:project_id>")
@projectBp.delete("<uuid:project_id>")
@login_required
@permission_required("access")
def delete(project_id: int | UUID):
    """ """

    base.delete(Project, project_id)

    return "", 204
