# Endpoints for crop verification in the API
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from botocore.exceptions import ClientError
from flask import Blueprint, abort
from flask_login import login_required, current_user
from flask_pydantic import validate
from psycopg.errors import DatabaseError, UniqueViolation

from app.extensions import base
from database import ObjectNotFound, User

from typing import cast

from .cropverifier_validators import *

verifierBp = Blueprint('verifier', __name__, url_prefix='/api/v1/verifier')

#---------------------------------------------------------------------------------------------------------------------------#
# GET 

@verifierBp.get('/reviewed-area')
@login_required
@validate()
def get(query: RAQuery):
	'''
	Retrieve a reviewed area
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
		params = query.model_dump()
		params['num'] = 1
		reviewed_areas = base.get_crop_to_review(params, cast(User, current_user))
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception) as e:
		print(e)
		abort(404, str(e))

	print(reviewed_areas)

	return reviewed_areas.serialize(), 200