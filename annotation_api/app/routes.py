# Attempt at RESTful CRUD app for crop generator and census server
# Based on https://https://www.digitalocean.com/community/tutorials/create-a-rest-app-using-flask-on-ubuntu 
# because I have never done this before
# Author: Michael B. Lance
# Created: April 7, 2025
# Updated: November 11, 2025

#---------------------------------------------------------------------------------------------------------------------------#

from datetime import datetime
import io
from uuid import UUID
import cv2
from flask import Blueprint, Response, abort, jsonify, request, session, current_app
from cropgenerator import auto_crop, create_subcrop
from cropgenerator.generatorobjects import Prediction, User, ReviewedArea, Annotation
from app.extensions import login_manager, cache, base 
from app import pathfinder
from database import Database
from typing import cast
from flask_login import (
	current_user,
	login_required,
	login_user,
	logout_user,
) 


bp = Blueprint('app', __name__)



#---------------------------------------------------------------------------------------------------------------------------#
# User session management

@login_manager.user_loader
def load_user(session_user_id):
	user = base.get_user(UUID(session_user_id))
	return user 

@login_manager.unauthorized_handler
def unathorizated_callback():
	abort(401, 'unathorized, are you logged in? Should you be accessing this?')

@bp.route('/api/v1/authenticate', methods=['POST'])
def authenticate():
	req_data = request.get_json()
	if not req_data or 'external-id' not in req_data:
		abort(400, 'malformed request')
	try:
		user = base.get_user(req_data['external-id'])
		print(user.username)
	except Exception as e:
		abort(401, str(e))
	else:
		login_user(user)
		if not user.last_login:
			user.last_login = base.login_user(user)
		else:
			base.login_user(user)
		return user.serialize(), 201

@bp.route('/api/v1/check_auth', methods=["GET"])
@login_required
def check_auth():
	return Response('true'), 201

@bp.route('/api/v1/users/getCurrentUser', methods = ['GET'])
@login_required
def getCurrentUser():
	try:
		user = base.get_user(UUID(current_user.id))
	except Exception:
		abort(500)
	return cast(User, user).serialize(), 201
@bp.route('/api/v1/deauthenticate', methods=["POST"])
@login_required
def logout():
	logout_user()
	return '', 200

#---------------------------------------------------------------------------------------------------------------------------#
# # Organization CRUD
# @bp.route('/app/v1/create/organization')
# @login_required
# def create_organization():
# 	pass

@bp.route('/api/v1/request/organizations/all')
@login_required
def get_user_organizations():
	organizations = base.get_user_organizations(cast(User, current_user))
	serialized_organizations = [organization.serialize() for organization in organizations] if organizations else None
	return jsonify(serialized_organizations), 201 

#---------------------------------------------------------------------------------------------------------------------------#
# Role CRUD

#---------------------------------------------------------------------------------------------------------------------------#
# Project CRUD

@bp.route('/api/v1/projects/create', methods = ['POST'])
@login_required
def create_project():
	data = request.get_json()
	project = base.create_project(name = data['name'],)
	return project.serialize(), 201 

@bp.route('/api/v1/projects/request/<string:project_id>', methods=['GET'])
@login_required
def get_project(project_id: str):
	project = base.get_project(project_id = UUID(project_id))
	if not project:
		abort(404, 'project not found')
	return project.serialize()
	
@bp.route('/api/v1/request/projects/all')
@login_required
def get_all_projects():
	projects = base.get_user_projects(cast(User, current_user))
	serialized_projects = [project.serialize() for project in projects] 
	return jsonify(serialized_projects), 201

# @bp.route('/app/v1/projects/update/<string:project_id>', methods = ['PUT'])
# @login_required
# def update_project(project_id: str):
# 	pass

#---------------------------------------------------------------------------------------------------------------------------#
# Schema CRUD

@bp.route('/api/v1/request/projects/<string:project_id>/schemas/all', methods=['GET'])
@login_required
def get_project_schemas(project_id: str):
	schemas = base.get_project_schemas(UUID(project_id))
	serialized_schemas = [schema.serialize() for schema in schemas] if schemas else None
	return jsonify(serialized_schemas), 201

