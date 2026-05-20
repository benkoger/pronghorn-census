# Error Handling for the Airial API
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from flask import current_app
from werkzeug.exceptions import HTTPException
from database.errors import AirialError

# ---------------------------------------------------------------------------------------------------------------------------


def handle_generic_http(error: HTTPException):
    current_app.logger.error(f"HTTP {error.code}: {error.description}")

    status_code = error.code if error.code is not None else 500
    return {
        "error": error.name,
        "code": error.code,
        "message": error.description,
    }, status_code


# ---------------------------------------------------------------------------------------------------------------------------


def handle_airial_error(error: AirialError):
    current_app.logger.error(str(error))
    return (
        {"error": error.name, "code": error.code, "message": error.message},
        error.code,
    )


# ---------------------------------------------------------------------------------------------------------------------------


def internal_service_error(error: Exception):
    current_app.logger.exception(error)
    return (
        {
            "error": "Internal Server Error",
            "code": 500,
            "message": "An unexpected error occurred on the server.",
        },
        500,
    )
