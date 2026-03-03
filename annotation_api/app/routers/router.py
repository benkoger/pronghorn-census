# Core router for the API
# Author: Michael B. Lance


#---------------------------------------------------------------------------------------------------------------------------#

from datetime import datetime
import io
from typing import cast
from uuid import UUID

from cropgenerator import auto_crop, create_subcrop
from cropgenerator.generatorobjects import Annotation, Prediction, ReviewedArea, User
import cv2
from flask import Blueprint, Response, abort, current_app, jsonify, request, session
from flask_login import current_user, login_required

from app.extensions import base, cache, login_manager, s3
from .herdunits import herdunitBp
from .images import imageBp
from .models import modelBp
from .projects import projectBp
from .schemas import schemaBp
from .surveys import surveyBp
from .cropverifier import verifierBp
from .reviewedarea import raBp
from .users import userBp

#---------------------------------------------------------------------------------------------------------------------------#

bp = Blueprint('app', __name__)

bp.register_blueprint(herdunitBp)
bp.register_blueprint(imageBp)
bp.register_blueprint(modelBp)
bp.register_blueprint(projectBp)
bp.register_blueprint(schemaBp)
bp.register_blueprint(surveyBp)
bp.register_blueprint(verifierBp)
bp.register_blueprint(raBp)
bp.register_blueprint(userBp)

#---------------------------------------------------------------------------------------------------------------------------#
# Project CRUD

@bp.route('/api/v1/projects/create', methods = ['POST'])
@login_required
def create_project():
	data = request.get_json()
	project = base.create_project(name = data['name'],)
	return project.to_dict(), 201 

@bp.route('/api/v1/projects/request/<string:project_id>', methods=['GET'])
@login_required
def get_project(project_id: str):
	project = base.get_project(project_id = UUID(project_id))
	if not project:
		abort(404, 'project not found')
	return project.to_dict()
	
@bp.route('/api/v1/request/projects/all')
@login_required
def get_all_projects():
	projects = base.get_user_projects(cast(User, current_user))
	to_dictd_projects = [project.to_dict() for project in projects] 
	return jsonify(to_dictd_projects), 201

#---------------------------------------------------------------------------------------------------------------------------#
# Prediction Crud

@bp.route('/api/v1/create/prediction', methods=['POST'])
def create_prediction():
	'''
	
	'''
	data = request.get_json()
	prediction = base.create_prediction(
		UUID(data['image_id']),
		UUID(data['model_id']),
		data['label'],
		data['score'],
		data['box_tx'],
		data['box_ty'],
		data['box_bx'],
		data['box_by'],
		data['returning']
	)
	if prediction is None:
		abort(500)
	return prediction.to_dict(), 201

#---------------------------------------------------------------------------------------------------------------------------#
# Auto Cropping

@bp.route('/api/v1/create/auto-crop-batch', methods=['POST'])
@login_required
def create_auto_crop_batch():
	'''
	
	'''
	data = request.get_json()
	if 'pred_crop_data' in session: # Delete last batch's prediction crops
		for data in session['pred_crop_data']:
			cache.delete(data['uuid'])
		session.pop('pred_crop_data')
	try:
		img_batch = base.get_auto_crop_batch(
			UUID(data['survey_id']),
			UUID(data['herd_unit_id']),
			int(data['size']),
			data['labels'],
			float(data['score']),
			UUID(data['model_id']),
			cast(User, current_user))
	except TypeError as e:
		abort(404, 'Database returned nothing, perhaps your confidence score is too high.')
	except Exception:
		abort(500)
	return img_batch, 201

@bp.route('/api/v1/create/predictionCrops', methods=['POST'])
@login_required
def create_prediction_crops():
	'''
	
	'''
	data = request.get_json()
	image = base.get_image(UUID(data['image_id']))
	img_data = cache.get(image.uuid)

	if not img_data:
		img_key = f'images/survey/{data['survey_id']}/herd_unit/{data['herd_unit_id']}/image/{image.name}'
		img_data = s3.get_object(Bucket=current_app.config['BUCKET_NAME'], Key=img_key)['Body'].read()
		cache.set(image.uuid, img_data, 360) 

	image.set_image(img_data)
	pred_crops = create_subcrop(image, data['predictions'])
	to_dictd_pred_crops = [] 

	for crop in pred_crops: # Save crop image data into the session cache
		cache.set(crop.uuid,  crop.get_image(), 3600)
		to_dictd_pred_crops.append(crop.to_dict())
	
	json_pred_crop_data = jsonify(to_dictd_pred_crops)
	
	if 'pred_crop_data' not in session:
		session['pred_crop_data'] = []
	
	session['pred_crop_data'] + to_dictd_pred_crops #type: ignore
	return json_pred_crop_data, 201