#---------------------------------------------------------------------------------------------------------------------------#
# Label CRUD

# @bp.route('/app/v1/create/label')
# @login_required
# def create_label():
# 	pass

@bp.route('/api/v1/request/projects/<string:project_id>/schemas/<string:schema_id>/labels/all', methods=['GET'])
@login_required
def get_schema_labels(project_id: str, schema_id: str):
	labels = base.get_schema_labels(UUID(schema_id))
	serialized_labels = [label.serialize() for label in labels]
	return jsonify(serialized_labels), 201

#---------------------------------------------------------------------------------------------------------------------------#
# Herd Unit Crud

@bp.route('/api/v1/request/projects/<string:project_id>/herd_units/all', methods=['GET'])
@login_required
def get_project_herdunits(project_id: str):
	herd_units = base.get_project_herd_units(UUID(project_id))
	serialized_herd_units = [herd_unit.serialize() for herd_unit in herd_units]
	if serialized_herd_units is None:
		abort(404, 'No Herd Units Found')
	return jsonify(serialized_herd_units), 201

@bp.route('/api/v1/request/surveys/<string:survey_id>/herd_units/all', methods=['GET'])
@login_required
def get_survey_herdunits(survey_id: str):
	herd_units = base.get_cropping_herd_units(UUID(survey_id))
	serialized_herd_units = [herd_unit.serialize() for herd_unit in herd_units] 
	if serialized_herd_units is None:
		abort(404, 'No Herd Units Found')
	return jsonify(serialized_herd_units), 201

#---------------------------------------------------------------------------------------------------------------------------#
# Model Crud

@bp.route('/api/v1/create/model', methods=['POST'])
@login_required
def create_model():
	'''
	
	'''
	data = request.get_json()
	try:
		model = base.create_model(data['name'])
	except Exception:
		abort(500)
	return model.serialize(), 201
	
@bp.route('/api/v1/request/projects/<string:project_id>/models/all', methods=['GET'])
@login_required
def get_project_models(project_id: str):
	try:
		models = base.get_project_models(UUID(project_id))
	except Exception as e:
		abort(404, e)
	serialized_models = [model.serialize() for model in models]
	return jsonify(serialized_models), 201

@bp.route('/api/v1/request/surveys/<string:survey_id>/herd_units/<string:herd_unit_id>/schemas/<string:schema_id>/models/all', methods=['GET'])
@login_required
def get_cropper_models(survey_id: str, herd_unit_id: str, schema_id: str):
	models = base.get_cropping_models(UUID(survey_id), UUID(herd_unit_id), UUID(schema_id))
	serialized_models = [model.serialize() for model in models]
	if serialized_models is None:
		abort(404, 'No Models Found')
	return jsonify(serialized_models), 201

#---------------------------------------------------------------------------------------------------------------------------#
# Survey Crud

@bp.route('/api/v1/request/projects/<string:project_id>/surveys/all', methods=['GET'])
@login_required
def get_project_surveys(project_id: str):
	surveys = base.get_projects_surveys(UUID(project_id))
	serialized_surveys = [survey.serialize() for survey in surveys]
	if serialized_surveys is None:
		abort(404)
	return jsonify(serialized_surveys), 201

#---------------------------------------------------------------------------------------------------------------------------#
# Image Crud

@bp.route('/api/v1/create/image', methods=['POST'])
@login_required
def upload_image_to_db():
	'''
	'''
	data = request.get_json()
	image = base.create_image(data['name'], UUID(data['herd_unit_id']), UUID(data['survey_id']), data['img_key'], data['image_length'], data['image_width'])
	if image is None:
		abort(500)
	return image.serialize(), 201

# @bp.route('/app/v1/get/image', methods=['GET'])
# @login_required
# def getImage():
# 	'''
	
# 	'''
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
	return prediction.serialize(), 201


#---------------------------------------------------------------------------------------------------------------------------#
# Image and Prediction Mass Uploader

