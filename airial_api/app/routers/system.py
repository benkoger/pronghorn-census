# Endpoints for managing the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from flask import Blueprint, abort, current_app

from app.extensions import base

systemBp = Blueprint("system", __name__, url_prefix="/api/v1")

# ---------------------------------------------------------------------------------------------------------------------------


@systemBp.get("/bootstrapped")
def check_bootstrapped():
    try:
        res = base.check_bootstrapped()
    except Exception as e:
        current_app.logger.exception(e)
        abort(500)

    return {"result": res}, 201
