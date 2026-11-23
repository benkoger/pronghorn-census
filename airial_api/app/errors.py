"""Error handling and exception definitions for the Airial API."""

# ---------------------------------------------------------------------------------------------------------------------------

from flask import current_app
from werkzeug.exceptions import HTTPException

from database.errors import AirialError

# ---------------------------------------------------------------------------------------------------------------------------
# Application Exception Classes


class AppError(AirialError):
    """Base exception class for application-level API errors."""


class ImageReadError(AppError):
    """Raised when an image payload cannot be read or decoded into pixel data."""

    def __init__(self, image_id: str):
        """Initialize ImageReadError exception.

        Args:
            image_id: Identifier for the image that could not be read.
        """
        self.message = f"Could not read image {image_id}"
        super().__init__("Image Read Error", 500, self.message)


# ---------------------------------------------------------------------------------------------------------------------------
# Error Handlers


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
