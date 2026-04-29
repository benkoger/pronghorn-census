# Endpoints for managing herd units in the API 
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from flask import Blueprint, abort
from flask_login import current_user, login_required
from database.object_models.user_management import User
from flask_pydantic import validate
from psycopg.errors import DatabaseError
from typing import cast

from app.extensions import base
from database import ObjectNotFound
from database.object_models.project_management import CreateHerdUnitReq

herdunitBp = Blueprint('herd_units', __name__, url_prefix='/api/v1/herd-units')

#---------------------------------------------------------------------------------------------------------------------------#
# GET 

@herdunitBp.get('/all')
@login_required
def get_all():
	'''

	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@herdunitBp.get('/<string:herd_unit_id>')
@login_required
def get_by_id(herd_unit_id: str):
	'''

	'''
	herd_unit = base.get_herd_unit(UUID(herd_unit_id), cast(User, current_user))

	if herd_unit is None:
		abort(404, f'Herd Unit with ID {herd_unit_id} was not found!')
		
	else:
		return herd_unit.to_dict()


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@herdunitBp.get('/<string:herd_unit_id>/surveys')
@login_required
def get_surveys(herd_unit_id: str):
	'''
	Retrieve all surveys associated with a herd unit.
	---
	parameters:
		- name: survye_id
		in: path
		type: string
		required: true
	responses:
		200:
			description: List of surveys.
		400:
			description: Invalid UUID format.
		404:
			description: No surveys found.
		500:
			description: Database error.
	'''
	try:
		surveys = base.get_herd_unit_surveys(UUID(herd_unit_id), cast(User, current_user))

	except ValueError as e:
		abort(400, str(e))
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)

	return [survey.to_dict() for survey in surveys], 200

#---------------------------------------------------------------------------------------------------------------------------#
# POST

@herdunitBp.post('')
@login_required
@validate()
def create(body: CreateHerdUnitReq):
	'''

	'''
	try:
		herd_unit = base.create_herd_unit(body, cast(User, current_user))
	except Exception as e:
		print(e)
		abort(500)

	return herd_unit.to_dict(), 201
