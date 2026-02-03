# Endpoints for managing models in the API 
# Author: Michael B. Lance
# Created: Janaury 28, 2026
# Updated: February 3, 2026

#---------------------------------------------------------------------------------------------------------------------------#

from flask import Blueprint,  abort, request
from app.extensions import base 
from datetime import date, datetime
from flask_login import (
	login_required,
) 
from typing import cast, List
from uuid import UUID

modelBp = Blueprint('models', __name__, url_prefix='/api/v1/models')

#TODO: These endpoints require propper organizational and project checking

#---------------------------------------------------------------------------------------------------------------------------#
# GET

@modelBp.get('/all')
@login_required
def get_all():
	'''

	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.get('/<string:model_id>')
@login_required
def get_by_id(model_id: str):
	'''

	'''
	model = base.get_model(UUID(model_id))

	if model is not None:
		return model.serialize()
	else:
		abort(404, f'Model with ID {model_id} was not found!')
	
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.get('/<string:model_id>/json')
@login_required
def get_json_all():
	'''

	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.get('/<string:model_id>/json/train')
@login_required
def get_json_train():
	'''

	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.get('/<string:model_id>/json/val')
@login_required
def get_json_test():
	'''

	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.get('/<string:model_id>/weights')
@login_required
def get_weights():
	'''

	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.get('/<string:model_id>/config')
@login_required
def get_config():
	'''

	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.get('/<string:model_id>/readme')
@login_required
def get_readme():
	'''

	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.get('/<string:model_id>/predictions')
@login_required
def get_predictions():
	'''

	'''
	score_range = request.args.get('score_range', None)
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.get('/training')
@login_required
def get_training_set():
	'''
	'''
	date_range = request.args.get('date_range', None)
	surveys = request.args.getlist('survey', type=int)
	labels = request.args.getlist('labels', type=int)
	herd_units = request.args.getlist('herd_unit', type=int)
	format_pattern = "%m/%d/%Y %H:%M:%S"

	if date_range is not None:
		date_range = (
			datetime.strptime(date_range[0], format_pattern), 
			datetime.strptime(date_range[1], format_pattern)
		)
	
	# call db method passing the params. method will handle null parameters
	try:

		data = base.get_model_training_data(
			labels,
			date_range,
			surveys,
			herd_units
		)
	except Exception as e:
		abort(404, 'bro what?')
	return data, 200

#---------------------------------------------------------------------------------------------------------------------------#
# POST

@modelBp.post('/new')
@login_required
def create():
	'''

	'''
	data = request.get_json()

	if not data['name']:
		abort(400, 'Error creating model! No name provided.')
	elif not data['project_id']:
		abort(400, 'Error creating model! Models must be associated with at least one project.')
	elif not data['schema_id']:
		abort(400, 'Error creating model! No schema provided.')

	project_id = data['project_id'] if isinstance(data['project_id'], int) else UUID(data['project_id'])
	schema_id = data['schema_id'] if isinstance(data['schema_id'], int) else UUID(data['schema_id'])
	survey_ids = [
		cast(int, survey_id) if isinstance(survey_id, int) else UUID(survey_id)
		for survey_id in data['survey_ids']
		]
	try:
		model = base.create_model(
			data['name'],
			project_id,
			schema_id,
			survey_ids
		)
	except Exception as e:
		print(e)
		abort(500)

	return model.serialize(), 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.post('/<string:model_id>/train')
@login_required
def create_train_json(model_id: str):
	'''
	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.post('/<string:model_id>/val')
@login_required
def create_val_json(mdoel_id: str):
	'''
	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.post('/<string:model_id>/weights')
@login_required
def create_weights(mdoel_id: str):
	'''
	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.post('/<string:model_id>/config')
@login_required
def create_config(model_id: str):
	'''
	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.post('/<string:model_id>/readme')
@login_required
def create_readme(model_id: str):
	'''
	'''
	return ''

#---------------------------------------------------------------------------------------------------------------------------#
# PUT

@modelBp.put('/<string:model_id>')
@login_required
def replace(model_id: str):
	'''

	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.put('/<string:model_id>/train')
@login_required
def replace_train_json(model_id: str):
	''' Replace the train.json file to s3 under the model's base key

	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.put('/<string:model_id>/val')
@login_required
def replace_val_json(model_id: str):
	''' Replace val.json file to s3 under the model's base key

	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.post('/<string:model_id>/weights')
@login_required
def replace_weights(mdoel_id: str):
	'''
	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.post('/<string:model_id>/config')
@login_required
def replace_config(mdoel_id: str):
	'''
	'''
	return ''

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@modelBp.post('/<string:model_id>/readme')
@login_required
def replace_readme(model_id: str):
	'''
	'''
	return ''

#---------------------------------------------------------------------------------------------------------------------------#
# PATCH (since json files are stored on s3 they are not patchable in the same way a database object is)

@modelBp.patch('/<string:model_id>')
@login_required
def update(model_id: str):
	'''

	'''
	data = request.get_json()
	
	try:
		model = base.update_model(
			UUID(model_id),
			data
		)
	except Exception as e:
		print(f'error: {e}')
		abort(500)

	return model.serialize(), 200

#---------------------------------------------------------------------------------------------------------------------------#
# DELETE

@modelBp.delete('/<string:model_id>') 
@login_required
def delete_model(model_id: str):
	'''

	'''
	return ''