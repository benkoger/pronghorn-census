# Endpoints for managing models in the API 
# Author: Michael B. Lance
# Created: Janaury 28, 2025
# Updated: Janaury 29, 2025

#---------------------------------------------------------------------------------------------------------------------------#

from flask import Blueprint, Response, abort, jsonify, request, session, current_app
from app.extensions import login_manager, cache, base 
from database import Database
from flask_login import (
	current_user,
	login_required,
) 

modelBp = Blueprint('training', __name__, url_prefix='/api/v1/models')

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
	score_range = request.args.get('score_range', None)
	surveys = request.args.getlist('survey')
	labels = request.args.getlist('labels')
	herd_units = request.args.getlist('herd_unit')
	
	# call db method passing the params. method will handle null parameters 

	return ''

#---------------------------------------------------------------------------------------------------------------------------#
# POST

@modelBp.post('')
@login_required
def create():
	'''

	'''
	project_id = request.args.get('project_id', 0)
	return ''

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
	return ''

#---------------------------------------------------------------------------------------------------------------------------#
# DELETE

@modelBp.delete('/<string:model_id>') 
@login_required
def delete_model(model_id: str):
	'''

	'''
	return ''