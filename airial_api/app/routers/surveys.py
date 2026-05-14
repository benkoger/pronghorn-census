# Endpoints for managing images in the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from flask import Blueprint, abort, request, current_app
from psycopg import DatabaseError
from app.decorators import permission_required
from database.errors import AuthenticationFailure, AuthorizationFailure, ObjectNotFound
from database.object_models.project_management import CreateSurveyReq, UpdateSurveyReq
from app.extensions import base
from datetime import datetime
from flask_pydantic import validate
from flask_login import (
    login_required,
)
from uuid import UUID

from database.object_models.project_management.surveys import SurveyImageQuery

surveyBp = Blueprint("surveys", __name__, url_prefix="/api/v1/surveys")

# ---------------------------------------------------------------------------------------------------------------------------
# GET


@surveyBp.get("/<string:survey_id>")
@login_required
@permission_required("access")
def get_by_id(survey_id: str):
    """ """
    try:
        survey = base.get_survey(UUID(survey_id))
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except AuthenticationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return survey.to_dict(), 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@surveyBp.get("/<string:survey_id>/annotations")
@login_required
@permission_required("access")
def get_annotations(survey_id: str):
    """ """
    try:
        annotations = base.get_survey_annotations(UUID(survey_id))
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return [annotation.to_dict() for annotation in annotations], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@surveyBp.get("/<string:survey_id>/herd-units")
@login_required
@permission_required("access")
def get_herd_units(survey_id: str):
    """ """
    try:
        herd_units = base.get_survey_herd_units(UUID(survey_id))
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return [herd_unit.to_dict() for herd_unit in herd_units], 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@surveyBp.get("/<string:survey_id>/images")
@login_required
@permission_required("access")
@validate()
def get_images(query: SurveyImageQuery, survey_id: str):
    """ """
    offset = (query.page - 1) * query.per_page
    try:
        images, total_images = base.get_survey_images(
            UUID(survey_id), query.per_page, offset
        )
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return {
        "images": [image.to_dict() for image in images],
        "total": total_images,
        "page": query.page,
        "per_page": query.per_page,
    }, 200


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# TODO: Update to use pydantic query class
@surveyBp.get("/<string:survey_id>/annotated_images")
@login_required
@permission_required("access")
def get_annotated_images(survey_id: str):
    """ """
    date_range = request.args.get("date_range", None)
    surveys = [base.get_survey(UUID(survey_id)).survey_id]
    labels = request.args.getlist("label", type=int)
    herd_units = request.args.getlist("herd_unit", type=int)
    format_pattern = "%m/%d/%Y %H:%M:%S"
    if date_range is not None:
        date_range = (
            datetime.strptime(date_range[0], format_pattern),
            datetime.strptime(date_range[1], format_pattern),
        )

    try:
        data = base.get_survey_annotated_images(labels, date_range, surveys, herd_units)
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return data, 200


# ---------------------------------------------------------------------------------------------------------------------------
# POST


@surveyBp.post("")
@login_required
@permission_required("access")
@validate()
def create(body: CreateSurveyReq):
    """ """
    try:
        survey = base.create_survey(body)
    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return survey.to_dict(), 201


# ---------------------------------------------------------------------------------------------------------------------------
# PUT

# ---------------------------------------------------------------------------------------------------------------------------
# PATCH


@surveyBp.patch("/<string:survey_id>")
@login_required
@permission_required("access")
@validate()
def update(body: UpdateSurveyReq, survey_id: str):
    """ """
    try:
        survey = base.update_survey(UUID(survey_id), body.model_dump())
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return survey.to_dict(), 200


# ---------------------------------------------------------------------------------------------------------------------------
# Delete


@surveyBp.delete("/<string:survey_id>")
@login_required
@permission_required("access")
def delete_survey(survey_id: str):
    """ """

    try:
        base.delete_survey(UUID(survey_id))
    except ObjectNotFound as e:
        current_app.logger.exception(e)
        abort(404, str(e))
    except AuthorizationFailure as e:
        current_app.logger.exception(e)
        abort(401, str(e))
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return "", 204
