# Endpoints for managing images in the API 
# Author: Michael B. Lance
# Created: February 3, 2026
# Updated: February 11, 2026

#---------------------------------------------------------------------------------------------------------------------------#

from flask import Blueprint,  abort, request, current_app
from psycopg.errors import UniqueViolation
from .image_validators import *																																																																							
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
	except (UniqueViolation, Exception) as e:
		if type(e) is UniqueViolation:
			abort(409, 'Image already exists')
		else:
			abort(500)

	return image.serialize(), 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.post('/presigned-get-url')
@login_required
def create_presigned_get(body: CreatePresignedPut):
	'''
	'''
	data = body.model_dump()
	image = base.get_image(UUID(data['image_id']))

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

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.post('/presigned-put-url')
@validate()
@login_required
def create_presigned_post():
	'''
	Generates a pre-signed URL for a single file chunk. 
	This is the core endpoint for offloading data transfer. 
	The client sends a PUT request to this temporary URL with the chunk data.
	'''
	data = request.get_json()
	image_id = UUID(data['image_id']) if isinstance(data['image_id'], str) else data['image_id']
	image = base._get_image(image_id)

	try: 
		response = s3.generate_presigned_url(
		ClientMethod='upload_part', 
		Params = {
			'Bucket': current_app.config['BUCKET_NAME'],
			'Key': image.img_key, 
			'UploadId': data['upload_id'],
			'PartNumber': data['part_number'],
			'ContentLength': data['chunk_size'],
			'ContentMD5' : data['chunk_md5'],
		},
		ExpiresIn=3600,
		)
	except Exception as e:
		abort(500)
	return response, 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.post('/create-multipart-upload')
@login_required
def create_multipart_upload():
	'''
	Initiates a new multipart upload. The client calls this for each file 
	to be uploaded. the app responds with a unique UploadId, which is required 
	for all subsequent chunk uploads for that file.
	'''

	data = request.get_json()
	try: 
		response = s3.create_multipart_upload(
			Bucket = current_app.config['BUCKET_NAME'],
			Key = data['image_key'],
			ContentType = 'image/jpeg',
		)
	except Exception:
		abort(500)
	
	return response['UploadId'], 201

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