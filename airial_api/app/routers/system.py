"""Endpoints for managing system state and bootstrap status in the API."""

from flask import Blueprint
from flask_login import login_required

from app.extensions import base

systemBp = Blueprint("system", __name__, url_prefix="/api/v1")

# ---------------------------------------------------------------------------------------------------------------------------


@systemBp.get("/bootstrapped")
def check_bootstrapped():
    """Check whether the application and database have been bootstrapped.

    Returns:
        Tuple containing a dictionary with boolean result and HTTP status 200.
    """
    res = base.check_bootstrapped()

    return {"result": res}, 200


# ---------------------------------------------------------------------------------------------------------------------------


@systemBp.post("/bootstrapped")
@login_required
def finish_bootstrapp():
    """Mark the application bootstrap process as complete.

    Returns:
        Tuple containing empty string and HTTP status 204.
    """
    base.set_bootstrapped()

    return "", 204
