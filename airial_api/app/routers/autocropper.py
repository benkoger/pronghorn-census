# Endpoints for the autocropper utility 
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from crop_generator import auto_crop
from flask import Blueprint, abort, current_app
from flask_login import login_required, current_user
from flask_pydantic import validate
from psycopg.errors import DatabaseError
from typing import cast

from app.extensions import base, s3, cache
from database import ObjectNotFound

from database.object_models.user_management import User
from database.object_models.project_management import LabelQuery
from database.object_models import (
	AutoCropperBatchQuery,
	AutoCropReq,
)

from database.object_models.core import (
		PredictionQuery,
		
		ImportReviewedAreaReq
		)

cropBp = Blueprint('autocropper', __name__, url_prefix='/api/v1/autocropper')

#---------------------------------------------------------------------------------------------------------------------------#
# GET 

@cropBp.get('/batch')
@login_required
@validate()
def fetch_batch(query: AutoCropperBatchQuery):
	'''

	'''
	try: 
		batch = base.get_auto_crop_batch(query, cast(User, current_user))
	except ObjectNotFound as e:
		abort(404, str(e))
	except (Exception, DatabaseError) as e:
		print(f'error: {e}')
		abort(500)

	return batch, 200

#---------------------------------------------------------------------------------------------------------------------------#
# POST

@cropBp.post('')
@login_required 
@validate()
def auto_crop_image(body: AutoCropReq):
	'''

	'''
	try:
		image = base.get_image(body.image_id, cast(User, current_user))
		predictions = base.get_predictions(
				PredictionQuery(prediction_id=body.prediction_id),
				cast(User, current_user)
				)

		labels = base.get_labels(LabelQuery(label_id=body.label_id), cast(User, current_user))

		image_data = cache.get(image.uuid)

		if not image_data: 
			image_data = s3.get_object(Bucket=current_app.config['BUCKET_NAME'],Key=image.img_key)['Body'].read()
			cache.set(image.uuid, image_data, 500)

		image.set_image(image_data)

		ra_and_annotations = auto_crop(image, predictions, )

	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)
