"""Database abstraction layer and errors package."""

from .database import Database
from .errors import (
    AirialError,
    AuthenticationFailure,
    AuthorizationFailure,
    FailedToCreate,
    ObjectNotFound,
    UserNotFound,
)

__all__ = [
    "AirialError",
    "AuthenticationFailure",
    "AuthorizationFailure",
    "Database",
    "FailedToCreate",
    "ObjectNotFound",
    "UserNotFound",
]
