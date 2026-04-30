# Core router for the API
# Author: Michael B. Lance
# TODO: Finish removing endpoints into sub routers

# ---------------------------------------------------------------------------------------------------------------------------#


from flask import Blueprint

from .authenticate import authBp
from .autocropper import cropBp
from .cropverifier import verifierBp
from .herd_units import herdunitBp
from .images import imageBp
from .models import modelBp
from .organizations import orgBp
from .projects import projectBp
from .reviewed_area import raBp
from .schemas import schemaBp
from .surveys import surveyBp
from .users import userBp
from .annotations import annotBp

# ---------------------------------------------------------------------------------------------------------------------------#

bp = Blueprint("app", __name__)

bp.register_blueprint(herdunitBp)
bp.register_blueprint(imageBp)

bp.register_blueprint(modelBp)
bp.register_blueprint(projectBp)

bp.register_blueprint(schemaBp)
bp.register_blueprint(surveyBp)

bp.register_blueprint(verifierBp)
bp.register_blueprint(raBp)

bp.register_blueprint(userBp)
bp.register_blueprint(authBp)

bp.register_blueprint(cropBp)
bp.register_blueprint(orgBp)

bp.register_blueprint(annotBp)
