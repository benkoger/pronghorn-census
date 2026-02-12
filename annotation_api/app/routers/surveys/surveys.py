# Endpoints for managing images in the API 
# Author: Michael B. Lance
# Created: February 11, 2026
# Updated: February 12, 2026

#---------------------------------------------------------------------------------------------------------------------------#

from flask import Blueprint,  abort, request, current_app
from .survey_validators import CreateSurvey, UpdateSurvey
from app.extensions import base, s3 
from botocore.exceptions import ClientError
from flask_pydantic import validate
from flask_login import (
	login_required,
) 
from uuid import UUID

surveyBp = Blueprint('surveys', __name__, url_prefix='/api/v1/surveys')

#TODO: These endpoints require propper organizational and project checking

#---------------------------------------------------------------------------------------------------------------------------#
# GET

@surveyBp.get('all')
@login_required
def get_all():
    '''
    
    '''
    return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@surveyBp.get('/<string:survey_id>')
@login_required
def get_by_id(survey_id: str):
    '''
    '''
    survey = base.get_survey(UUID(survey_id))

    if survey is None:
        abort(404, f'survey with ID{survey_id} was not found')
    else:
        return survey.serialize()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@surveyBp.get('/<string:survey_id>/annotations')
@login_required
def get_survey_annotations(survey_id: str):
    '''
    '''
    annotations = base.get_survey_annotations(UUID(survey_id))

    if len(annotations) == 0:
        abort(404, 'no annotaitons found')
    
    return [annotation.serialize() for annotation in annotations], 200

#---------------------------------------------------------------------------------------------------------------------------#
# POST

@surveyBp.post('')
@validate()
@login_required
def create(body: CreateSurvey):
    '''
    
    '''
    try: 
        survey = base.create_survey(body.model_dump())
    except Exception as e: 
        abort(500)

    return survey.serialize(), 201

#---------------------------------------------------------------------------------------------------------------------------#
# PUT

#---------------------------------------------------------------------------------------------------------------------------#
# PATCH

@surveyBp.patch('/<string:survey_id>')
@validate()
@login_required
def update(body: UpdateSurvey, survey_id: str):
    '''
    '''
    data = request.get_json()
    try:
        survey = base.update_survey(UUID(survey_id), body.model_dump())
    except Exception as e:
        abort(500)

    return survey.serialize(), 200

#---------------------------------------------------------------------------------------------------------------------------#
# Delete

@surveyBp.delete('/<string:survey_id>')
@login_required
def delete_survey(survey_id: str):
    '''
    '''

    try:
        res = base.delete_survey(UUID(survey_id))
    except:
        abort(500)
    if res:
        return '', 204
    else:
        abort(404, 'could not find survey to delete')
