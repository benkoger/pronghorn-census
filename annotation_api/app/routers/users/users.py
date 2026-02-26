# Endpoints for managing users in the API 
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from flask import Blueprint, abort, current_app, request, Response
from flask_login import current_user, login_required
from flask_login import current_user, login_required, login_user, logout_user
from flask_pydantic import validate
from psycopg.errors import DatabaseError, UniqueViolation

from cropgenerator.generatorobjects import User

from app.extensions import base, cache, login_manager
from database import AuthorizationFailure, UserNotFound

from .user_validators import *
from msgpack import unpackb, packb

userBp = Blueprint('users', __name__, url_prefix='/api/v1/users')

#---------------------------------------------------------------------------------------------------------------------------#

@login_manager.user_loader
def load(session_user_id: str):
	user_key = 'user_{}'.format(session_user_id)
	cached_user = cache.get(user_key)

	if cached_user:
		return User(**unpackb(cached_user))

	try:
		user_obj = base.get_user(UUID(session_user_id))
		cache.set(user_key, packb(user_obj.to_cache()), timeout=3600)
	except UserNotFound as e:
		abort(404, str(e))
	
	return user_obj

@login_manager.unauthorized_handler
def unathorizated_callback():
	abort(401, 'unathorized, are you logged in? Should you be accessing this?')

#---------------------------------------------------------------------------------------------------------------------------#
# Get

@userBp.get('/check-auth')
@login_required
def check_auth():
	return 'true', 201

@userBp.route('/get-current-user', methods = ['GET'])
@login_required
def getCurrentUser():
	try:
		user = base.get_user(UUID(current_user.id))
	except Exception:
		abort(500)
	return user.to_dict(), 201


#---------------------------------------------------------------------------------------------------------------------------#
# POST

@userBp.post('/authenticate')
@validate()
def authenticate(body: Authenticate):
	'''
	'''

	try:
		user = base.login_user(body.external_id)
	except AuthorizationFailure as e:
		abort(401, str(e))
	else:
		login_user(user)
		
		return user.to_dict(), 201

@userBp.post('/deauthenticate')
@login_required
def logout():
	logout_user()
	return '', 200