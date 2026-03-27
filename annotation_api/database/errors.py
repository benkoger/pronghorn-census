# Psycopg3 database abstraction layer errors for crop generator_api
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from uuid import UUID

class ObjectNotFound(Exception):
	'''Raised when an image UUID does not exist in the database.'''
	def __init__(self, object_type: str, object_id: str):
		self.message = f'{object_type} with ID {str(object_id)} not found.'
		super().__init__(self.message)

class FailedToCreate(Exception):
	'''Raised when an object fails to be created'''
	def __init__(self, object_type: str):
		self.message = f'Failed to create {object_type}'
		super().__init__(self.message)

class AuthorizationFailure(Exception):
	'''Raised when an authorization attempt fails'''
	def __init__(self):
		super().__init__('Authorization Failure')
		
class UserNotFound(Exception):
	'''Raised when a user is not found'''
	def __init__(self):
		super().__init__('User not found')

class InvalidModelState(Exception):
	'''Raised when an illegal model state is passed to a database method'''
	def __init__(self, method_name: str, state_violation: str):
		self.message = f'Invalid model state for {method_name}: {state_violation}'
		super().__init__(self.message)

class AccessDenied(Exception):
	'''Raised when a user attempts to access an object they are supposed to'''
	def __init__(self, object_type: str, object_id: str, user_id: str):
		self.message = f'User: {user_id} cannot access {object_type}: {object_id}'
		super().__init__(self.message)