@bp.route('/api/v1/create/image/presigned-put-url', methods=['POST'])
@login_required
def get_presigned_url():
	'''
	Generates a pre-signed URL for a single file chunk. 
	This is the core endpoint for offloading data transfer. 
	The client sends a PUT request to this temporary URL with the chunk data.
	'''
	data = request.get_json()
	try: 
		response = pathfinder.generate_presigned_url(
		ClientMethod='upload_part', 
		Params = {
		'Bucket': current_app.config['BUCKET_NAME'],
		'Key': data['image_key'], 
		'UploadId': data['upload_id'],
		'PartNumber': data['part_number'],
		'ContentLength': data['chunk_size'],
		'ContentMD5' : data['chunk_md5'],
		},
		ExpiresIn=3600,
		)
	except Exception:
		abort(500)
	return jsonify(response), 201


@bp.route('/api/v1/upload/image/create_multipart_upload', methods=['POST'])
@login_required
def create_multipart_upload():
	'''
	Initiates a new multipart upload. The client calls this for each file 
	to be uploaded. the app responds with a unique UploadId, which is required 
	for all subsequent chunk uploads for that file.
	'''

	data = request.get_json()
	try: 
		response = pathfinder.create_multipart_upload(
			Bucket = current_app.config['BUCKET_NAME'],
			Key = data['image_key'],
			ContentType = 'image/jpeg',
		)
		upload_id = response['UploadId']
		return jsonify({'upload_id': upload_id}), 201
	except Exception:
		abort(500)

@bp.route('/api/v1/upload/image/complete', methods=['POST'])
@login_required
def complete_upload():
	'''
	Finalizes a multipart upload. After all chunks have been successfully 
	uploaded, the client calls this endpoint with the UploadId and a list 
	of all part details (PartNumber, ETag) to assemble the file on the 
	storage backend.
	'''
	data = request.get_json()
	try:
		response = pathfinder.complete_multipart_upload(
			Bucket = current_app.config['BUCKET_NAME'],
			Key = data['image_key'],
			MultipartUpload={
				'Parts': data['parts']
			},
			UploadId = data['upload_id'],
		)
	except Exception:
		abort(500)
	return jsonify(response), 201

@bp.route('/api/v1/upload/image/abort', methods=['POST'])
@login_required 
def abort_upload():
	'''
	Aborts a multipart upload. This endpoint is for cleaning up partial 
	uploads on the storage backend if an upload is canceled or fails
	permanently.
	'''
	data = request.get_json()
	try:
		response = pathfinder.abort_multipart_upload(
			Bucket = current_app.config['BUCKET_NAME'],
			Key = data['image_key'],
			UploadId = data['upload_id'],
		)
	except Exception: #
		abort(500)
	return jsonify(response), 201

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
	image = base.getImage(UUID(data['image_id']))
	img_data = cache.get(image.uuid)

	if not img_data:
		img_key = f'images/survey/{data['survey_id']}/herd_unit/{data['herd_unit_id']}/image/{image.name}'
		img_data = pathfinder.get_object(Bucket=current_app.config['BUCKET_NAME'], Key=img_key)['Body'].read()
		cache.set(image.uuid, img_data, 360) 

	image.setImage(img_data)
	pred_crops = create_subcrop(image, data['predictions'])
	serialized_pred_crops = [] 

	for crop in pred_crops: # Save crop image data into the session cache
		cache.set(crop.uuid,  crop.getImage(), 3600)
		serialized_pred_crops.append(crop.serialize())
	
	json_pred_crop_data = jsonify(serialized_pred_crops)
	
	if 'pred_crop_data' not in session:
		session['pred_crop_data'] = []
	
	session['pred_crop_data'] + serialized_pred_crops #type: ignore
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

@bp.route('/api/v1/update/image/set-closed', methods=["POST"])
@login_required
def no_annotations():
	'''
	
	'''
	data = request.get_json()
	res = base.close_image(UUID(data['image_id']))
	return '', 201 if res  else abort(500, 'Update failed!')

