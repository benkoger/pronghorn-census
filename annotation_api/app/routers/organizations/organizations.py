# Endpoints for managing organizations in the api
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

from cropgenerator.generatorobjects import Organization
from flask import Blueprint, abort, session
from flask_login import current_user, login_required
from flask_pydantic import validate
from msgpack import packb, unpackb
from psycopg.errors import DatabaseError, UniqueViolation

from app.decorators import roles_required
from app.extensions import base, cache
from database import AuthorizationFailure, ObjectNotFound, UserNotFound
from database.view_models.organizations import *

orgBp = Blueprint('organizations', __name__, url_prefix='/api/v1/organizations')

#---------------------------------------------------------------------------------------------------------------------------#
# PATCH

@orgBp.patch('/set_current_organization')
@login_required 
@validate()
def set_organization(body: SetActiveOrg):
	
	org = base.get_organization(body.org_id)

	if org.uuid in current_user.orgs:
		session['current_org_id'] = org.uuid

		projects = base.get_organization_projects(org.organization_id)

		session['current_org_projects'] 

	return '', 200