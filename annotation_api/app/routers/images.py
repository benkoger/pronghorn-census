# Endpoints for managing images in the API 
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from cropgenerator import create_subcrop
from botocore.exceptions import ClientError
from flask import Blueprint, abort, current_app, request, Response
import cv2
from flask_login import current_user, login_required
from flask_pydantic import validate
from psycopg.errors import DatabaseError, UniqueViolation

from app.extensions import base, s3, cache
from database import ObjectNotFound
from database.errors import AuthorizationFailure
from database.view_models import (
		CreateImage,
		CreatePresignedPut,
		UpdateImage,
		CreatePredictionCrop,
        PredictionQuery
		)

imageBp = Blueprint('images', __name__, url_prefix='/api/v1/images')

#---------------------------------------------------------------------------------------------------------------------------#
# GET

@imageBp.get('/<string:image_id>')
@login_required
def get_by_id(image_id: str):
	'''
	Request an image object from the database using its UUID.
	---
	parameters:
	  - name: image_id
		in: path
		type: string
		required: true
	responses:
	  200:
		description: The requested image was found.
	  400:
		description: Invalid UUID format provided.
	  404:
		description: No image record found for the provided ID.
	'''
	try:
		image = base.get_image(UUID(image_id))
	except ValueError as e:
		abort(400, str(e))
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)

	return image.to_dict(), 200


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.get('/prediction_crops/<string:prediction_id>')
def get_prediction_crop(prediction_id: str): 
	'''

	'''
	crop = cache.get(prediction_id)
	if crop is None:
		abort(404, f'Prediction crop: {prediction_id} was not found')

	_, encoded_image= cv2.imencode('.webp', crop)
	return Response(encoded_image.tobytes(), mimetype='image/webp'), 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.get('/<string:image_id>/crops')
@login_required
def get_crops(image_id: str):
	'''
	Retrieve crops for a specific image
	---
	responses:
	  200:
		description: List of crops.
	  404:
		description: No crops found.
	  500:
		description: Database error.
	'''
	try:
		crops = base.get_image_crops(UUID(image_id))
	except ValueError as e:
		abort(400, str(e))
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception):
		abort(500)

	return [crop.to_dict() for crop in crops], 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.get('/<string:image_id>/predictions')
@login_required
def get_predictions(image_id: str):
	'''
	Retrieve all predictions associated with an image.
	---
	parameters:
		- name: image_id
		in: path
		type: string
		required: true
	responses:
		200:
			description: List of predictions.
		400:
			description: Invalid UUID format.
		404:
			description: No predictions found.
		500:
			description: Database error.
	'''
	try:
		predictions = base.get_image_predictions(UUID(image_id))
	except ValueError as e:
		abort(400, str(e))
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception):
		abort(500)

	return [pred.to_dict() for pred in predictions], 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.get('/<string:image_id>/annotations')
@login_required
def get_annotations(image_id: str):
	'''
	Retrieve all annotations associated with an image.
	---
	parameters:
		- name: image_id
		  in: path
		  type: string
		  required: true
	
	'''
	try:
		annotations = base.get_image_annotations(UUID(image_id))
		if not annotations:
			abort(404, 'No annotations found')
	except ValueError as e:
		abort(400, str(e))
	except (DatabaseError, Exception):
		abort(500)
	
	return [annot.to_dict() for annot in annotations], 200

#---------------------------------------------------------------------------------------------------------------------------#
#POST

@imageBp.post('')
@validate()
@login_required
def create(body: CreateImage):
	'''
	Create a new image record.
	---
	responses:
		201:
			description: Created successfully.
		409:
			description: Image already exists (Unique Violation).
		500:
			description: Database error.
	'''
	try:
		image = base.create_image(body.model_dump())
	except UniqueViolation:
		abort(409, 'Image already exists')
	except (DatabaseError, Exception):
		abort(500)

	return image.to_dict(), 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.post('/presigned-get-url')