@bp.route('/api/v1/create/reviewed-area-and-annotations', methods=["PUT"])
@login_required
def create_reviewed_area_and_annotations():
	'''
	
	'''
	data = request.get_json()
	# Request image object from data in request
	image = base.getImage(UUID(data['image_uuid']))
	img_data = cache.get(image.uuid)

	if not img_data:
		img_key = f'images/survey/{data['survey_id']}/herd_unit/{data['herd_unit_id']}/image/{image.name}'
		img_data = pathfinder.get_object(Bucket=current_app.config['BUCKET_NAME'], Key=img_key)['Body'].read()
		cache.set(image.uuid, img_data, 360) 
	image.setImage(img_data)

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

		pathfinder.put_object(
			Bucket=current_app.config['BUCKET_NAME'],
			Key=ra_key,
			Body=io.BytesIO(img_bytes),  #type: ignore
			ContentType='image/jpeg'
		)

	res_3 = base.close_image(image)

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

@bp.route('/api/v1/end/crop_session', methods=['POST'])
@login_required
def close_crop_session():
	'''
	
	'''
	try:
		base.set_user_open_images_closed(current_user.user_id)
	except Exception as e:
		abort(500, e)
	return '', 201 

#---------------------------------------------------------------------------------------------------------------------------#
# Crop Review
# This route name is kinda bad, but it cant be called getRA because thats a different kind of endpoint 
@bp.route('/api/v1/create/reviewed-area-batch', methods=['POST'])
@login_required
def get_ra_batch():
	'''

	'''
	data = request.get_json()
	try:
		ra = base.get_crop_to_review(
			cast(User, current_user), 
			UUID(data['herd_unit_id']),
			UUID(data['survey_id']))
	except Exception as e:
		abort(404, str(e))

	# set image open 
	user_id = cast(User, current_user).user_id
	base.update_image(ra.image_id, opened_by_user_id=user_id)
	return ra.serialize(), 201

@bp.route('/api/v1/create/reviewed-area/presigned-get-url', methods=['POST'])
@login_required
def create_ra_presigned_get():
	'''
	'''
	data = request.get_json()
	try:
		response = pathfinder.generate_presigned_url(
			'get_object',
			Params={'Bucket': current_app.config['BUCKET_NAME'],
					'Key': data['ra_key']
			},
			ExpiresIn=3600,
		)
	except Exception as e:
		print(e)
		abort(500)
	return jsonify(response), 201

@bp.route('/api/v1/get/reviewed-area/<string:reviewed_area_id>/annotations', methods=['GET'])
@login_required
def get_ra_annotations(reviewed_area_id: str):
	'''
	'''
	annotations = base.get_crop_annotations(UUID(reviewed_area_id))
	return [annot.serialize() for annot in annotations], 201

@bp.route('/api/v1/update/reviewed-area/approve-annotations', methods=['POST', 'PUT'])
@login_required
def approve_annotations():
	'''
	
	'''
	data = request.get_json()
	reviewed_area = data['reviewed_area']
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
				user_id = cast(User, current_user),
				uuid = annot['uuid']
			)

		if res_i == False:
			abort(500, 'failed to make or update annotations')

	# loop over deleted annotations
	for annot in data['deleted_annotations']:
		base.delete_annotation(annot['annotation_id'])

	# set crop reviewed 
	res_1 = base.update_reviewed_area(reviewed_area['reviewed_area_id'], reviewed_by_user_id = cast(User, current_user).user_id)

	# set image closed
	res_2 = base.update_image(reviewed_area['image_id'], opened_by_user_id=0)

	if res_1 == False or res_2 == False:
		abort(500, 'failed to set image crop reviewed and image closed')

	return '', 201



#---------------------------------------------------------------------------------------------------------------------------#
# Inference

@bp.route('/api/v1/get/survey/<string:survey_id>/images/all', methods=['GET'])
@login_required
def get_survey_images(survey_id: str):
	'''
	
	'''
	try:
		images = base.get_survey_images(UUID(survey_id))
		serialized_images = [image.serialize() for image in images]
	except Exception as e:
		print(e)
		abort(500, e)
	return jsonify(serialized_images), 201

