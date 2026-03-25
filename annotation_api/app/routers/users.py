# Endpoints for managing legacy manual token users in the API 
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from cropgenerator.generatorobjects import User
from flask import Blueprint, abort, session
from flask_login import current_user, login_required, login_user, logout_user
from flask_pydantic import validate
from msgpack import packb, unpackb
from psycopg.errors import DatabaseError, UniqueViolation
from werkzeug.security import check_password_hash

from app.extensions import base, cache, login_manager
from app.decorators import roles_required
from database import AuthorizationFailure, ObjectNotFound, UserNotFound
from database.view_models.users import *
from database.view_models.organizations import SetActiveOrg

userBp = Blueprint('users', __name__, url_prefix='/api/v1/users')

#---------------------------------------------------------------------------------------------------------------------------#

@login_manager.user_loader
def load(session_user_id: str):
	user_key = 'user_{}'.format(session_user_id)
	cached_user = cache.get(user_key)

	if cached_user:
		user = User(**unpackb(cached_user))
		return user
	try:
		user_obj = base.get_user(UUID(session_user_id))
		cache.set(user_key, packb(user_obj.to_cache()), timeout=3600)
	except UserNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)
	
	return user_obj

@login_manager.unauthorized_handler
def unathorizated_callback():
	abort(401, 'unathorized, are you logged in? Should you be accessing this?')

#---------------------------------------------------------------------------------------------------------------------------#
# GET

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
	return 'true', 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@userBp.get('/current-user')
@login_required
def get_current_user():
	'''
	'''
	return current_user.to_dict(), 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@userBp.get('/<string:user_id>/organizations')
@login_required
def get_orgs(user_id: str):
	'''
	
	'''
	try:
		orgs = base.get_user_organizations(UUID(user_id))
		print(orgs[0].to_dict)
	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)

	return [org.to_dict() for org in orgs]

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@userBp.get('/role-check')
@login_required
@validate()
def check_role(query: RoleQuery):
	'''
	'''

	if current_user.roles and query.role_name in current_user.roles:
		return 'true', 200
	else:
		return 'false', 200

#---------------------------------------------------------------------------------------------------------------------------#
# POST

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

#---------------------------------------------------------------------------------------------------------------------------#
# PATCH

@userBp.patch('/set-active-organization')
@login_required
@validate()
def set_org(body: SetActiveOrg):
	'''

	'''
	if isinstance(body.org_id, int):
		org_id = base.get_organization(body.org_id).uuid
	else: 
		org_id = body.org_id

	session['active_org_uuid'] = org_id 

	return '', 200
