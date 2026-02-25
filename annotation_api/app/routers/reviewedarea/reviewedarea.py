# Endpoints for managing reviewed areas in the API 
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from botocore.exceptions import ClientError
from flask import Blueprint, abort, current_app, request
from flask_login import login_required
from flask_pydantic import validate
from psycopg.errors import DatabaseError, UniqueViolation

from app.extensions import base, s3
from database import ObjectNotFound

from .reviewedarea_validators import *

raBp = Blueprint('reviewed-area', __name__, url_prefix='/api/v1/reviewed-area')

#---------------------------------------------------------------------------------------------------------------------------#
# GET

@raBp.get('')
@login_required
@validate()
def get(query: RAQuery):
	'''
	Retrieve all reviewed areas 
	---
	paramaters:
	  - in: query
		name: herd_unit_id
		type: number
	  - in: query
		name: survey_id
		type: number
	responses:
		200:
			description: List of reviewed areas.
		400:
			description: Invalid UUID format.
		404:
			description: No reviewed areas found.
		500:
			description: Database error.
	'''
	try:
		reviewed_areas = base.get_reviewed_areas(query.model_dump())
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception) as e:
		print(e)
		abort(404, str(e))

	print(reviewed_areas)

	return [ra.serialize() for ra in reviewed_areas]

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

