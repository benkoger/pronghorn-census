# Endpoints for managing projects in the API
# Author: Michael B. Lance

"""Endpoints for managing projects in the API."""

# ---------------------------------------------------------------------------------------------------------------------------

from typing import cast
from uuid import UUID

from flask import Blueprint, session
from flask_login import current_user, login_required
from flask_pydantic import validate
from msgpack import unpackb

from app.decorators import permission_required
from app.extensions import base
from database.object_models.project_management import (
    Project,
    ProjectsHerdUnits,
)
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
from database.object_models.user_management import Organization, OrganizationProject, User
from database.object_models.user_management.roles import Role

projectBp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@projectBp.get("")
@login_required
@permission_required("access")
@validate()
def get_all():
    """Retrieve all projects belonging to the currently active session organization.

    ---
    responses:
      200:
        description: List of projects for the active organization.
      401:
        description: User not authenticated or session lacks active organization.
      500:
        description: Database or session error.
    """
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
    """Request a project object from the database using its integer PK or UUID.

    ---
    parameters:
      - name: project_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the project (integer ID or UUID).
    responses:
      200:
        description: The requested project was found.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this project.
      404:
        description: No project record found for the provided ID.
      500:
        description: Database error.
    """
    return base.get(Project, project_id).serialize(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@projectBp.get("/<int:project_id>/models")
@projectBp.get("/<uuid:project_id>/models")
@permission_required("access")
@login_required
def get_models(project_id: int | UUID):
    """Retrieve all models associated with a specific project.

    ---
    parameters:
      - name: project_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the project (integer ID or UUID).
    responses:
      200:
        description: List of models (returns empty list if none exist).
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this project.
      404:
        description: Project not found.
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
    """Retrieve all herd units associated with a specific project.

    ---
    parameters:
      - name: project_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the project (integer ID or UUID).
    responses:
      200:
        description: List of herd units (returns empty list if none exist).
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this project.
      404:
        description: Project not found.
      500:
        description: Database error.
    """
    if isinstance(project_id, UUID):
        project = base.get(Project, project_id)
        project_id = project.project_id

    herd_units = base.get_related(ProjectsHerdUnits, HerdUnit, {"project_id": project_id})

    return [herd_unit.serialize() for herd_unit in herd_units], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@projectBp.get("/<int:project_id>/surveys")
@projectBp.get("/<uuid:project_id>/surveys")
@login_required
@permission_required("access")
def get_surveys(project_id: int | UUID):
    """Retrieve all surveys associated with a specific project.

    ---
    parameters:
      - name: project_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the project (integer ID or UUID).
    responses:
      200:
        description: List of surveys (returns empty list if none exist).
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this project.
      404:
        description: Project not found.
      500:
        description: Database error.
    """
    if isinstance(project_id, UUID):
        project = base.get(Project, project_id)
        project_id = project.project_id

    surveys = base.get_related(ProjectsSurveys, Survey, {"project_id": project_id})

    return [survey.serialize() for survey in surveys], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@projectBp.get("/<int:project_id>/schemas")
@projectBp.get("/<uuid:project_id>/schemas")
@login_required
@permission_required("access")
def get_schemas(project_id: int | UUID):
    """Retrieve all schemas associated with a specific project.

    ---
    parameters:
      - name: project_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the project (integer ID or UUID).
    responses:
      200:
        description: List of schemas (returns empty list if none exist).
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this project.
      404:
        description: Project not found.
      500:
        description: Database error.
    """
    if isinstance(project_id, UUID):
        project = base.get(Project, project_id)
        project_id = project.project_id

    schemas = base.get_related(ProjectsSchemas, Schema, {"project_id": project_id})

    return [schema.serialize() for schema in schemas], 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@projectBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: createProjectReq):
    """Create a new project object.

    ---
    parameters:
      - name: body
        in: body
        required: true
        type: createProjectReq
        description: Project creation payload containing name and organization_ids.
    responses:
      201:
        description: Project created successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized to create projects.
      409:
        description: Conflict or unique constraint violation.
      500:
        description: Database error.
    """
    role = base.where(Role, {"name": "admin"})[0]

    return base.insert(Project, body, cast(User, current_user), role).serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# DELETE


@projectBp.delete("/<int:project_id>")
@projectBp.delete("/<uuid:project_id>")
@login_required
@permission_required("access")
def delete(project_id: int | UUID):
    """Delete a project by its integer ID or UUID.

    ---
    parameters:
      - name: project_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the project to delete.
    responses:
      204:
        description: Project deleted successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized to delete this project.
      404:
        description: Project not found.
      500:
        description: Database error.
    """
    base.delete(Project, project_id)

    return "", 204
