"""Database and authorization exception classes for the Airial API."""

# ---------------------------------------------------------------------------------------------------------------------------

from abc import ABC
from dataclasses import dataclass

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class AirialError(ABC, Exception):
    """Base exception class for Airial errors."""

    name: str
    code: int
    message: str


# ---------------------------------------------------------------------------------------------------------------------------


class ObjectNotFound(AirialError):
    """Raised when an image UUID does not exist in the database."""

    def __init__(self, object_type: str, object_id: str):
        """Initialize ObjectNotFound exception.

        Args:
            object_type: Name of the missing entity model type.
            object_id: Identifier of the entity that was not found.
        """
        super().__init__("Object Not Found", 404, f"{object_type} with ID {object_id} not found.")


# ---------------------------------------------------------------------------------------------------------------------------


class FailedToCreate(AirialError):
    """Raised when an object fails to be created."""

    def __init__(self, object_type: str):
        """Initialize FailedToCreate exception.

        Args:
            object_type: Name of the entity model type that failed creation.
        """
        self.message = f"Failed to create {object_type}"
        super().__init__("Invalid Request", 400, self.message)


# ---------------------------------------------------------------------------------------------------------------------------

class FailedToFetch(AirialError):
    """Raised when a fetch operation from the database fails."""

    def __init__(self, object_type: str):
        """Initialize FailedToFetch exception.
        
        Args:
            object_type: Name of the entity model type that could not be fetched.
        """
        self.message = f"Failed to fetch {object_type}"
        super().__init__("Invalid Request", 400, self.message)


# ---------------------------------------------------------------------------------------------------------------------------


class AuthenticationFailure(AirialError):
    """Raised when an authentication attempt fails."""

    def __init__(self):
        """Initialize AuthenticationFailure exception."""
        self.message = "Username or Password is incorrect"
        super().__init__("Unauthorized", 401, "Authentication Failure")


# ---------------------------------------------------------------------------------------------------------------------------


class UserNotFound(AirialError):
    """Raised when a user is not found."""

    def __init__(self):
        """Initialize UserNotFound exception."""
        super().__init__("ObjectNotFound", 404, "User not found")


# ---------------------------------------------------------------------------------------------------------------------------


class AuthorizationFailure(AirialError):
    """Raised when a user attempts to access an object without authorization."""

    def __init__(self, user_id: str, permission: str, object_type: str, object_id: str):
        """Initialize AuthorizationFailure exception.

        Args:
            user_id: User identifier lacking permission.
            permission: Requested permission relation name.
            object_type: Target resource entity type.
            object_id: Target resource identifier.
        """
        self.message = f"User: {user_id} does not have permission {permission} for {object_type}: {object_id}"
        super().__init__("Unauthorized", 401, self.message)


# ---------------------------------------------------------------------------------------------------------------------------


class MissingImageData(AirialError):
    """Raised when an images serve method is called when its data has not been loaded from s3."""

    def __init__(self, image_id: str):
        """Initialize Missing ImageData exception.

        Args:
            image_id: Identifier for image object.
        """
        self.mesage = f"Image: {image_id} does not have any data loaded!"
        super().__init__("No Image Data", 500, self.message)
