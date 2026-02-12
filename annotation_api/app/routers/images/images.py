# Endpoints for managing images in the API 
# Author: Michael B. Lance
# Created: February 3, 2026
# Updated: February 11, 2026

#---------------------------------------------------------------------------------------------------------------------------#

from flask import Blueprint,  abort, request, current_app
from .image_validators import CreateImage, UpdateImage
from app.extensions import base, s3 
from botocore.exceptions import ClientError
from flask_pydantic import validate
from flask_login import (
	login_required,
) 
from uuid import UUID

imageBp = Blueprint('images', __name__, url_prefix='/api/v1/images')

#TODO: These endpoints require propper organizational and project checking

#---------------------------------------------------------------------------------------------------------------------------#
# GET

@imageBp.get('/all')
@login_required
def get_all():
	'''

	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.get('/<string:image_id>')
@login_required
def get_by_id(image_id: str):
	'''
	Request an image object from the database using its UUID
	---
	parameters:
		- name: image_id
		in: path
		type: string
		required: true

	responses:
		200:
			description: The requested image was found
		404:
			description: Not found
	'''
	image = base.get_image(UUID(image_id))

	if image is None:
		abort(404, '')
	else:
		return image.serialize()


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.get('/<string:image_id>/crops')
@login_required
def get_crops(image_id: str):
	'''
	
	'''
	crops = base.get_image_crops(UUID(image_id))

	if len(crops) == 0:
		abort(404, 'No crops found')

	return [crop.serialize() for crop in crops], 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.get('/<string:image_id>/predictions')
@login_required
def get_predictions(image_id: str):
	'''

	'''
	predictions = base.get_image_predictions(UUID(image_id))

	if len(predictions) == 0:
		abort(404, 'No predictions found')

	return [pred.serialize() for pred in predictions], 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.get('/<string:image_id>/annotations')
@login_required
def get_annotations(image_id: str):
	'''
	'''
	annotations = base.get_image_annotations(UUID(image_id))

	if len(annotations) == 0:
		abort(404, 'No annotations found')
	
	return [annot.serialize() for annot in annotations], 200

#---------------------------------------------------------------------------------------------------------------------------#
#POST

@imageBp.post('')
@validate()
@login_required
def create(body: CreateImage):
	'''

	'''
	try:
		image = base.create_image(body.model_dump())
	except Exception as e:
		abort(500)

	return image.serialize(), 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.post('/<string:image_id>/presigned_url')
@login_required
def create_presigned_get(image_id: str):
	'''
	'''
	data = request.get_json()
	image = base.get_image(UUID(image_id))

	try:
		response = s3.generate_presigned_url(
			'get_object',
			Params = {
				'Bucket': current_app.config['BUCKET_NAME'],
				'Key': image.img_key
			},
			ExpiresIn = data['expires_in']
		)
	except ClientError as e:
		abort(500)
	return response, 201

#---------------------------------------------------------------------------------------------------------------------------#
#PUT

#---------------------------------------------------------------------------------------------------------------------------#
#PATCH

@imageBp.patch('/<string:image_id>')
@validate()
@login_required
def update(body: UpdateImage, image_id: str):
	'''

	'''
	try: 
		image = base.update_image(UUID(image_id), body.model_dump())
	except:
		abort(500)

	return image.serialize(), 200

#---------------------------------------------------------------------------------------------------------------------------#
#DELETE

@imageBp.delete('/<string:image_id>')
@login_required
def delete_image(image_id: str):
	'''
	
	'''
	try:
		res = base.delete_image(UUID(image_id))
	except:
		abort(500)
	if res:
		return '', 204
	else:
		abort(404, 'Could not find the image to delete')