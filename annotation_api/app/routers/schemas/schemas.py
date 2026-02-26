# Endpoints for managing schemas in the API 
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from botocore.exceptions import ClientError
from flask import Blueprint, abort
from flask_login import login_required
from flask_pydantic import validate
from psycopg.errors import DatabaseError, UniqueViolation

from app.extensions import base
from database import ObjectNotFound

from .schema_validators import *

schemaBp = Blueprint('schemas', __name__, url_prefix='/api/v1/schemas')

#TODO: These endpoints require propper organizational and project checking

#---------------------------------------------------------------------------------------------------------------------------#
# GET

@schemaBp.get('/<string:schema_id>/labels')
@login_required
def get_crops(schema_id: str):
	'''
	Retrieve labels for a schema
	---
	responses:
	  200:
		description: List of labels.
	  404:
		description: No labels / schema found.
	  500:
		description: Database error.
	'''
	print(schema_id)
	try:
		labels = base.get_schema_labels(UUID(schema_id))
	except ValueError as e:
		abort(400, str(e))
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)

	return [label.to_dict() for label in labels], 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#