# Endpoints for managing the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from flask import Blueprint
from flask_login import login_required

from app.extensions import base

systemBp = Blueprint("system", __name__, url_prefix="/api/v1")

# ---------------------------------------------------------------------------------------------------------------------------


@systemBp.get("/bootstrapped")
def check_bootstrapped():
    """ """
    res = base.check_bootstrapped()

    return {"result": res}, 200


# ---------------------------------------------------------------------------------------------------------------------------


@systemBp.post("/bootstrapped")
@login_required
def finish_bootstrapp():
    """ """
    base.set_bootstrapped()

    return "", 204
