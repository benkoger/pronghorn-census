# Endpoints for managing images in the API 
# Author: Michael B. Lance
# Created: February 11, 2026
# Updated: February 12, 2026

#---------------------------------------------------------------------------------------------------------------------------#

from flask import Blueprint,  abort, request, current_app
from psycopg import DatabaseError
from database.view_models.surveys import *
from app.extensions import base
from datetime import date, datetime
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
		return survey.to_dict()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@surveyBp.get('/<string:survey_id>/annotations')
@login_required
def get_annotations(survey_id: str):
	'''
	'''
	annotations = base.get_survey_annotations(UUID(survey_id))

	if len(annotations) == 0:
		abort(404, f'no annotaitons found for survey {survey_id}')
	
	return [annotation.to_dict() for annotation in annotations], 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@surveyBp.get('/<string:survey_id>/herd-units')
@login_required 
def get_herd_units(survey_id: str):
	'''
	'''
	try:
		herd_units = base.get_survey_herd_units(UUID(survey_id))
	except( DatabaseError, Exception):
		abort(500)

	return [herd_unit.to_dict() for herd_unit in herd_units], 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@surveyBp.get('/<string:survey_id>/images')
@login_required
def get_images(survey_id: str):
	'''
	'''
	try:
		images = base.get_survey_images(UUID(survey_id))
	except (DatabaseError, Exception):
		abort(500)

	return [image.to_dict() for image in images], 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@surveyBp.get('/<string:survey_id>/annotated_images')
@login_required
def get_annotated_images(survey_id: str):
	'''
	'''
	date_range = request.args.get('date_range', None)
	surveys = [base.get_survey(UUID(survey_id)).survey_id]
	labels = request.args.getlist('label', type=int)
	herd_units = request.args.getlist('herd_unit', type=int)
	format_pattern = "%m/%d/%Y %H:%M:%S"
	if date_range is not None:
		date_range = (
			datetime.strptime(date_range[0], format_pattern), 
			datetime.strptime(date_range[1], format_pattern)
		)

	try: 
		data = base.get_survey_annotated_images(
			labels,
			date_range,
			surveys,
			herd_units
		)
	except Exception as e:
		abort(404, 'Couldnt find anything matching your query parameters')
	
	return data, 200   

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

	return survey.to_dict(), 201

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

	return survey.to_dict(), 200

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
