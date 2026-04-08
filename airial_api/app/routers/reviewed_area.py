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
from database.object_models.core import RAQuery

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

	return [ra.to_dict() for ra in reviewed_areas]

#---------------------------------------------------------------------------------------------------------------------------#
# POST

@raBp.post('/presigned-get-url')
@login_required
def create_ra_presigned_get():
	'''
	Generate a presigned GET URL for a reviewed area.
	---
	responses:
		201:
			description: Presigned URL generated.
		400:
			description: Invalid ID format.
		404:
			description: Image record not found.
		500:
			description: Storage or database error.
	'''
	data = request.get_json()
	try:
		response = s3.generate_presigned_url(
			'get_object',
			Params={'Bucket': current_app.config['BUCKET_NAME'],
					'Key': data['ra_key']
			},
			ExpiresIn=3600,
		)
	except ValueError as e:
		abort(400, str(e))
	except ClientError as e:
		status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 500)
		abort(status, e.response.get('Error', {}).get('Message'))
	except (DatabaseError, Exception):
		abort(500)
		
	return response, 201