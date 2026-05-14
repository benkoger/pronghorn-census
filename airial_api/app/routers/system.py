# Endpoints for managing the API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from flask import Blueprint, abort, current_app
from flask_login import login_required
from psycopg import DatabaseError

from app.extensions import base

systemBp = Blueprint("system", __name__, url_prefix="/api/v1")

# ---------------------------------------------------------------------------------------------------------------------------


@systemBp.get("/bootstrapped")
def check_bootstrapped():
    try:
        res = base.check_bootstrapped()
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return {"result": res}, 200


# ---------------------------------------------------------------------------------------------------------------------------


@systemBp.post("/bootstrapped")
@login_required
def finish_bootstrapp():
    try:
        base.set_bootstrapped()
    except (DatabaseError, Exception) as e:
        current_app.logger.exception(e)
        abort(500)

    return "", 204
