# Psycopg3 database abstraction layer errors for crop generator_api
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from abc import ABC
from dataclasses import dataclass

# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class AirialError(ABC, Exception):
    name: str
    code: int
    message: str
    pass


# ---------------------------------------------------------------------------------------------------------------------------


class ObjectNotFound(AirialError):
    """Raised when an image UUID does not exist in the database."""

    def __init__(self, object_type: str, object_id: str):
        super().__init__(
            "Object Not Found", 404, f"{object_type} with ID {object_id} not found."
        )


# ---------------------------------------------------------------------------------------------------------------------------


class FailedToCreate(AirialError):
    """Raised when an object fails to be created"""

    def __init__(self, object_type: str):
        self.message = f"Failed to create {object_type}"
        super().__init__("Invalid Request", 400, self.message)


# ---------------------------------------------------------------------------------------------------------------------------


class AuthenticationFailure(AirialError):
    """Raised when an authentication attempt fails"""

    def __init__(self):
        self.message = "Username or Password is incorrect"
        super().__init__("Unauthorized", 401, "Authentication Failure")


# ---------------------------------------------------------------------------------------------------------------------------


class UserNotFound(AirialError):
    """Raised when a user is not found"""

    def __init__(self):
        super().__init__("ObjectNotFound", 404, "User not found")


# ---------------------------------------------------------------------------------------------------------------------------


class AuthorizationFailure(AirialError):
    """Raised when a user attempts to access an object they are supposed to"""

    def __init__(self, user_id: str, permission: str, object_type: str, object_id: str):
        self.message = f"User: {user_id} does not have permission {permission} for {object_type}: {object_id}"
        super().__init__("Unauthorized", 401, self.message)
