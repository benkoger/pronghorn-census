# Endpoints for managing herd units in the API 
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from flask import Blueprint,  abort, request
from app.extensions import base 
from flask_pydantic import validate
from .herdunit_validators import CreateHerdUnit
from datetime import date, datetime
from flask_login import (
	login_required,
) 
from typing import cast, List
from uuid import UUID

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
	herd_unit = base.get_herd_unit(UUID(herd_unit_id))

	if herd_unit is None:
		abort(404, f'Herd Unit with ID {herd_unit_id} was not found!')
		
	else:
		return herd_unit.serialize()


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

#---------------------------------------------------------------------------------------------------------------------------#
# POST

@herdunitBp.post('')
@login_required
@validate()
def create(body: CreateHerdUnit):
	'''

	'''
	try:
		herd_unit = base.create_herd_unit(body.model_dump())
	except Exception as e:
		print(e)
		abort(500)

	return herd_unit.serialize(), 201