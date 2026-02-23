# Psycopg3 database abstraction layer errors for crop generator_api
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

class ObjectNotFound(Exception):
    """Raised when an image UUID does not exist in the database."""
    def __init__(self, object_type: str, object_id: str | int | UUID):
        self.message = f"{object_type} with ID {str(object_id)} not found."
        super().__init__(self.message)