@login_required
def create_presigned_get():
	'''
	Generate a presigned GET URL for an image.
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
		image = base.get_image(UUID(data['image_id']))

		if not image:
			abort(404, 'Image not found')

		response = s3.generate_presigned_url(
			'get_object',
			Params = {
				'Bucket': current_app.config['BUCKET_NAME'],
				'Key': image.img_key
			},
			ExpiresIn = data['expires_in']
		)
	except ValueError as e:
		abort(400, str(e))
	except ClientError as e:
		status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 500)
		abort(status, e.response.get('Error', {}).get('Message'))
	except (DatabaseError, Exception):
		abort(500)

	return response, 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.post('/presigned-put-url')
# @roles_required('admin')
@validate()
@login_required
def create_chunk_presigned_put(body: CreatePresignedPut):
	'''
	Generates a pre-signed URL for a single file chunk (UploadPart).
	---
	responses:
		201:
			description: URL generated.
		400:
			description: Missing data or invalid UUID.
		404:
			description: Image not found.
		500:
			description: Storage/Database error.
	'''
	data = body.model_dump()
	try: 
		image_id = UUID(data['image_id']) if isinstance(data['image_id'], str) else data['image_id']
		image = base._get_image(image_id)
		
		if image is None:
			abort(404, 'Image not found')

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
	except (ValueError, KeyError):
		abort(400)
	except ClientError as e:
		status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 500)
		abort(status)
	except (DatabaseError, Exception):
		abort(500)
	
	return response, 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.post('/create-multipart-upload')
@login_required
def create_multipart_upload():
	'''
	Initiates a new multipart upload.
	---
	responses:
		201:
			description: Multipart upload started.
		500:
			description: system error.
	'''
	data = request.get_json()
	try: 
		response = s3.create_multipart_upload(
			Bucket = current_app.config['BUCKET_NAME'],
			Key = data['image_key'],
			ContentType = 'image/jpeg',
		)
	except ClientError as e:
		status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 500)
		abort(status)
	except Exception:
		abort(500)
	
	return response['UploadId'], 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.post('/complete-multipart-upload')
@login_required
def complete_upload():
	'''
	Completes a new multipart upload.
	---
	responses:
		201:
			description: Multipart upload finished.
		500:
			description: S3 or system error.
	'''
	data = request.get_json()
	try:
		response = s3.complete_multipart_upload(
			Bucket = current_app.config['BUCKET_NAME'],
			Key = data['image_key'],
			MultipartUpload={
				'Parts': data['parts']
			},
			UploadId = data['upload_id'],
		)
	except ClientError as e:
		status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 500)
		abort(status)
	except Exception:
		abort(500)

	return response, 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.post('/abort-multipart-upload')
@login_required 
def abort_upload():
	'''
	Aborts a multipart upload.
	---
	responses:
		201:
			description: Multipart upload started.
		500:
			description: S3 or system error.
	'''
	data = request.get_json()
	try:
		response = s3.abort_multipart_upload(
			Bucket = current_app.config['BUCKET_NAME'],
			Key = data['image_key'],
			UploadId = data['upload_id'],
		)
	except ClientError as e:
		status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 500)
		abort(status)
	except Exception:
		abort(500)

	return response, 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.post('/prediction_crops')
@login_required
@validate()
def get_prediciton(body: CreatePredictionCrop):
	'''

	'''
	try:
		image = base.get_image(body.image_id)
		predictions = base.get_predictions(PredictionQuery(prediction_id=body.prediction_id))
		image_data = cache.get(image.uuid)
		if not image_data:
			image_data = s3.get_object(Bucket=current_app.config['BUCKET_NAME'],Key=image.img_key)['Body'].read()
			cache.set(image.uuid, image_data, 500)

		print('here')
		image.set_image(image_data)
		pred_crops = create_subcrop(image, predictions)

		[cache.set(crop.uuid, crop.get_image(), 3600) for crop in pred_crops]


	except ObjectNotFound as e:
		abort(404, str(e))
	except AuthorizationFailure as e:
		abort(401, str(e))
	except (DatabaseError, Exception) as e:
		print(f'error: {e}')
		abort(500)

	return [crop.to_dict() for crop in pred_crops]

#---------------------------------------------------------------------------------------------------------------------------#
#PUT

#---------------------------------------------------------------------------------------------------------------------------#
#PATCH

@imageBp.patch('/<string:image_id>')
@validate()
@login_required
def update(body: UpdateImage, image_id: str):
	'''
	Update image record metadata.
	---
	parameters:
		- name: image_id
		in: path
		type: string
		required: true
	responses:
		200:
			description: Record updated.
		400:
			description: Invalid UUID.
		404:
			description: Not found.
		500:
			description: Database error.
	'''
	try: 
		image = base.update_image(UUID(image_id), body.model_dump())
	except ValueError as e:
		abort(400, str(e))
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception):
		abort(500)

	return image.to_dict(), 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.patch('/close-user-images')
@login_required
def close_user_images():
	'''

	'''
	try:
		base.close_user_images(current_user.user_id)
	except ValueError as e:
		abort(400, str(e))
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception):
		abort(500)
	
	return '', 204

#---------------------------------------------------------------------------------------------------------------------------#
#DELETE

@imageBp.delete('/<string:image_id>')
@login_required
def delete_image(image_id: str):
	'''
	
	'''
	try:
		image = base.get_image(UUID(image_id))
		if not image:
			abort(404, 'Image not found')

		s3.delete_object(
			Bucket=current_app.config['BUCKET_NAME'], 
			Key=image.img_key
		)

		base.delete_image(UUID(image_id))
	except ValueError as e:
		abort(400, str(e))
	except ClientError as e:
		status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 500)
		abort(status, e.response.get('Error', {}).get('Message'))
	except (DatabaseError, Exception):
		abort(500)

	return '', 204
