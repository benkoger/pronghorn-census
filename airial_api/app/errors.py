"""HTTP and Airial database error handlers for Flask."""

# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from flask import current_app
from werkzeug.exceptions import HTTPException

from database.errors import AirialError

# ---------------------------------------------------------------------------------------------------------------------------


def handle_generic_http(error: HTTPException):
    """Handle generic Werkzeug HTTP exceptions and return JSON response.

    Args:
        error: Raised Werkzeug HTTP exception.

    Returns:
        Tuple containing error response dictionary and integer HTTP status code.
    """
    current_app.logger.error(f"HTTP {error.code}: {error.description}")

    status_code = error.code if error.code is not None else 500
    return {
        "error": error.name,
        "code": error.code,
        "message": error.description,
    }, status_code


# ---------------------------------------------------------------------------------------------------------------------------


def handle_airial_error(error: AirialError):
    """Handle Airial custom domain exceptions and return JSON response.

    Args:
        error: Raised Airial domain exception.

    Returns:
        Tuple containing error payload dictionary and integer HTTP status code.
    """
    current_app.logger.error(str(error))
    return (
        {"error": error.name, "code": error.code, "message": error.message},
        error.code,
    )


# ---------------------------------------------------------------------------------------------------------------------------


def internal_service_error(error: Exception):
    """Handle uncaught 500 exceptions and log traceback.

    Args:
        error: Uncaught exception instance.

    Returns:
        Tuple containing error payload dictionary and 500 HTTP status code.
    """
    current_app.logger.exception(error)
    return (
        {
            "error": "Internal Server Error",
            "code": 500,
            "message": "An unexpected error occurred on the server.",
        },
        500,
    )
