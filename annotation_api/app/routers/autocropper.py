# Endpoints for the autocropper utility 
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from cropgenerator.generatorobjects import User
from flask import Blueprint, abort
from flask_login import login_required, current_user
from flask_pydantic import validate
from psycopg.errors import DatabaseError
from typing import cast

from app.extensions import base
from database import ObjectNotFound
from database.view_models.autocropper import (
		AutoCropperBatchQuery,
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

