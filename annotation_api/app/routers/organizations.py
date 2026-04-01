# Endpoints for managing organizations in the api
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from flask import Blueprint, session
from flask_login import current_user, login_required
from flask_pydantic import validate

from app.extensions import base
from database.view_models.organizations import (
		SetActiveOrg
		)

orgBp = Blueprint('organizations', __name__, url_prefix='/api/v1/organizations')

#---------------------------------------------------------------------------------------------------------------------------#
# PATCH

