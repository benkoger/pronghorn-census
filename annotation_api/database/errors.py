# Psycopg3 database abstraction layer errors for crop generator_api
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

class ObjectNotFound(Exception):
	'''Raised when an image UUID does not exist in the database.'''
	def __init__(self, object_type: str, object_id: str):
		self.message = f'{object_type} with ID {object_id} not found.'
		super().__init__(self.message)

class FailedToCreate(Exception):
	'''Raised when an object fails to be created'''
	def __init__(self, object_type: str):
		self.message = f'Failed to create {object_type}'
		super().__init__(self.message)

class AuthenticationFailure(Exception):
	'''Raised when an authentication attempt fails'''
	def __init__(self):
		self.message = 'Username or Password is incorrect'
		super().__init__('Authentication Failure')
		
class UserNotFound(Exception):
	'''Raised when a user is not found'''
	def __init__(self):
		super().__init__('User not found')

class InvalidModelState(Exception):
	'''Raised when an illegal model state is passed to a database method'''
	def __init__(self, method_name: str, state_violation: str):
		self.message = f'Invalid model state for {method_name}: {state_violation}'
		super().__init__(self.message)

class AuthorizationFailure(Exception):
	'''Raised when a user attempts to access an object they are supposed to'''
	def __init__(self, user_id: str, permission: str, object_type: str, object_id: str):
		self.message = f'User: {user_id} does not have permission {permission} for {object_type}: {object_id}'
		super().__init__(self.message)
