# Endpoints for integrating oauth2.0 
# Special thanks to Miguel Grinberg for the excellent guide 
# https://blog.miguelgrinberg.com/post/oauth-authentication-with-flask-in-2023
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

import secrets
from urllib.parse import urlencode
from uuid import UUID

from flask import Blueprint, abort, current_app, redirect, request, session, url_for
from flask_login import login_user
from psycopg.errors import DatabaseError
import requests

from app.extensions import base
from database.errors import *
from database.view_models.users import *

authBp = Blueprint('oauth2', __name__, url_prefix='/api/v1/')

#---------------------------------------------------------------------------------------------------------------------------#
# Authorization

@authBp.get('/authorize/<string:provider>')
def oauth2_authorize(provider: str):
	'''
	'''
	provider_data = current_app.config['OAUTH2_PROVIDERS'].get(provider)
	if not provider_data:
		abort(404, 'Oauth Provider not found')

	session['oauth2_state'] = secrets.token_urlsafe(16)
	session.modified = True

	query_string = urlencode({
		'client_id': provider_data['client_id'],
		'redirect_uri': url_for('.oauth2_callback', provider=provider, 
									_external=True),
		'response_type': 'code',
		'scope': ' '.join(provider_data['scopes']),
		'state': session['oauth2_state'],
	})

	return redirect(provider_data['authorize_url'] + '?' + query_string)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@authBp.get('/callback/<string:provider>')
def oauth2_callback(provider: str):
	'''

	'''
	provider_data = current_app.config['OAUTH2_PROVIDERS'].get(provider)
	if not provider_data:
		abort(404, 'Oauth Provider not found')

	if 'error' in request.args:
		for key, value in request.args.items():
			if key.startswith('error'):
				print(f'key: {key}, value: {value}')
				abort(500)
	
	if request.args['state'] != session.get('oauth2_state'):
		abort(401)

	if 'code' not in request.args:
		abort(401)

	response = requests.post(provider_data['token_url'], data={
		'client_id': provider_data['client_id'],
		'client_secret': provider_data['client_secret'],
		'code': request.args['code'],
		'grant_type': 'authorization_code',
		'redirect_uri': url_for('.oauth2_callback', provider=provider,
									_external=True)
	}, headers={'Accept': 'application/json'})

	if response.status_code != 200:
		abort(401)
	
	oauth2_token = response.json().get('access_token')
	if not oauth2_token:
		abort(401)

	response = requests.get(provider_data['userinfo']['url'], headers={
		'Authorization': 'Bearer ' + oauth2_token,
		'Accept': 'application/json'
	})
	if response.status_code != 200:
		abort(401)
	email = provider_data['userinfo']['email'](response.json())

	try:	
		print(email)
		user = base.get_user(email)
	except UserNotFound:
		abort(403, 'You must first be invited to access this resource')
	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)

	if user.status == 'invited':
		base.activate_user(user.email, user.user_id, response.json().get('sub'), provider)
	else:
		base.login_user(user.user_id)

	login_user(user)

	frontend_url = current_app.config.get('ORIGIN_URL')
	return redirect(f"{frontend_url}/")