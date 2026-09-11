# Endpoints for managing surveys in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from flask import Blueprint, request
from app.decorators import permission_required
from database.object_models.core.annotations import Annotation
from database.object_models.project_management import CreateSurveyReq, UpdateSurveyReq
from app.extensions import base
from datetime import datetime
from flask_pydantic import validate
from flask_login import (
    login_required,
)
from uuid import UUID

from database.object_models.project_management.herd_units import HerdUnit
from database.object_models.project_management.surveys import Survey, SurveyImageQuery

surveyBp = Blueprint("surveys", __name__, url_prefix="/api/v1/surveys")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@surveyBp.get("/<int:survey_id>")
@surveyBp.get("/<uuid:survey_id>")
@login_required
@permission_required("access")
def get_by_id(survey_id: int | UUID):
    """
    Request a survey object from the database using its integer PK or UUID.
    ---
    parameters:
      - name: survey_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the survey (integer ID or UUID).
    responses:
      200:
        description: The requested survey was found.
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this survey.
      404:
        description: No survey record found for the provided ID.
      500:
        description: Database error.
    """
    return base.get(Survey, survey_id).serialize()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@surveyBp.get("/<int:survey_id>/annotations")
@surveyBp.get("/<uuid:survey_id>/annotations")
@login_required
@permission_required("access")
def get_annotations(survey_id: int | UUID):
    """
    Retrieve all annotations associated with a specific survey.
    ---
    parameters:
      - name: survey_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the survey (integer ID or UUID).
    responses:
      200:
        description: List of annotations (returns empty list if none exist).
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this survey.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    annotations = base.get_children(Annotation, Survey, survey_id)

    return [annotation.serialize() for annotation in annotations], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@surveyBp.get("/<int:survey_id>/herd-units")
@surveyBp.get("/<uuid:survey_id>/herd-units")
@login_required
@permission_required("access")
def get_herd_units(survey_id: int | UUID):
    """
    Retrieve all herd units associated with a specific survey.
    ---
    parameters:
      - name: survey_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the survey (integer ID or UUID).
    responses:
      200:
        description: List of herd units (returns empty list if none exist).
      400:
        description: Invalid ID format provided.
      401:
        description: User not authorized to access this survey.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    herd_units = base.get_children(HerdUnit, Survey, survey_id)

    return [herd_unit.serialize() for herd_unit in herd_units], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# TODO update get_children method to use pagination and get this to use get_children
@surveyBp.get("/<string:survey_id>/images")
@login_required
@permission_required("access")
@validate()
def get_images(query: SurveyImageQuery, survey_id: str):
    """
    Retrieve paginated images belonging to a specific survey.
    ---
    parameters:
      - name: survey_id
        in: path
        required: true
        type: string
        format: uuid
        description: UUID of the survey.
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number for pagination.
      - name: per_page
        in: query
        type: integer
        default: 20
        description: Number of images per page.
    responses:
      200:
        description: Paginated image collection with total count.
      400:
        description: Invalid UUID or query parameters.
      401:
        description: User not authorized to access this survey.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    offset = (query.page - 1) * query.per_page

    images, total_images = base.get_survey_images(
        UUID(survey_id), query.per_page, offset
    )

    return {
        "images": [image.serialize() for image in images],
        "total": total_images,
        "page": query.page,
        "per_page": query.per_page,
    }, 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# TODO: Update to use pydantic query class
@surveyBp.get("/<int:survey_id>/annotated_images")
@surveyBp.get("/<uuid:survey_id>/annotated_images")
@login_required
@permission_required("access")
def get_annotated_images(survey_id: int | UUID):
    """
    Retrieve annotated images within a survey, optionally filtered by label, herd unit, and date range.
    ---
    parameters:
      - name: survey_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the survey.
      - name: label
        in: query
        type: array
        items:
          type: integer
        description: Label IDs to filter by.
      - name: herd_unit
        in: query
        type: array
        items:
          type: integer
        description: Herd unit IDs to filter by.
      - name: date_range
        in: query
        type: array
        items:
          type: string
        description: Date range tuple in '%m/%d/%Y %H:%M:%S' format.
    responses:
      200:
        description: Annotated image records matching criteria.
      400:
        description: Invalid query parameters or ID format.
      401:
        description: User not authorized to access this survey.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    date_range = request.args.get("date_range", None)
    surveys = [base.get(Survey, survey_id).survey_id]
    labels = request.args.getlist("label", type=int)
    herd_units = request.args.getlist("herd_unit", type=int)
    format_pattern = "%m/%d/%Y %H:%M:%S"
    if date_range is not None:
        date_range = (
            datetime.strptime(date_range[0], format_pattern),
            datetime.strptime(date_range[1], format_pattern),
        )

    data = base.get_survey_annotated_images(labels, date_range, surveys, herd_units)

    return data, 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@surveyBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateSurveyReq):
    """
    Create a new survey object.
    ---
    parameters:
      - name: body
        in: body
        required: true
        type: CreateSurveyReq
        description: Survey creation payload containing name, survey_date, project_id, and herd_unit_ids.
    responses:
      201:
        description: Survey created successfully.
      400:
        description: Validation error or invalid payload.
      401:
        description: User not authorized to create surveys.
      409:
        description: Conflict or constraint violation.
      500:
        description: Database error.
    """
    return base.insert(Survey, body).serialize(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# PUT

# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@surveyBp.patch("/<int:survey_id>")
@surveyBp.patch("/<uuid:survey_id>")
@login_required
@permission_required("access")
@validate()
def update(body: UpdateSurveyReq, survey_id: int | UUID):
    """
    Update survey metadata by its integer ID or UUID.
    ---
    parameters:
      - name: survey_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the survey to update.
      - name: body
        in: body
        required: true
        type: UpdateSurveyReq
        description: Survey update payload with revised name, date, or additional info.
    responses:
      200:
        description: Survey updated successfully.
      400:
        description: Validation error or invalid ID format.
      401:
        description: User not authorized to update this survey.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    return base.update(Survey, survey_id, body).serialize(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# Delete


@surveyBp.delete("/<int:survey_id>")
@surveyBp.delete("/<uuid:survey_id>")
@login_required
@permission_required("access")
def delete_survey(survey_id: int | UUID):
    """
    Delete a survey by its integer ID or UUID.
    ---
    parameters:
      - name: survey_id
        in: path
        required: true
        schema:
          oneOf:
            - type: integer
              example: 1
            - type: string
              format: uuid
              example: "123e4567-e89b-12d3-a456-426614174000"
        description: Primary key of the survey to delete.
    responses:
      204:
        description: Survey deleted successfully.
      400:
        description: Invalid ID format.
      401:
        description: User not authorized to delete this survey.
      404:
        description: Survey not found.
      500:
        description: Database error.
    """
    base.delete(Survey, survey_id)

    return "", 204
