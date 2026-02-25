# Endpoints for crop verification in the API
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from botocore.exceptions import ClientError
from flask import Blueprint, abort, request
from flask_login import login_required, current_user
from flask_pydantic import validate
from psycopg.errors import DatabaseError, UniqueViolation

from app.extensions import base, s3
from database import ObjectNotFound

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
		reviewed_areas = base.get_crop_to_review(params, current_user.user_id)
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception) as e:
		print(e)
		abort(404, str(e))

	print(reviewed_areas)

	return reviewed_areas.serialize(), 200

#---------------------------------------------------------------------------------------------------------------------------#

@verifierBp.put('/submit')
@login_required
@validate()
def approve_annotations(body: ApproveAnnotations):
	'''
	
	'''
	data = body.model_dump()
	res_1 = False
	res_2 = False

	# loop over incoming annotation data
	for annot in data['annotations']:
		res_i = False
		# check if annotation in the database
		if base.get_annotation_exists(UUID(annot['uuid'])):
			
			# TODO: check if annotation still inersects prediction in threshold
			# update annotation
			res_i = base.update_annotation(
				annot['annotation_id'],
				label_id=annot['label_id'],
				box_tx=annot['dimensions']['top_left']['x'],
				box_ty=annot['dimensions']['top_left']['y'],
				box_bx=annot['dimensions']['bottom_right']['x'],
				box_by=annot['dimensions']['bottom_right']['y'],	
			)
		# else
		else:
			# create annotation
			res_i = base.create_annotation(
				label_id = annot['label_id'],
				image_id = annot['image_id'], 
				herd_unit_id = annot['herd_unit_id'],
				box_tx = annot['dimensions']['top_left']['x'],
				box_ty = annot['dimensions']['top_left']['y'],
				box_bx = annot['dimensions']['bottom_right']['x'],
				box_by = annot['dimensions']['bottom_right']['y'],
				user_id = current_user.user_id,
				uuid = annot['uuid']
			)

		if res_i == False:
			abort(500, 'failed to make or update annotations')

	# loop over deleted annotations
	# TODO: add method to delete multiple dicts in a single pass
	for annot in data['deleted_annotations']:
		base.delete_annotation(annot['annotation_id'])

	# set crop reviewed 
	res_1 = base.update_reviewed_area(data['reviewed_area_id'], reviewed_by_user_id = current_user.user_id)

	# set image closed
	res_2 = base.update_image(data['image_id'], {'opened_by_user_id':0})

	if res_1 == False or res_2 == False:
		abort(500, 'failed to set image crop reviewed and image closed')

	return '', 201