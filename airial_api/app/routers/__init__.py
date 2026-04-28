# Core router for the API
# Author: Michael B. Lance
# TODO: Finish removing endpoints into sub routers

# ---------------------------------------------------------------------------------------------------------------------------#


from flask import Blueprint

from .authenticate import authBp
from .autocropper import cropBp
from .cropverifier import verifierBp
from .herd_units import herdunitBp
from .images import imageBp
from .models import modelBp
from .organizations import orgBp
from .projects import projectBp
from .reviewed_area import raBp
from .schemas import schemaBp
from .surveys import surveyBp
from .users import userBp
from .annotations import annotBp

# ---------------------------------------------------------------------------------------------------------------------------#

bp = Blueprint("app", __name__)

bp.register_blueprint(herdunitBp)
bp.register_blueprint(imageBp)

bp.register_blueprint(modelBp)
bp.register_blueprint(projectBp)

bp.register_blueprint(schemaBp)
bp.register_blueprint(surveyBp)

bp.register_blueprint(verifierBp)
bp.register_blueprint(raBp)

bp.register_blueprint(userBp)
bp.register_blueprint(authBp)

bp.register_blueprint(cropBp)
bp.register_blueprint(orgBp)

bp.register_blueprint(annotBp)

# #---------------------------------------------------------------------------------------------------------------------------#
# # Auto Cropping

# @bp.route('/api/v1/create/reviewed-area-and-annotations', methods=["PUT"])
# @login_required
# def create_reviewed_area_and_annotations():
# 	'''

# 	'''
# 	data = request.get_json()
# 	# Request image object from data in request
# 	image = base.get_image(UUID(data['image_uuid']))
# 	img_data = cache.get(image.uuid)

# 	if not img_data:
# 		img_key = f'images/survey/{data['survey_id']}/herd_unit/{data['herd_unit_id']}/image/{image.name}'
# 		img_data = s3.get_object(Bucket=current_app.config['BUCKET_NAME'], Key=img_key)['Body'].read()
# 		cache.set(image.uuid, img_data, 360)

# 	image.set_image(img_data)

# 	# get label - id for schema
# 	label_ids = { lbl['label'] : lbl['label_id'] for lbl in data['labels'] }

# 	# (re)Construct prediction objects from data in request
# 	predictions = []

# 	for pred in data['predictions']:
# 		prediction = Prediction(
# 			pred_id = pred['pred_id'],
# 			image_id = pred['image_id'],
# 			model_id = pred['model_id'],
# 			label = pred['label'],
# 			score = pred['score'],
# 			box_tx = pred['dimensions']['top_left'][0],
# 			box_ty = pred['dimensions']['top_left'][1],
# 			box_bx = pred['dimensions']['bottom_right'][0],
# 			box_by = pred['dimensions']['bottom_right'][1],
# 			created = datetime.fromisoformat(pred['created'].replace("Z", "+00:00")),
# 			uuid = pred['uuid'],
# 			reviewed_by_user_id = 0
# 		)
# 		predictions.append(prediction)

# 	# Create reviewed area(s) from auto_crop() function
# 	reviewed_areas = auto_crop(image=image, predictions=predictions, labels_ids=label_ids)

# 	#Create reviewed area and predictions objects
# 	res_1 = False # init result as false to calm pyright down
# 	for area_set in reviewed_areas:
# 		reviewed_area: ReviewedArea = cast(ReviewedArea, area_set[0])
# 		annotations: Annotation = cast(Annotation, area_set[1] )
# 		ra_key = f'reviewed_areas/survey/{data['survey_id']}/herd_unit/{data['herd_unit_id']}/reviewed_area/{reviewed_area.name}'
# 		reviewed_area.ra_key = ra_key
# 		reviewed_area_id = base.insert_reviewed_areas(reviewed_area)
# 		annotation_ids = base.insert_annotations(annotations, cast(User, current_user))
# 		res_1 = base.add_reviewed_area_annotations(cast(int, reviewed_area_id), annotation_ids)

# 		try:
# 			img_bytes = reviewed_area.serve('.JPG')
# 		except Exception as e:
# 			print(e)
# 			abort(500, e)

# 		s3.put_object(
# 			Bucket=current_app.config['BUCKET_NAME'],
# 			Key=ra_key,
# 			Body=io.BytesIO(img_bytes),  #type: ignore
# 			ContentType='image/jpeg'
# 		)

# 	res_3 = base.update_image(image.image_id, {'opened_by_user_id': 0})

# 	return '', 201 if res_1 and res_3 else abort(500)

# @bp.route('/api/v1/update/predictions/set-reviewed', methods=['POST'])
# @login_required
# def mark_predictions_reviewed():
# 	'''
# 	'''
# 	data = request.get_json()
# 	ids = [UUID(predId) for predId in data['prediction_ids']]
# 	res = base.set_predictions_reviewed(ids, cast(User, current_user).user_id)

# 	return '', 201 if res else abort(500)

# @bp.route('/api/v1/get/reviewed-area/<string:reviewed_area_id>/annotations', methods=['GET'])
# @login_required
# def get_ra_annotations(reviewed_area_id: str):
# 	'''
# 	'''
# 	annotations = base.get_crop_annotations(UUID(reviewed_area_id))
# 	return [annot.to_dict() for annot in annotations], 201
