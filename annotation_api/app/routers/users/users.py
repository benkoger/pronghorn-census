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
from werkzeug.security import check_password_hash

from app.extensions import base, cache, login_manager
from app.decorators import roles_required
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

@userBp.get('')
@login_required
def get_all():
	'''

	'''
	try:
		users = base.get_users()
	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)

	return [user.to_dict() for user in users], 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

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

@userBp.get('/role-check')
@login_required
@validate()
def check_role(query: RoleQuery):
	'''
	'''
	print('I tried at all')
	try:
		role = base.get_role(query.role_name)
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)

	if role in current_user.roles:
		return 'true', 200
	else:
		return 'false', 200

#---------------------------------------------------------------------------------------------------------------------------#
# POST

@userBp.post('/authenticate')
@validate()
def authenticate(body: LegacyAuth):
	''' Legacy manual token aut
	'''

	try:
		user = base.get_user(body.email)
		print(user)
		if not user.password_hash:
			abort(400)

		if check_password_hash(body.password, user.password_hash):
			base.login_user(user.user_id)
			
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

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@userBp.post('')
@login_required
@validate()
def create(body: CreateUser):
	'''

	'''
	try:
		user = base.create_user(body)
	except UniqueViolation:
		abort(409, 'User already exists')
	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)

	return user.to_dict(), 201