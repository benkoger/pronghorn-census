# Endpoints for managing projects in the API 
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from cropgenerator.generatorobjects import Organization, User
from flask import Blueprint, abort, session
from flask_login import login_required, current_user
from flask_pydantic import validate
from msgpack import unpackb
from psycopg.errors import DatabaseError
from typing import cast

from app.extensions import base
from database import ObjectNotFound
from database.view_models.projects import (
		ProjectQuery,
		)

projectBp = Blueprint('projects', __name__, url_prefix='/api/v1/projects')

#---------------------------------------------------------------------------------------------------------------------------#
# GET

@projectBp.get('/')
@login_required
@validate()
def get_all(query: ProjectQuery):
	'''

	'''
	try:
		org_id = session.get('active_org_uuid')
		active_org = session.get(f'org_{org_id}')	
		org = Organization(**unpackb(active_org))
		
		projects = base.get_projects(query, org)
	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)
	return [proj.to_dict() for proj in projects], 200

@projectBp.get('/<string:project_id>')
@login_required
def get_by_id(project_id: str):
	'''
	Request a project object from the database using its UUID.
	---
	parameters:
	  - project_id
		in: path
		type: string
		required: true
	responses:
	  200:
		description: The requested project was found.
	  400:
		description: Invalid UUID format provided.
	  404:
		description: No project record found for the provided ID.
	  500:
		description: Database Error.
	'''
	try:
		project = base.get_project(UUID(project_id))
	except ValueError as e:
		abort(400, str(e))
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)
	
	return project.to_dict(), 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@projectBp.get('/<string:project_id>/models')
@login_required
def get_models(project_id: str):
	'''
	Retrieve models for a specific project
	---
	---
	parameters:
		- name: project_id
		in: path
		type: string
		required: true
	responses:
	  200:
		description: List of models.
	  404:
		description: No project found.
	  500:
		description: Database error.
	'''
	try:
		models = base.get_project_models(UUID(project_id), cast(User, current_user))
	except ValueError as e:
		abort(400, str(e))
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception):
		abort(500)
	
	return [model.to_dict() for model in models], 200

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

@projectBp.get('/<string:project_id>/herd-units')
@login_required
def get_herd_units(project_id: str):
	'''
	Retrieve herd units for a specific project
	---
	responses:
	  200:
		description: List of herd units.
	  404:
		description: No project found.
	  500:
		description: Database error.
	'''
	try:
		herd_units = base.get_project_herd_units(UUID(project_id), cast(User, current_user))
	except ValueError as e:
		abort(400, str(e))
	except ObjectNotFound as e:
		abort(404, str(e))
	except (DatabaseError, Exception) as e:
		print(e)
		abort(500)
	
	return [herd_unit.to_dict() for herd_unit in herd_units], 200