@bp.route('/api/v1/request/image/<string:image_id>/pred_crop/<string:pred_crop_id>', methods=['GET'])
def get_pred_crop(image_id: str, pred_crop_id: str):
	'''
	
	'''
	crop = cache.get(pred_crop_id)
	if crop is None:
		abort(404, 'crop not found')

	_, encoded_img = cv2.imencode('.webp', crop)
	return Response(encoded_img.tobytes(), mimetype='image/webp'), 201

@bp.route('/api/v1/create/reviewed-area-and-annotations', methods=["PUT"])
@login_required
def create_reviewed_area_and_annotations():
	'''
	
	'''
	data = request.get_json()
	# Request image object from data in request
	image = base.get_image(UUID(data['image_uuid']))
	img_data = cache.get(image.uuid)

	if not img_data:
		img_key = f'images/survey/{data['survey_id']}/herd_unit/{data['herd_unit_id']}/image/{image.name}'
		img_data = s3.get_object(Bucket=current_app.config['BUCKET_NAME'], Key=img_key)['Body'].read()
		cache.set(image.uuid, img_data, 360) 
	image.set_image(img_data)

	# get label - id for schema
	label_ids = { lbl['label'] : lbl['label_id'] for lbl in data['labels'] }
	
	# (re)Construct prediction objects from data in request
	predictions = []

	for pred in data['predictions']:
		prediction = Prediction(
			pred_id = pred['pred_id'], 
			image_id = pred['image_id'],
			model_id = pred['model_id'],
			label = pred['label'],
			score = pred['score'],
			box_tx = pred['dimensions']['top_left'][0],
			box_ty = pred['dimensions']['top_left'][1],
			box_bx = pred['dimensions']['bottom_right'][0],
			box_by = pred['dimensions']['bottom_right'][1],
			created = datetime.fromisoformat(pred['created'].replace("Z", "+00:00")),
			uuid = pred['uuid'],
			reviewed_by_user_id = 0
		)
		predictions.append(prediction)

	# Create reviewed area(s) from auto_crop() function
	reviewed_areas = auto_crop(image=image, predictions=predictions, labels_ids=label_ids)

	#Create reviewed area and predictions objects
	res_1 = False # init result as false to calm pyright down
	for area_set in reviewed_areas: 
		reviewed_area: ReviewedArea = cast(ReviewedArea, area_set[0])
		annotations: Annotation = cast(Annotation, area_set[1] )
		ra_key = f'reviewed_areas/survey/{data['survey_id']}/herd_unit/{data['herd_unit_id']}/reviewed_area/{reviewed_area.name}'
		reviewed_area.ra_key = ra_key
		reviewed_area_id = base.insert_reviewed_areas(reviewed_area)
		annotation_ids = base.insert_annotations(annotations, cast(User, current_user))
		res_1 = base.add_reviewed_area_annotations(cast(int, reviewed_area_id), annotation_ids)
		
		try:
			img_bytes = reviewed_area.serve('.JPG')
		except Exception as e:
			print(e)
			abort(500, e)

		s3.put_object(
			Bucket=current_app.config['BUCKET_NAME'],
			Key=ra_key,
			Body=io.BytesIO(img_bytes),  #type: ignore
			ContentType='image/jpeg'
		)

	res_3 = base.update_image(image.image_id, {'opened_by_user_id': 0})

	return '', 201 if res_1 and res_3 else abort(500)

@bp.route('/api/v1/update/predictions/set-reviewed', methods=['POST'])
@login_required
def mark_predictions_reviewed():
	'''
	'''
	data = request.get_json()
	ids = [UUID(predId) for predId in data['prediction_ids']]
	res = base.set_predictions_reviewed(ids, cast(User, current_user).user_id)

	return '', 201 if res else abort(500)

@bp.route('/api/v1/get/reviewed-area/<string:reviewed_area_id>/annotations', methods=['GET'])
@login_required
def get_ra_annotations(reviewed_area_id: str):
	'''
	'''
	annotations = base.get_crop_annotations(UUID(reviewed_area_id))
	return [annot.to_dict() for annot in annotations], 201


