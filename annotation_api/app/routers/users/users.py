# Endpoints for managing legacy manual token users in the API 
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from cropgenerator.generatorobjects import User
from flask import Blueprint, abort
from flask_login import current_user, login_required, login_user, logout_user
from flask_pydantic import validate
from msgpack import packb, unpackb
from psycopg.errors import DatabaseError, UniqueViolation
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import base, cache, login_manager
from database import AuthorizationFailure, ObjectNotFound, UserNotFound
from database.view_models.users import *

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
	except (DatabaseError, Exception):
		abort(500)
	
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

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@userBp.get('/current-user')
@login_required
def get_current_user():
	try:
		user = base.get_user(UUID(current_user.id))
	except UserNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception):
		abort(500)

	return user.to_dict(), 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@userBp.get('/has-role')
@login_required
@validate()
def check_role(query: RoleQuery):
	'''
	'''
	role_id = UUID(query.role_id) if isinstance(query.role_id, str) else query.role_id
	try:
		role = base.get_role(role_id)
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception):
		abort(500)

	if role in current_user.roles:
		return 'true', 200
	else:
		return 'false'

#---------------------------------------------------------------------------------------------------------------------------#
# POST

@userBp.post('/authenticate/manual-token')
@validate()
def authenticate(body: Authenticate):
	''' Legacy manual token aut
	'''

	try:
		user = base.get_user(body.email)
		base.login_user(body.external_auth_id)
	except AuthorizationFailure as e:
		abort(401, str(e))
	else:
		login_user(user)
		
		return user.to_dict(), 201

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@userBp.post('/deauthenticate')
@login_required
def logout():
	logout_user()
	return '', 200