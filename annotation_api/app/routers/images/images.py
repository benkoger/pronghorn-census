# Endpoints for managing images in the API 
# Author: Michael B. Lance
# Created: February 3, 2026
# Updated: February 4, 2026

#---------------------------------------------------------------------------------------------------------------------------#

from flask import Blueprint,  abort, request, current_app
from .image_validators import CreateImage
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
def get_by_id(body: CreateImage, image_id: str):
	"""
    Test Endpoint
    ---
    responses:
      200:
        description: A valid response  # Must be indented under 200
      404:
        description: Not found
    """
	image = base.get_image(UUID(image_id))

	if image is not None:
		return image.serialize()
	else:
		abort(404, f'Image with ID {image_id} was not found!')
	
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

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
        print(e)
        abort(500)

    return image.serialize(), 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@imageBp.post('/presigned_url')
@login_required
def create_image_presigned_get():
    '''
    '''
    data = request.get_json()

    print(data['ra_key'])

    try:
        response = s3.generate_presigned_url(
            'get_object',
            Params = {
                'Bucket': current_app.config['BUCKET_NAME'],
                'Key': data['ra_key']
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

#---------------------------------------------------------------------------------------------------------------------------#
#DELETE