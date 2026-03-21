# Psycopg3 database abstraction layer for crop generator_api
# Author: Michael B. Lance

#---------------------------------------------------------------------------------------------------------------------------#

from datetime import date, datetime, timezone
from functools import wraps
import os
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast, Union
from uuid import UUID
import uuid

from authzed.api.v1 import (
	Client,
	ObjectReference,
	Relationship,
	RelationshipUpdate,
	SubjectReference,
	WriteRelationshipsRequest,
	CheckPermissionRequest,
	CheckPermissionResponse
)
from cropgenerator.generatorobjects import (
	Annotation,
	HerdUnit,
	Image,
	Label,
	Model,
	Organization,
	Prediction,
	Project,
	ReviewedArea,
	Role,
	Schema,
	Survey,
	User,
)
from grpc import ChannelCredentials
from psycopg import Cursor
from psycopg.rows import class_row, dict_row
import psycopg.sql as sql
from psycopg_pool import ConnectionPool
from werkzeug.security import generate_password_hash

from .errors import *
from .view_models import *

from .query_builder import QueryBuilder

EXT_KEY = 'base' 

#---------------------------------------------------------------------------------------------------------------------------#

class Database:
	def __init__(self, db_config: Dict[str, str], spice_config: Dict[str, Union[str, ChannelCredentials]]):
		self._config = db_config
		self._pool = None
		self._spice_client = Client(
			cast(str, spice_config['spice_url']),
			cast(ChannelCredentials, spice_config['bearer_token'])
		)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	def init_app(self, app, app_attribute_name='database'):
		'''
		'''
		if not hasattr(app, 'extensions'):
			app.extensions = {}
		app.extensions[EXT_KEY] = self

		setattr(app, app_attribute_name, self)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# 

	def create_pool(self, min_size: int=2, max_size: int=4):
		if self._pool is not None: # dispose of existing pool
			self.close_pool()
			
		self.pool_uuid = uuid.uuid4()
		self._pool = ConnectionPool(
			kwargs = self._config,
			min_size = min_size,
			max_size = max_size,
			open = True,
			max_lifetime = 290,
			check=ConnectionPool.check_connection 
		)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def close_pool(self):
		if self._pool:
			self._pool.close()

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def connect(fn: Callable[..., Any]) -> Callable[..., Any]: #type: ignore
		''' Wrapper function for handling connection context
		
		Args: 
			fn: method of Database class that needs to interact with the database
		'''
		@wraps(fn)
		def wrapper(self, *args, **kwargs):

			has_cursor = 'cursor' in kwargs or (len(args) > 0 and args[0].__class__.__name__ == 'Cursor')
        
			if has_cursor:
				return fn(self, *args, **kwargs)

			if not self._pool:
				self.create_pool()
			with self._pool.connection() as conn:
				with conn.cursor() as cursor:    
					return fn(self, cursor, *args, **kwargs)
		return wrapper

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	
	def _write_spice_relationships(self, updates: List[RelationshipUpdate]):
		'''
		
		'''
		return self._spice_client.WriteRelationships(
			WriteRelationshipsRequest(
				updates=updates
			)
		)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def _create_spice_update(self, object_type: str, object_id: str, subject_type: str, subject_id: str, relation: str) -> RelationshipUpdate:
		'''

		'''
		return RelationshipUpdate(
			operation=RelationshipUpdate.Operation.OPERATION_CREATE,
			relationship=Relationship(
				resource=ObjectReference(object_type=object_type, object_id=object_id),
				relation=relation,
				subject=SubjectReference(
					object=ObjectReference(
						object_type=subject_type,
						object_id=subject_id,
					)
				)
			)
		)
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def _check_permissions(self, object_type: str, object_id: str, subject_type: str, subject_id: str, permission:str):
		'''
		'''
		resp = self._spice_client.CheckPermission(
			CheckPermissionRequest(
				resource=ObjectReference(
					object_type=object_type,
					object_id=object_id
				),
				permission=permission,
				subject=SubjectReference(
					object=ObjectReference(
						object_type=subject_type,
						object_id=subject_id,
					)
				)
			)
		)
		assert resp.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	
	@connect
	def _bootstrap(self, cursor: Cursor) -> bool:
			try:
				with open(os.path.join(os.path.dirname(__file__), 'db_definitions.sql')) as script:
					sql_script = script.read()
					# pyright: ignore[reportArgumentType]
					cursor.execute(sql_script) #type: ignore
			except Exception as e: 
				print(e)
				return False
			finally:
				return True

	def bootstrap(self) -> bool:
		''' Create tables detailed in sql file

		'''
		return self._bootstrap()
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	# Project Management - Organizations
	@connect
	def _create_organization(self, cursor: Cursor[Organization], name: str, logo_url: str | None = None) -> Organization | None:
		''' Internal helper function, do not call directly
		
		''' 
		cursor.row_factory = class_row(Organization)
		cursor.execute(sql.SQL('INSERT INTO usermanagement.organizations (name, logo_url) VALUES (%s, %s) RETURNING *; '), (name, logo_url))
		org = cursor.fetchone()
		return org
	
	def create_organizaztion(self, name: str, logo_url: str | None = None) -> Organization | None:

		return self._create_organization(name = name, logo_url = logo_url)
		

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_organization(self, cursor: Cursor[Organization], organization_id: int | UUID) -> Organization:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Organization)
		query = sql.SQL('SELECT * FROM usermanagement.organizations WHERE {id_field} = %s; ')
		match organization_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('organization_id')), (organization_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (organization_id,))
			case _:
				raise TypeError('organization_ids must be an int, or uuid or a list')
		
		organization = cursor.fetchone()

		if not organization:
			raise ObjectNotFound('organization', organization_id)

		return organization


	def get_organization(self, organization_id: int | UUID) -> Organization:
		''' Request an organization, or organizations object(S) from the database

		Args:
			organization_ids: an integer, uuid, or role name, or a list consisting entirely of one of those 3 types
		'''
		return self._get_organization(organization_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _get_many_organizations(self, cursor: Cursor[Organization], organization_ids: List[Union[int, UUID]]) -> List[Organization]:
		'''

		'''
		cursor.row_factory = class_row(Organization)
		ints = [i for i in organization_ids if isinstance(i, int)]
		uuids = [str(i) for i in organization_ids if not isinstance(i, int)]
		query = sql.SQL('''
			SELECT * FROM usermanagement.organizations
			WHERE organization_id = ANY(%s)
			OR uuid = ANY(%s::uuid[])
			)
		''')

		cursor.execute(query, (ints, uuids))

		return cursor.fetchall()

	def get_many_organizations(self, organization_ids: List[Union[int, UUID]]) -> List[Organization]:
		'''
		'''
		return self._get_many_organizations(organization_ids)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_organization_projects(self, cursor: Cursor[Project], org_id: Union[int, UUID]) -> List[Project]:
		'''

		'''
		query = sql.SQL('''
			SELECT P.* FROM projectmanagement.projects AS P
			JOIN usermanagement.organizations_projects AS OP ON OP.project_id = P.project_id
			WHERE OP.orgnaization_id = %s;
		''')

		org = self._get_organization(cursor, org_id)
		cursor.row_factory = class_row(Project)
		cursor.execute(query, (org.organization_id,))

		return cursor.fetchall()

	def get_organization_projects(self, org_id: Union[int, UUID]) -> List[Project]:
		'''

		'''
		return self._get_organization_projects(org_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _update_organization(self, cursor: Cursor[Organization], orgId: Organization | int | UUID,
							name: str | None = None, logo_url: str | None = None) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(''' UPDATE usermanagement.organizations SET {augmented_field}, modified = CURRENT_TIMESTAMP
							WHERE {id_field} = %s; ''')
		kw_augmented_field = sql.SQL(',').join([sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key)) for key, value in locals().items() if key in set(['name', 'logo_url']) and value is not None])
		match orgId:
			case Organization():
				cursor.execute(query.format(
					augmented_field = sql.SQL(f"name = '{organization_id.name}', logo_url = '{organization_id.logo_url}'"), #type: ignore
					id_field = sql.Identifier('organization_id')
				), (orgId.organization_id,))
			case int():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('organization_id')
				), (orgId,))
			case UUID():
				cursor.execute(query.format(
					kw_augmented_field = kw_augmented_field,
					id_field = sql.Identifier('uuid')
				), (orgId,))
			case _:
				raise TypeError('organization_id must be an Organization, int, uuid, string')
		return True if cursor.rowcount > 0 else False
	
	def update_organization(self,  organization_id: Organization | int | UUID,
							name: str | None = None, logo_url: str | None = None) -> bool:
		''' Augment an organization in the database by providing either a modified Organization object or a valid id and a new name and or a new logo_url
		
		Args:
			organization_id: either an Organization object, a database id, or a universally unique identifier 
			name: the new name for the organization
			logo_url: a url for the organization's logo image
		'''
		return self._update_organization(organization_id = organization_id, name = name, logo_url = logo_url)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _delete_organization(self, cursor: Cursor[Organization], organization_ids: Organization | int | UUID | list[int | UUID]) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(' DELETE FROM usermanagement.organizations WHERE {id_field} = %s; ')
		match organization_ids:
			case list() if isinstance(organization_ids[0], Organization):
				cursor.executemany(query.format(id_field = sql.Identifier('organization_id')), [(cast(Organization, org).organization_id,) for org in organization_ids])
			case list() if isinstance(organization_ids[0], int):
				cursor.executemany(query.format(id_field = sql.Identifier('organization_id')), [(org_id,) for org_id in organization_ids])
			case list() if isinstance(organization_ids[0], UUID):
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), organization_ids)
			case Organization():
				cursor.execute(query.format(id_field = sql.Identifier('organization_id')), (organization_ids.organization_id,))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('organization_id')), (organization_ids,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (organization_ids,))
			case _:
				raise TypeError('organization_ids must be an Organization, int, uuid, string, or a list consisting of ONE of the three')
		return True if cursor.rowcount > 0 else False

	def delete_organization(self, organization_ids: Organization | int | UUID | list[int | UUID]) -> bool:
		''' Delete an organization object from the database
		
		Args:
			organization_id: either an Organization object, a database id, or a universally unique identifier
		'''
		return self._delete_organization(organization_ids = organization_ids)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Project Management - Roles

	@connect
	def _create_role(self, cursor: Cursor[Role], name: str) -> Role | None:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Role)
		cursor.execute(sql.SQL(' INSERT INTO usermanagement.roles (name) VALUES (%s) RETURNING *; '), (name,))
		role = cursor.fetchone()
		return role
	
	def create_role(self, name: str) -> Role:
		''' Insert a new role object into the database

		Args:
			role: The human readable role version
		'''
		return self._create_role(name = name)
		
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_role(self, cursor: Cursor[Role], role_id: int | UUID | str  ) -> Role:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Role)
		query = sql.SQL(' SELECT * FROM usermanagement.roles WHERE {id_field} = %s; ')
		match role_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('role_id')), (role_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (role_id,))
			case str():
				cursor.execute(query.format(id_field = sql.Identifier('name')), (role_id,))

		role = cursor.fetchone() 

		if not role:
			raise ObjectNotFound('Role', role_id)

		return role

	def get_role(self, role_id: int | UUID | str) -> Role:
		''' 

		'''
		return self._get_role(role_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _get_many_roles(self, cursor: Cursor[Role], parameters: GetRoles) -> List[Role]:
		'''

		'''
		cursor.row_factory = class_row(Role)
	
		query = sql.SQL('''
			SELECT * FROM usermanagement.roles
			WHERE  role_id = ANY(%s)
				OR uuid = ANY(%s::uuid[])
		''')

		model = parameters.model_dump()
	
		query += sql.SQL('''
			
		''')

		ints = [i for i in model['role_id'] if isinstance(i, int)]
		uuids = [str(i) for i in model['role_id'] if not isinstance(i, int)]
	
		return cursor.execute(query, (ints, uuids)).fetchall()

	def get_many_roles(self, parameters: GetRoles) -> List[Role]:
		'''

		'''
		return self._get_many_roles(parameters)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	
	@connect
	def _update_role(self, cursor: Cursor[Role], role_id: Role | int | UUID | str, name: str | None = None) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(''' UPDATE usermanagement.roles SET name = %s, modified = CURRENT_TIMESTAMP
							WHERE {id_field} = %s; ''')
		match role_id:
			case Role():
				cursor.execute(query.format(id_field = sql.Identifier('role_id')), (role_id.name, role_id.role_id))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('role_id')), (name, role_id))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (name, role_id))
			case str():
				cursor.execute(query.format(id_field = sql.Identifier('name')), (name, role_id))
			case _:
				raise TypeError('role_id must be a Role, int, uuid, string, or a list consisting of ONE of the three')
		return True if cursor.rowcount > 0 else False
	
	def update_role(self, role_id: Role | int | UUID, name: str | None = None) -> Role:
		return self._update_role(role_id = role_id, name = name)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _delete_role(self, cursor: Cursor[Role], role_ids: int | UUID | str) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(' DELETE FROM usermanagement.roles WHERE {id_field} = %s; ') 
		match role_ids:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('role_id')), (role_ids,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (role_ids,))
			case str():
				cursor.execute(query.format(id_field = sql.Identifier('role')), (role_ids,))
			case _:
				raise TypeError('role_id must be a Role, int, uuid, string, or a list consisting of ONE of the three')
		return True if cursor.rowcount > 0 else False
	
	def delete_role(self, role_ids: Role | int | UUID) -> bool:
		''' Delete a role object from the database
		
		Args:
			role_id: either a Role object, a database id, or a universally unique identifier
		
		'''
		return self._delete_role(role_ids = role_ids)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# User Management - Users

	@connect
	def _create_user(self, cursor: Cursor[User], parameters: CreateUser ) -> User:
		''' Internal helper function, do not call directly
		
		'''  
		query_1 = sql.SQL('''
			INSERT INTO usermanagement.users (
				username, email, external_auth_id, external_auth_provider,
				status, locale, passowrd_hash
			)
			VALUES (
				%(username)s, %(email)s, %(external_auth_id)s, %(external_auth_provider)s, 
				%(status)s, %(locale)s, %(password_hash)s
			)
			RETURNING *;
		''')

		query_2 = sql.SQL('''
			INSERT INTO projectmanagement.projects_users (
				project_id, user_id
			)
			VALUES (
				%s, %s
			)
		''')
		query_3 = sql.SQL('''
			INSERT INTO usermanagement.organizations_users (
				user_id, organziation_id, role_id
			)
			VALUES (
				%s, %s, %s
			)
		''')

		placeholders = parameters.model_dump()

		placeholders['password_hash'] = generate_password_hash(
			placeholders['password']
		)

		cursor.row_factory = class_row(User)
		cursor.execute(query_1, parameters.model_dump())

		user = cursor.fetchone()

		if not user:
			raise FailedToCreate('user')

		projects = self._get_projects(cursor, parameters.project_ids)

		cursor.executemany(query_2, [(user.user_id, proj.project_id) for proj in projects])

		# Organizations and Ids should be equal length and appear in the same order
		orgs = self._get_many_organizations(cursor, parameters.organization_ids)
		roles = self._get_many_roles(cursor, GetRoles(role_id=parameters.role_ids))
		
		if len(roles) != len(orgs):
			raise InvalidModelState('create_user', 'Number of roles and nubmer of organizations must be equal.')

		cursor.executemany(query_3, [(user.user_id, org.organization_id, role.role_id) for org, role in zip(orgs, roles)])

		return user

	def create_user(self, parameters: CreateUser) -> User:
		''' 

		'''
		return self._create_user(parameters)
		
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_user(self, cursor: Cursor[User], user_id: int | UUID | str ) -> User:
		''' Internal helper function, do not call directly
		
		'''  
		cursor.row_factory = class_row(User)
		query = sql.SQL('''
			SELECT U.*, R.name as roles, O.uuid as orgs FROM usermanagement.users AS U 
			JOIN usermanagement.organizations_users AS OU ON OU.user_id = U.user_id
			JOIN usermanagement.roles AS R ON R.role_id = OU.role_id
			JOIN usermanagement.organizations O on O.organization_id = OU.organization_id
			
			WHERE U.{id_field} = %s
		''')
		match user_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('user_id')), (user_id,))
			case str():
				cursor.execute(query.format(id_field = sql.Identifier('email')), (user_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (user_id,))

		user = cursor.fetchone()
		if not user:
			raise UserNotFound

		return user
		
	def get_user(self, user_id: int | UUID | str ) -> User:
		''' Query the database for a user
		
		Args:
			user_id: The user's unique database id 
		'''
		return self._get_user(user_id = user_id)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	#TODO: Users should be queried by organization
	@connect
	def _get_users(self, cursor: Cursor[User]) -> List[User]:
		'''

		'''
		cursor.row_factory = class_row(User)
		query = sql.SQL('SELECT * FROM usermanagement.users WHERE user_id != 0;')

		return cursor.execute(query).fetchall()

	def get_users(self):
		return self._get_users()

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_user_roles(self, cursor: Cursor[Role], user_id: int | UUID) -> list[Role] | None:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Role)
		query = sql.SQL(''' 
			SELECT R.* FROM usermanagement.roles AS R JOIN usermanagement.organizations_users AS OU 
			ON OU.role_id = R.role_id WHERE OU.user_id = %s; ''')
		match user_id:
			case int():
				cursor.execute(query, (user_id,))
			case _:
				user = self._get_user(user_id)
				cursor.execute(query, (user.user_id,))
		roles = cursor.fetchall()
		return roles

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	def get_user_roles(self, user_id: User| int | UUID) -> list[Role] | Role | None:
		''' Request all roles associated with a user 

		Args:
			user_id: The user's unique database id 
		'''
		return self._get_user_roles(user_id = user_id)

	@connect
	def _get_user_organizations(self, cursor: Cursor[Organization], user_id: int | UUID) -> list[Organization]:
		'''
		
		'''
		query = sql.SQL('''
			SELECT O.* FROM usermanagement.organizations AS O
			JOIN usermanagement.organizations_users AS OU ON OU.organization_id = O.organization_id
			WHERE OU.user_id = %s; 
		''')
		match user_id:
			case int():
				cursor.execute(query, (user_id,))
			case _:
				user = self._get_user(cursor, user_id)
				cursor.execute(query, (user.user_id,))

		cursor.row_factory = class_row(Organization)
		return cursor.fetchall()
	
	def get_user_organizations(self, user_id: int | UUID) -> list[Organization]:
		'''
		
		'''
		return self._get_user_organizations(user_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#		

	@connect 
	def _activate_user(self, cursor: Cursor, email: str, user_id: int | UUID, external_id: str, provider: str) -> None:
		'''

		'''
		if isinstance(user_id, UUID):
			user_id = self._get_user(cursor, user_id).user_id

		self._update_user(cursor, user_id, {
			'status': 'active',
			'email': email,
			'external_auth_id': external_id,
			'external_auth_provider': provider,
			'last_login': datetime.now(timezone.utc)
		})

		return

	def activate_user(self, email: str, user_id: int | UUID, external_id: str, provider: str) -> None:
		'''
		
		'''
		return self._activate_user(email, user_id, external_id, provider)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _login_user(self, cursor: Cursor[User], user_id: int | UUID) -> None:
		''' Internal helper function, do not call directly
		
		'''

		self._update_user(cursor, user_id, {'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S%z')})
	
	def login_user(self, user_id: int | UUID) -> None:
		''' 

		'''
		return self._login_user(user_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _update_user(self, cursor: Cursor[User], user_id: int | UUID, parameters: dict) -> User:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(User)
		query = sql.SQL(''' 
			UPDATE usermanagement.users SET {augmented_field}, modified = CURRENT_TIMESTAMP 
			WHERE {id_field} = %s
			RETURNING *; 
		''')
		kw_augmented_field = sql.SQL(',').join(
			[
				sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
				for key, value in parameters.items() 
				if key in set([
					'username', 'external_auth_id', 'external_auth_provider', 
					'status', 'locale', 'last_login', 'email', 'password_hash'
				]) 
				and value is not None
			]
		)
		match user_id:
			case int():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('user_id')
				), (user_id,))
			case UUID():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('uuid')
				), (user_id,))
		
		user = cursor.fetchone()

		if not user:
			raise UserNotFound
		
		return user

	
	def update_user(self, user_id: int | UUID, parameters: dict) -> bool:
		''' 

		'''
		return self._update_user(user_id, parameters)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _delete_user(self, cursor: Cursor[User], user_ids: User | int | UUID |list[User | int | UUID]) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(' DELETE FROM usermanagement.users WHERE {id_field} = %s')
		match user_ids:
			case list() if isinstance(user_ids[0], User):
				cursor.executemany(query.format(id_field = sql.Identifier('user_id')), [(cast(User, user).user_id,) for user in (user_ids)])
			case list() if isinstance(user_ids[0], int):
				cursor.executemany(query.format(id_field = sql.Identifier('user_id')), [(user_id,) for user_id in user_ids])
			case list() if isinstance(user_ids[0], UUID):
				cursor.executemany(query.format(id_field = sql.Identifier('uuid')), [(user_id,) for user_id in user_ids])
			case User():
				cursor.execute(query.format(id_field = sql.Identifier('user_id')), (user_ids.user_id,))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('user_id')), (user_ids,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (user_ids,))
			case _:
				raise TypeError('user_ids must be a User, int, uuid, , or a list consisting of ONE of the two')
		return True if cursor.rowcount > 0 else False

	def delete_user(self, user_ids: User | int | UUID) -> bool:
		''' Delete a user object from the database
		
		Args:
			user_ids: either a user object, a database id, or a universally unique identifier or a list consisting of ONE of the two
		'''
		return self._delete_user(user_ids = user_ids)
		
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	# Project Management - Projects
	@connect
	def _create_project(self, cursor: Cursor[Project], name: str, ) -> Project:
		''' Internal helper function, do not call directly
		
		'''   
		cursor.row_factory = class_row(Project)        
		cursor.execute(sql.SQL(' INSERT INTO projectmanagement.projects (name) VALUES (%s) RETURNING *; '), (name,))
		project = cursor.fetchone()
		if project is None:
			raise Exception('Failed to create project')
		return project 
	
	def create_project(self, name:str) -> Project:
		''' Insert a new project object into the database

		Args:
			name: The name of the project you want to create
		'''
		return self._create_project(name = name)
		

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# 

	@connect
	def _get_project(self, cursor: Cursor[Project], project_id: int | UUID) -> Project:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Project)
		query = sql.SQL(' SELECT * FROM projectmanagement.projects WHERE {id_field} = %s ')
		match project_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('project_id')), (project_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (project_id,))
			case _:
				raise TypeError('project_id MUST be an integer or a UUID')
		
		project = cursor.fetchone()
		if not project:
			raise ObjectNotFound('Project', project_id)

		return project 
	
		
	def get_project(self, project_id: int | UUID) -> Project:
		''' Query the database for a project 
		
		Args:
			project_id: either the project's internal database id or its universally unique identifier
		'''
		return self._get_project(project_id=project_id)
		
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	
	@connect 
	def _get_projects(self, cursor: Cursor[Project], project_ids: List[Union[int, UUID]]) -> List[Project]:
		'''

		'''
		cursor.row_factory = class_row(Project)
		ints = [i for i in project_ids if isinstance(i, int)]
		uuids = [str(i) for i in project_ids if not isinstance(i, int)]
		query = sql.SQL('''
			SELECT * FROM projectmanagement.projects
			WHERE project_id = ANY(%s)
			OR uuid = ANY(%s::uuid[])
			)
		''')

		cursor.execute(query, (ints, uuids))

		return cursor.fetchall()

	def get_projects(self, project_ids: List[Union[int, UUID]]) -> List[Project]:
		'''
		'''
		return self._get_projects(project_ids)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_project_models(self, cursor: Cursor[Model], project_id: int | UUID) -> List[Model]:
		'''
		
		'''
		project = self._get_project(cursor, project_id)
		query = sql.SQL(''' 
			SELECT m.* FROM projectmanagement.models M
			JOIN projectmanagement.projects_models PM ON PM.model_id = M.model_id
			WHERE PM.project_id = %s; 
		''') 

		cursor.row_factory = class_row(Model)
		cursor.execute(query, (project.project_id,))

		return cursor.fetchall()
	
	def get_project_models(self, project_id: Project | int | UUID) -> List[Model]:
		'''
		
		'''
		return self._get_project_models(project_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _get_project_herd_units(self, cursor: Cursor[HerdUnit], project_id: int | UUID) -> list[HerdUnit]:
		'''
		
		'''
		project = self._get_project(cursor, project_id)
		query = sql.SQL('''
			SELECT HU.* FROM projectmanagement.herd_units HU JOIN
			projectmanagement.projects_herd_units PHU ON PHU.herd_unit_id = HU.herd_unit_id
			WHERE PHU.project_id = %s; 
		''')

		cursor.row_factory = class_row(HerdUnit)
		cursor.execute(query, (project.project_id,))
		
		return cursor.fetchall()

	def get_project_herd_units(self, project_id: Project | int | UUID) -> list[HerdUnit]:
		'''
		
		'''
		return self._get_project_herd_units(project_id)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _update_project(self, cursor: Cursor[Project], project_id: Project | int | UUID, name: str | None = None) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(' UPDATE projectmanagement.projects SET name = %s, modified = CURRENT_TIMESTAMP WHERE {id_field} = %s; ')
		match project_id:
			case Project():
				cursor.execute(query.format(id_field = sql.Identifier('project_id')), (project_id.name, project_id.project_id))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('project_id')), (name, project_id))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (name, project_id))
			case _:
				raise TypeError('project_id MUST be an integer, UUID or Project type, and name must be a string')
		return True if cursor.rowcount > 0 else False

	def update_project(self, project_id: Project | int | UUID, name: str | None=None) -> bool:
		''' Augment a project in the database by providing either a modified Project object or a valid id and a new name
		
		Args:
			project_id: either a project object, a database id, or a universally unique identifier 
			name: the new name for the project
		'''
		return self._update_project(project_id=project_id, name=name)


	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	
	@connect
	def _delete_project(self, cursor: Cursor[Project], project_id: Project | int | UUID) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(' DELETE FROM projectmanagement.projects WHERE {id_field} = %s; ')
		match project_id:
			case Project():
				cursor.execute(query.format(id_field = sql.Identifier('project_id')), (project_id.project_id,))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('project_id')), (project_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (project_id,))
			case _:
				raise TypeError('project_id MUST be an integer, UUID or Project type')
		return True if cursor.rowcount > 0 else False    

	def delete_project(self, project_id: Project | int | UUID) -> bool:
		''' Delete a project object from the database
		
		Args:
			project_id: either a project object, a database id, or a universally unique identifier
		'''
		return self._delete_project(project_id = project_id)
		
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Project Management - Schemas

	@connect
	def _create_schema(self, cursor: Cursor[Schema], name: str) -> Schema | None:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Schema)
		cursor.execute(sql.SQL(' INSERT INTO projectmanagement.schemas (name) VALUES (%s) RETURNING *; '), (name,))
		schema = cursor.fetchone()
		return schema if isinstance(schema, Schema) else None

	def create_schema(self, name: str) -> Schema | None:
		''' Insert a new schema object into the database

		Args:
			name: the schema name 
		'''
		return self._create_schema(name=name)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	
	@connect 
	def _get_schema(self, cursor: Cursor[Schema], schema_id: int | UUID) -> Schema:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Schema)
		query = sql.SQL('  SELECT * FROM projectmanagement.schemas WHERE {id_field} = %s ')
		match schema_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('schema_id')), (schema_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (schema_id,))
			case _:
				raise TypeError('schema_id MUST be an integer or a UUID')
		schema = cursor.fetchone()
		if not schema:
			raise ObjectNotFound('Schema', schema_id)

		return schema 

	def get_schema(self, schema_id: int | UUID) -> Schema:
		''' Query the database for a schema 
		
		Args:
			schema_id: either the schema's internal database id or its universally unique identifier
		'''
		return self._get_schema(schema_id)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_schema_labels(self, cursor: Cursor[Label], schema_id: int | UUID) -> list[Label]:
		'''
		
		'''
		schema = self._get_schema(cursor, schema_id)
		query = sql.SQL(' SELECT * FROM projectmanagement.labels WHERE schema_id = %s; ')
		
		
		cursor.row_factory = class_row(Label)
		cursor.execute(query, (schema.schema_id,))
		labels = cursor.fetchall() 
		if len(labels) == 0:
			raise ObjectNotFound('labels for schema', schema_id)
		return labels 

	def get_schema_labels(self, schema_id: Project | int | UUID) -> list[Label]:
		'''
		
		'''
		return self._get_schema_labels(schema_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _update_schema(self, cursor: Cursor[Schema], schema_id: Schema | int | UUID, name: str | None = None) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(' UPDATE projectmanagement.schemas SET name =%s, modified = CURRENT_TIMESTAMP WHERE {id_field} = %s; ')
		match schema_id:
			case Schema():
				cursor.execute(query.format(id_field = sql.Identifier('shcema_id')), (schema_id.name, schema_id.schema_id))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('schema_id')), (name, schema_id))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (name, schema_id))
			case _:
				raise TypeError('schema_id MUST be an integer, UUID or Project type, and name must be a string')
		return True if cursor.rowcount > 0 else False

	def update_schema(self, schema_id: Schema | int | UUID, name: str):
		''' Augment a schema in the database by providing a modified Project object
		
		Args:
			schema: A schema object
		'''
		return self._update_schema(schema_id=schema_id, name=name)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	
	@connect
	def _delete_schema(self, cursor: Cursor[Schema], schema_id: Schema | int | UUID) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(' DELETE FROM projectmanagement.schemas WHERE {id_field} = %s; ')
		match schema_id:
			case Schema():
				cursor.execute(query.format(id_field = sql.Identifier('schema_id')), (schema_id.schema_id,))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('schema_id')), (schema_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (schema_id,))
			case _:
				raise TypeError('schema_id MUST be an integer, UUID or Project type')
		return True if cursor.rowcount > 0 else False 
	
	def delete_schema(self, schema_id: Schema | int | UUID):
		''' Delete a scehma object from the database
		
		Args:
			schema: A schema object
		'''
		return self._delete_schema(schema_id=schema_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	# Project Management - labels
	@connect 
	def _create_label(self, cursor: Cursor[Label], name: str, label: int, color: str | None = None, image_link: str | None = None) -> Label | None:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Label)
		cursor.execute(sql.SQL(' INSERT INTO projectmanagement.labels (name, label, color, image_link) VALUES (%s, %s, %s) RETURNING *; '), (name, label, color, image_link))
		lbl = cursor.fetchone()
		return  lbl if isinstance(lbl, Label) else None 
	
	def create_label(self, name: str, label: int, image_link: str) -> Label | None:
		''' Insert a new label object into the database

		Args:
			name: The name of the label you want to create
			label: the integer value associated to the class being labeled
			image_link: optional parameter for the generator to grab an image representing the class
		'''
		return self._create_label(name=name, label=label, image_link=image_link)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_label(self, cursor: Cursor[Label], label_ids: int | UUID) -> Label:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Label)
		query = sql.SQL(' SELECT * FROM projectmanagement.labels WHERE {id_field} = %s; ')
		match label_ids:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('label_id')), (label_ids,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (label_ids,))
			case _:
				raise TypeError('label_id MUST be an integer or a UUID')

		label = cursor.fetchone()
		if label is None:
			raise Exception('Labels not found')
		return label
	
	def get_label(self, label_id: int | UUID):
		''' Query the database for a label  
		
		Args:
			label_id: either the label's internal database id or its universally unique identifier
		'''
		return self._get_label(label_id=label_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _update_label(self, cursor: Cursor[Label], label_id: Label | int | UUID, name: str | None = None, 
					label: int | None = None, color: str | None = None, image_link: str | None = None) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(''' UPDATE projectmanagement.labels SET {augmented_field}, modified = CURRENT_TIMESTAMP  
							WHERE {id_field} = %s; ''')
		kw_augmented_field = sql.SQL(',').join([sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key)) for key, value in locals().items() if key in set(['name', 'label,' 'image_link', 'color']) and value is not None])
		match label_id:
			case Label():
				cursor.execute(query.format(
					augmented_field = sql.SQL(f"label = '{label_id.label}', name = '{label_id.name}', color = '{label_id.color}', image_link = '{label_id.image_link}'"), #type: ignore
					id_field = sql.Identifier('label_id')
				), (label_id.label_id,))
			case int():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('label_id')
				), (label_id,))
			case UUID():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('uuid')
				), (label_id,))
			case _:
				raise TypeError('label_id must be a Label, int, or UUID')
		return True if cursor.rowcount > 0 else False
			
	def update_label(self, label_id: Label | int | UUID, name: str | None = None, 
					  label: int | None = None, image_link: str | None = None, **kwargs) -> bool:
		''' Augment a label in the database by providing a modified Label object or a valid id and a new name, and or label, and or image_link
		
		Args:
			label_id: either a Label object, a database id, or a universally unique identifier 
			label: the integer value representing the label in models
			name: the new name for the label
			image_link: a link to an example image of the object the label represents
		'''
		return self._update_label(label_id=label_id, name=name, label=label, image_link=image_link)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _delete_label(self, cursor: Cursor[Label], label_ids: Label | int | UUID | list[int | UUID | str]) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(' DELETE FROM projectmanagement.labels WHERE {id_field} = %s; ')
		match label_ids:
			case list() if isinstance(label_ids[0], Label):
				cursor.executemany(query.format(id_field = sql.Identifier('label_id')), [(cast(Label, label).label_id,) for label in label_ids])
			case list() if isinstance(label_ids[0], int):
				cursor.executemany(query.format(id_field = sql.Identifier('label_id')), [(label_id,) for label_id in label_ids])
			case list() if isinstance(label_ids[0], UUID):
				cursor.executemany(query.format(id_field = sql.Identifier('uuid')), [(label_id,) for label_id in label_ids])
			case Label():
				cursor.execute(query.format(id_field = sql.Identifier('label_id')), (label_ids.label_id,))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('label_id')), (label_ids,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (label_ids,))
			case _:
				raise TypeError('label_id must be a Label, int, uuid, string')
		return True if cursor.rowcount > 0 else False
	
	def delete_label(self, label_ids: Label | int | UUID) -> bool:
		''' Delete a label object from the database
		
		Args:
			label: either a label object, a database id, or a universally unique identifier 
		'''

		return self._delete_label(label_ids = label_ids)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Project Management - Herd Units

	@connect
	def _create_herd_unit(self, cursor: Cursor[HerdUnit], parameters: dict) -> HerdUnit:
		''' Internal helper function, do not call directly
		
		'''
		
		project = self._get_project(cursor, parameters['project_id'])

		if not project:
			raise Exception('Project not found')

		query_1 = sql.SQL('''
			INSERT INTO projectmanagement.herd_units (
				name
			) 
			VALUES (
				%(name)s
			)
			RETURNING *; ''')
		
		cursor.row_factory = class_row(HerdUnit)
		cursor.execute(query_1, parameters)

		herd_unit = cursor.fetchone()
		if not herd_unit:
			raise Exception('Failed to create herd unit')

		query_2 = sql.SQL('''
			INSERT INTO projectmanagement.projects_herd_units (
				project_id, herd_unit_id 
			)
			VALUES (
				%s, %s
			);
		''')

		cursor.execute(query_2, (project.project_id, herd_unit.herd_unit_id))

		return herd_unit

	def create_herd_unit(self, parameters: dict) -> HerdUnit:
		''' Insert a new herd unit object into the database

		Args:
			name: the herd unit name 
		'''
		return self._create_herd_unit(parameters)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_herd_unit(self, cursor: Cursor[HerdUnit], herd_unit_id: int | UUID) -> HerdUnit:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(HerdUnit)
		query = sql.SQL(' SELECT * FROM projectmanagement.herd_units WHERE {id_field} = %s; ')
		match herd_unit_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('herd_unit_id')), (herd_unit_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (herd_unit_id,))
			case _:
				raise TypeError('herd_unit_id MUST be an integer or a UUID')
		herd_unit = cursor.fetchone()

		if not herd_unit:
			raise Exception('Herd Unit was not found')

		return herd_unit
	
	def get_herd_unit(self, herd_unit_id: int | UUID) -> HerdUnit:
		''' Query the database for a herd unit 

			Args:
			herd_unit_id: either the herd unit's internal database id or its universally unique identifier
		'''
		return self._get_herd_unit(herd_unit_id=herd_unit_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_herd_unit_surveys(self, cursor: Cursor[Survey], herd_unit_id: int | UUID) -> list[Survey]:
		'''
		
		'''
		herd_unit = self._get_herd_unit(herd_unit_id)

		cursor.row_factory = class_row(Survey)
		query = sql.SQL('''
			SELECT S.* FROM projectmanagement.surveys as S JOIN
			projectmanagement.surveys_herd_units AS SHU ON SHU.survey_id = S.survey_id
			WHERE SHU.herd_unit_id = %s; ''')
		cursor.execute(query, (herd_unit.herd_unit_id,))
		surveys = cursor.fetchall()
		if len(surveys) == 0:
			raise ObjectNotFound('Surveys for herd unit', herd_unit_id) 

		return surveys

	def get_herd_unit_surveys(self, survey_id: int | UUID) -> list[Survey]:
		'''
		
		'''
		return self._get_herd_unit_surveys(survey_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _update_herd_unit(self, cursor: Cursor[HerdUnit], herd_unit_id: HerdUnit | int | UUID, name: str | None = None) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(''' UPDATE projectmanagement.herd_units SET name = %s, modified = CURRENT_TIMESTAMP
							WHERE {id_field} = %s; ''')
		match herd_unit_id:
			case HerdUnit():
				cursor.execute(query.format(id_field = sql.Identifier('herd_unit_id')), (herd_unit_id.name, herd_unit_id.herd_unit_id))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('herd_unit_id')), (name, herd_unit_id))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (name, herd_unit_id))
			case _:
				raise TypeError('herd_unit MUST be an integer, UUID or Herd_Unit type, and name must be a string')
		return True if cursor.rowcount > 0 else False

	def update_herd_unit(self, herd_unit_id: HerdUnit | int | UUID, name: str | None = None) -> bool:
		''' Augment a herd unit in the database by providing a modified HerdUnit object or a valid id and a new name
		
		Args:
			herd_unit_id: either a HerdUnit object, a database id, or a universally unique identifier 
			name: the new name for the herd unit
		'''
		return self._update_herd_unit(herd_unit_id = herd_unit_id, name=name)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _delete_herd_unit(self, cursor: Cursor[HerdUnit], herd_unit_ids: HerdUnit | int | UUID) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(' DELETE FROM projectmanagement.herd_units WHERE {id_field} = %s; ')
		match herd_unit_ids:
			case list() if isinstance(herd_unit_ids[0], HerdUnit):
				cursor.executemany(query.format(id_field = sql.Identifier('herd_unit_id')), [(herd_unit.herd_unit_id,) for herd_unit in herd_unit_ids])
			case list() if isinstance(herd_unit_ids[0], int):
				cursor.executemany(query.format(id_field = sql.Identifier('herd_unit_id')), [(hu_id,) for hu_id in herd_unit_ids])
			case list() if isinstance(herd_unit_ids[0], UUID):
				cursor.executemany(query.format(id_field = sql.Identifier('uuid')), [(hu_id,) for hu_id in herd_unit_ids])
			case HerdUnit():
				cursor.execute(query.format(id_field = sql.Identifier('herd_unit_id')), (herd_unit_ids.herd_unit_id,))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('herd_unit_id')), (herd_unit_ids,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (herd_unit_ids,))
			case _:
				raise TypeError('herd_unit_id must be a Label, int, uuid, string')
		return True if cursor.rowcount > 0 else False

	def delete_herd_unit(self, herd_unit_ids: HerdUnit | int | UUID) -> bool:
		''' Delete a herd unit object from the database
		
		Args:
			herd_unit_id: either a herd unit object, a database id, or a universally unique identifier
		'''
		return self._delete_herd_unit(herd_unit_ids = herd_unit_ids)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Project Management - Models
	
	@connect
	def _create_model(self, cursor: Cursor[Model], parameters: dict) -> Model:
		''' Internal helper function, do not call directly
		
		'''
		project = self._get_project(cursor, parameters['project_id'])
		schema = self._get_schema(cursor, parameters['schema_id'])

		# TODO: create method to get list of surveys
		survey_ids = [
			survey_id if isinstance(survey_id, int) else UUID(survey_id)
			for survey_id in parameters['survey_ids']
		]


		if not schema:
			raise Exception('Schema not found')
		if len(survey_ids) == 0:
			raise Exception('no surveys were found')

		query_1 = sql.SQL(''' 
			INSERT into projectmanagement.models (
				name, schema_id
			)
			VALUES (
				%(name)s, %(schema_id)s
			)
			RETURNING *; 
		''')
		
		cursor.execute(query_1, parameters)
		cursor.row_factory=class_row(Model)
		model = cursor.fetchone()
		if not model:
			raise Exception('Failed to create model')

		query_2 = sql.SQL(''' 
			INSERT INTO projectmanagement.projects_models (
				project_id, model_id
			) 
			VALUES (
				%s, %s
			); 
		''')

		cursor.execute(query_2, (project.project_id, model.model_id))

		query_3 = sql.SQL('''
			INSERT INTO projectmanagement.surveys_models (
				survey_id, model_id
			)
			VALUES (
				%s, %s	
			);
		''')

		cursor.executemany(query_3, [(survey_id, model.model_id) for survey_id in survey_ids])

		return model 

	def create_model(self, parameters: dict) -> Model:
		''' Insert a new model object into the database

		Args:
			name: the model name 
		'''
		return self._create_model(parameters)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _get_model(self, cursor: Cursor[Model], model_id: int | UUID) -> Model:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Model)
		query = sql.SQL(' SELECT * FROM projectmanagement.models WHERE {id_field} = %s; ')
		match model_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('model_id')), (model_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (model_id,))
			case _:
				raise TypeError('model_id MUST be an integer or a UUID')
		model = cursor.fetchone()
		if not model:
			raise ObjectNotFound('Model', model_id)

		return model 
	
	def get_model(self, model_id: int | UUID) -> Model:
		''' Query the database for a model
		
		Args:
			model_id: either the models's internal database id or its universally unique identifier
		'''
		return self._get_model(model_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_model_schema(self, cursor: Cursor[Schema], model_id: int | UUID) -> Schema:
		'''
		'''
		model = self._get_model(model_id)
		
		cursor.row_factory = class_row(Schema)
		query = sql.SQL(' SELECT * FROM projectmanagement.schemas WHERE schema_id = %s; ')
		cursor.execute(query, (model.schema_id,))

		schema = cursor.fetchone()
		if not schema:
			raise ObjectNotFound('Schema for model', model_id)
		
		return schema

	def get_model_schema(self, model_id: int | UUID) -> Schema:
		'''
		'''
		return self._get_model_schema(model_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _update_model(self, cursor: Cursor[Model], model_id: int | UUID, parameters: dict) -> Model:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Model)
		query = sql.SQL(''' UPDATE projectmanagement.models SET {augmented_field}, modified = CURRENT_TIMESTAMP 
							WHERE {id_field} = %s RETURNING *; ''')
		kw_augmented_field = sql.SQL(',').join(
			[
				sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
				for key, value, in parameters.items() 
				if key in set(['survey_id', 'survey_date', 'name', 'additional_info'])
				and value is not None
			]
		) 
		match model_id:
			case int():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('model_id')
				), (model_id,)
						)
			case UUID():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('uuid')
				), (model_id,))
			case _:
				raise TypeError('model_id MUST be an integer, or UUID')
		
		model = cursor.fetchone()

		if model:
			return model 
		else:
			raise Exception('failed to update the model')
	
	def update_model(self, model_id: int | UUID, parameters: dict) -> Model:
		''' Augment a model in the database by providing a modified Model object or a valid id and a new name
		
		Args:
			model: either a Model object, a database id, or a universally unique identifier 
			name: the new name for the model
		'''
		return self._update_model(model_id, parameters)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _delete_model(self, cursor: Cursor[Model], model_ids: Model | int | UUID) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(' DELETE FROM projectmanagement.models WHERE {id_field} = %s; ')
		match model_ids:
			case list() if isinstance(model_ids[0], HerdUnit):
				cursor.executemany(query.format(id_field = sql.Identifier('model_id')), [(model.model_id,) for model in herd_unit_ids])
			case list() if isinstance(model_ids[0], int):
				cursor.executemany(query.format(id_field = sql.Identifier('model_id')), [(model_id,) for model_id in model_ids])
			case list() if isinstance(model_ids[0], UUID):
				cursor.executemany(query.format(id_field = sql.Identifier('uuid')), [(model_id,) for model_id in model_ids])
			case Model():
				cursor.execute(query.format(id_field = sql.Identifier('model_id')), (model_ids.model_id,))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('model_id')), (model_ids,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (model_ids,))
			case _:
				raise TypeError('model_id must be a Label, int, or uuid')
		return True if cursor.rowcount > 0 else False


	def delete_model(self, model_ids: Model | int | UUID) -> bool:
		''' Delete a model object from the database
		
		Args:
			model_id: either a model object, a database id, or a universally unique identifier
		'''
		return self._delete_model(model_ids = model_ids)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_model_training_data(
			self, 
			cursor: Cursor[dict],
			label_ids: List[int],
			date_range: Tuple[date, date] | None,
			survey_ids: List[int] | None,
			herd_unit_ids: List[int] | None
		):
		'''
		'''
		cursor.row_factory = dict_row

		params_1 = []
		placeholders: Dict[str, Union[List[int], date]] = {
			'label_ids': label_ids
		}

		if survey_ids:
			params_1.append(sql.SQL('i.survey_id = ANY(%(survey_ids)s)'))
			placeholders['survey_ids'] = survey_ids

		if herd_unit_ids:
			params_1.append(sql.SQL('i.herd_unit_id = ANY(%(herd_unit_ids)s)'))
			placeholders['herd_unit_ids'] = herd_unit_ids

		if date_range:
			params_1.append(sql.SQL('i.created BETWEEN %(date_range_lower)s AND %(date_range_upper)s'))
			placeholders['date_range_lower'] = date_range[0]
			placeholders['date_range_upper'] = date_range[1]

		image_params = sql.SQL(' AND ').join(params_1)

		query = sql.SQL('''
			WITH SelectedImageIds AS (
				SELECT DISTINCT i.image_id 
				FROM core.images i
				WHERE {image_args}
			)
			SELECT json_agg(row_to_json(crops)) 
			FROM (
				SELECT
					ra.reviewed_area_id,
					ra.image_id,
					ra.name, 
					ra.ra_key,
					ra.area_tx,
					ra.area_ty,
					ra.area_bx,
					ra.area_by,
					ra.reviewed_area_length_px,
					ra.reviewed_area_width_px,
					ra.reviewed_by_user_id,
					ra.created,
					ra.modified,
					ra.uuid,
					json_agg(
						json_build_object( 
							'annotation_id', a.annotation_id,
							'label_id', a.label_id,
							'image_id', a.image_id,
							'pred_id', a.pred_id,
							'herd_unit_id', a.herd_unit_id,
							'box_tx', a.box_tx,
							'box_ty', a.box_ty,
							'box_bx', a.box_bx,
							'box_by', a.box_by,
							'created_by_user_id', a.created_by_user_id,
							'created', a.created,
							'modified', a.modified, 
							'uuid', a.uuid
						)
					) AS annotations
				FROM core.reviewed_area ra
				INNER JOIN core.annotations_reviewed_area a_ra ON ra.reviewed_area_id = a_ra.reviewed_area_id
				INNER JOIN core.annotations a ON a.annotation_id = a_ra.annotation_id
				WHERE ra.image_id IN (SELECT image_id FROM SelectedImageIds)
					AND a.label_id =  ANY(%(label_ids)s)
				GROUP BY ra.reviewed_area_id
			) AS crops
		''')
		
		try:
			cursor.execute(query.format(image_args = image_params), placeholders)
		except Exception as e:
			print(e)
		results = cursor.fetchone()

		return results

	def get_model_training_data(
		self,
		label_ids: List[int],
		date_range: Tuple[date, date] | None,
		survey_ids: List[int] | None,
		herd_unit_ids: List[int] | None
	):
		'''
		'''
		return self._get_model_training_data(
			label_ids,
			date_range,
			survey_ids,
			herd_unit_ids
		)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Project Management - Surveys

	@connect
	def _create_survey(self, cursor: Cursor[Survey], parameters: dict) -> Survey:
		''' Internal helper function, do not call directly
		
		'''

		project = self._get_project(cursor, parameters['project_id'])
		
		# TODO: create method to get list of herd units
		herd_unit_ids = [
			herd_unit_id if isinstance(herd_unit_id, int) else UUID(herd_unit_id)
			for herd_unit_id in parameters['herd_unit_ids']
		]

		# TODO: Remove this after methods get updated for these objects
		if not project:
			raise Exception('Project not found')
		if len(herd_unit_ids) == 0:
			raise Exception('no herd units were found')

		query_1 = sql.SQL(''' 
			INSERT into projectmanagement.surveys (
				survey_date, name, additional_info
			) 
			VALUES (
				%(survey_date)s, %(name)s, %(additional_info)s
			) 
			RETURNING *; ''')

		cursor.row_factory = class_row(Survey)
		cursor.execute(query_1, parameters)
		survey = cursor.fetchone()
		if not survey:
			raise Exception('Failed to create survey')

		query_2 = sql.SQL('''
			INSERT INTO projectmanagement.projects_surveys (
				project_id, survey_id
			)
			VALUES (
				%s, %s
			);
		''')

		cursor.execute(query_2, (project.project_id, survey.survey_id))

		query_3 = sql.SQL('''
			INSERT INTO projectmanagement.surveys_herd_units (
				survey_id, herd_unit_id
			)
			VALUES (
				%s, %s
			);
		''')

		cursor.executemany(query_3, [(survey.survey_id, herd_id) for herd_id in herd_unit_ids])

		return survey
	
	def create_survey(self, parameters: dict) -> Survey:
		''' Insert a new survey object into the database

		Args:
			survey_date: the year of the survey
			name: the survey name 
			additional_info: any information that may be important regarding the survey (can be null)
		'''
		return self._create_survey(parameters)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_survey(self, cursor: Cursor[Survey], survey_id: int | UUID) -> Survey:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Survey)
		query = sql.SQL(' SELECT * FROM projectmanagement.surveys WHERE {id_field} = %s; ')
		match survey_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('survey_id')), (survey_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (survey_id,))
			case _:
				raise TypeError('survey_id MUST be an integer or a UUID')
		survey = cursor.fetchone()
		if not survey:
			raise Exception('Could not find survey')
		else:
			return survey


	def get_survey(self, survey_id: int | UUID) -> Survey:
		''' Query the database for a survey
		
		Args:
			survey_id: either the survey's internal database id or its universally unique identifier
		'''
		return self._get_survey(survey_id = survey_id)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	
	@connect
	def _get_survey_annotations(self, cursor: Cursor[Annotation], survey_id: int | UUID) -> List[Annotation]:
		'''
		'''
		cursor.row_factory = class_row(Annotation)
		query = sql.SQL('''
			SELECT A.* FROM core.annotations A
			JOIN core.images I ON I.image_id = A.image_id
			WHERE I.survey_id = %s;
		''')

		match survey_id:
			case int():
				cursor.execute(query, (survey_id,))
			case UUID():
				db_id = self.get_survey(survey_id).survey_id
				cursor.execute(query, (db_id,))

		return cursor.fetchall()

	def get_survey_annotations(self, survey_id: int | UUID) -> List[Annotation]:
		'''
		'''
		return self._get_survey_annotations(survey_id) 

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	
	@connect 
	def _get_survey_annotated_images(
		self,
		cursor: Cursor[dict],
		label_ids: List[int],
		date_range: Tuple[date, date] | None,
		survey_ids: List[int] | None,
		herd_unit_ids: List[int] | None
		):
		'''
		'''
		cursor.row_factory = dict_row

		params_1 = []
		placeholders: Dict[str, Union[List[int], date]] = {
			'label_ids': label_ids
		}

		if survey_ids is not None:
			params_1.append(sql.SQL('i.survey_id = ANY(%(survey_ids)s)'))
			placeholders['survey_ids'] = survey_ids

		if herd_unit_ids is not None:
			params_1.append(sql.SQL('i.herd_unit_id = ANY(%(herd_unit_ids)s)'))
			placeholders['herd_unit_ids'] = herd_unit_ids

		if date_range is not None:
			params_1.append(sql.SQL('i.created BETWEEN %(date_range_lower)s AND %(date_range_upper)s'))
			placeholders['date_range_lower'] = date_range[0]
			placeholders['date_range_upper'] = date_range[1]

		image_params = sql.SQL(' AND ').join(params_1)

		query = sql.SQL('''
			SELECT json_agg(row_to_json(images))
			FROM (
				SELECT
					I.*,
					json_agg(
						json_build_object(
							'annotation_id', a.annotation_id,
							'label_id', a.label_id,
							'image_id', a.image_id,
							'pred_id', a.pred_id,
							'herd_unit_id', a.herd_unit_id,
							'box_tx', a.box_tx,
							'box_ty', a.box_ty,
							'box_bx', a.box_bx,
							'box_by', a.box_by,
							'created_by_user_id', a.created_by_user_id,
							'created', a.created,
							'modified', a.modified, 
							'uuid', a.uuid
						)
					) as annotations
				FROM core.images I
				INNER JOIN core.annotations A ON A.image_id = I.image_id
				WHERE {image_args}
					AND A.label_id = ANY(%(label_ids)s)
				GROUP BY I.image_id
			) as images
		''')

		try:
			cursor.execute(query.format(image_args = image_params), placeholders)
		except Exception as e:
			print(e)
		results = cursor.fetchall()
		return results

	def get_survey_annotated_images(
		self,
		label_ids: List[int],
		date_range: Tuple[date, date] | None,
		survey_ids: List[int] | None,
		herd_unit_ids: List[int] | None
	):
		'''
		'''
		return self._get_survey_annotated_images(
			label_ids,
			date_range,
			survey_ids,
			herd_unit_ids
		)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_survey_herd_units(self, cursor: Cursor[HerdUnit], survey_id: int | UUID) -> list[HerdUnit]:
		'''
		
		'''
		survey = self._get_survey(cursor, survey_id)
		
		cursor.row_factory = class_row(HerdUnit)
		query = sql.SQL('''
			SELECT H.* FROM projectmanagement.herd_units as H JOIN
			projectmanagement.surveys_herd_units AS SHU ON SHU.herd_unit_id = H.herd_unit_id
			WHERE SHU.survey_id = %s; ''')
		cursor.execute(query, (survey.survey_id,))
		herd_units = cursor.fetchall()
		if len(herd_units) == 0:
			raise ObjectNotFound('Herd units for survey', survey_id)
		return herd_units

	def get_survey_herd_units(self, survey_id: int | UUID) -> list[HerdUnit]:
		'''
		
		'''
		return self._get_cropping_herd_units(survey_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _update_survey(self, cursor: Cursor[Survey], survey_id: int | UUID, parameters: dict) -> Survey:
		''' Internal helper function, do not call directly
		
		'''
		cursor.row_factory = class_row(Survey)
		query = sql.SQL(''' UPDATE projectmanagement.surveys SET {augmented_field}, modified = CURRENT_TIMESTAMP
							WHERE {id_field} = %s
							RETURNING *; ''')
		kw_augmented_field = sql.SQL(',').join(
			[
				sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key)) 
				for key, value in parameters.items() 
				if key in set(['survey_date', 'name', 'additional_info',
				]) 
				and value is not None
			]
		)
		match survey_id:
			case int():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('survey_id')
				), (survey_id,))
			case UUID():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('uuid')
				), (survey_id,))
			case _:
				raise TypeError('survey_id must be an integer, or uuid')
		
		survey = cursor.fetchone()

		if survey is None:
			raise Exception('Failed to update sruvey!')

		return survey		

	def update_survey(self, survey_id: int | UUID, parameters: dict):
		''' Augment a survey in the database by providing a modified Survey object or a valid id and a new name, and or survey_date, and or additional_info
		
		Args:
			survey_id: either a Survey object, a database id, or a universally unique identifier 
			survey_date: the date the survey was conducted
			name: the new name for the survey
			additional_info: a link to an additional info regarding the survey
		'''
		return self._update_survey(survey_id = survey_id, parameters=parameters)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _delete_survey(self, cursor: Cursor[Survey], survey_id: int | UUID) -> bool:
		''' Internal helper function, do not call directly
		
		'''
		query = sql.SQL(' DELETE FROM projectmanagement.surveys WHERE {id_field} = %s; ')
		match survey_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('survey_id')), (survey_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (survey_id,))
			case _:
				raise TypeError('survey_id must be a Survey, int, uuid')

		return True if cursor.rowcount > 0 else False
	
	def delete_survey(self, survey_id: int | UUID) -> bool:
		''' Delete a survey object from the database
		
		Args:
			survey_id: either a survey object, a database id, or a universally unique identifier
		'''
		return self._delete_survey(survey_ids = survey_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Core - Images	

	@connect
	def _create_image(self, cursor: Cursor[Image], parameters: dict) -> Image:
		'''
		
		'''
		if isinstance(parameters['survey_id'], str):
			parameters['survey_id'] = self._get_survey(cursor, UUID(parameters['survey_id'])).survey_id

		if isinstance(parameters['herd_unit_id'], str):
			parameters['herd_unit_id'] = self._get_herd_unit(cursor, UUID(parameters['herd_unit_id'])).herd_unit_id

		query = sql.SQL(''' 
			INSERT INTO core.images (
				herd_unit_id, survey_id, name, img_key, image_length_px, image_width_px,
				area, viewshed_polygon, has_detection, dem_name, bbox_wsen
			) 
			VALUES (
				%(herd_unit_id)s, %(survey_id)s, %(name)s, %(img_key)s, %(image_length_px)s, 
				%(image_width_px)s, %(area)s, %(viewshed_polygon)s, %(has_detection)s, %(dem_name)s, %(bbox_wsen)s
			) 
			RETURNING *; 
		''')

		cursor.row_factory = class_row(Image)
		cursor.execute(query, parameters)

		image = cursor.fetchone()

		if not image: 
			raise FailedToCreate('Image')

		return image

	def create_image(self, parameters: dict) -> Image:
		'''
		
		'''
		return self._create_image(parameters)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_image(self, cursor: Cursor[Image], image_id: int | UUID) -> Image:
		'''
		
		'''
		cursor.row_factory = class_row(Image)
		query = sql.SQL(' SELECT * FROM core.images WHERE {id_field} = %s; ')

		match image_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('image_id')), (image_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (image_id,))

		image = cursor.fetchone()
		if not image:
			raise ObjectNotFound('Image', image_id)

		return image 
	
	def get_image(self, image_id: int | UUID) -> Image:
		'''
		
		'''
		return self._get_image(image_id = image_id)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _get_image_crops(self, cursor: Cursor[ReviewedArea], image_id: int | UUID) -> List[ReviewedArea]:
		'''

		'''
		image = self._get_image(cursor, image_id)
		query = sql.SQL(' SELECT * FROM core.reviewed_area WHERE image_id = %s; ')

		cursor.row_factory = class_row(ReviewedArea)
		cursor.execute(query, (image.image_id,))
		
		crops = cursor.fetchall()
		if len(crops) == 0:
			raise ObjectNotFound('Crops for image', image_id)
		
		return crops

	def get_image_crops(self, image_id: int | UUID) -> List[ReviewedArea]:
		'''

		'''
		return self._get_image_crops(image_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_image_predictions(self, cursor: Cursor[Prediction], image_id: int | UUID) -> List[Prediction]:
		'''
		'''
		image = self._get_image(cursor, image_id)
		query = sql.SQL(' SELECT * FROM core.predictions WHERE image_id = %s; ')

		cursor.row_factory = class_row(Prediction)
		cursor.execute(query, (image.image_id,))
			
		predictions = cursor.fetchall()
		if len(predictions) == 0:
			raise ObjectNotFound('Predctions for image', image_id)
		
		return predictions

	def get_image_predictions(self, image_id: int | UUID) -> List[Prediction]:
		'''
		'''
		return self._get_image_predictions(image_id = image_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_image_annotations(self, cursor: Cursor[Annotation], image_id: int | UUID) -> List[Annotation]:
		'''
		'''
		cursor.row_factory = class_row(Annotation)
		query = sql.SQL(' SELECT * FROM core.annotations WHERE image_id = %s; ')

		match image_id:
			case int():
				cursor.execute(query, (image_id,))
			case UUID():
				db_id = self.get_image(image_id).image_id
				cursor.execute((query), (db_id,))
			case _:
				raise TypeError('image_id must be an integer, or UUID!')
		
		return cursor.fetchall()

	def get_image_annotations(self, image_id: int | UUID) -> List[Annotation]:
		'''
		'''
		return self._get_image_annotations(image_id = image_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _update_image(self, cursor: Cursor[Image], image_id: int | UUID, parameters: dict) -> Image:
		'''
		
		'''
		cursor.row_factory = class_row(Image)
		query = sql.SQL(''' 
			UPDATE core.images SET {augmented_field}, modified = CURRENT_TIMESTAMP
			WHERE {id_field} = %s
			RETURNING *; 
		''')
		kw_augmented_field = sql.SQL(',').join(
			[
				sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
				for key, value, in parameters.items() 
				if key in set([
					'name', 'img_key', 'image_length_px', 'image_width_px', 'herd_unit_id', 'survey_id', 
					'opened_by_user_id', 'area', 'polygon', 'has_detection', 'dem_name', 'bbox_wsen' 
				])
				and value is not None
			]
		) 
		match image_id:
			case int():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('image_id')
				), (image_id,))
			case UUID():   
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('uuid')
				), (image_id,))

		image = cursor.fetchone()

		if not image:
			raise ObjectNotFound('Image', image_id)

		return image
	
	def update_image(self, image_id: int | UUID, parameters: dict) -> Image:
		'''
		
		'''
		return self._update_image(image_id, parameters)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _delete_image(self, cursor: Cursor, image_id: int | UUID) -> bool:
		'''

		'''
		query = sql.SQL(''' DELETE FROM core.images WHERE {id_field} = %s; ''')
		match image_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('image_id')), (image_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (image_id,))
			case _:
				raise TypeError('image_id must be an integer, or UUID')

		return True if cursor.rowcount > 0 else False

	def delete_image(self, image_id: int | UUID) -> bool:
		'''
		
		'''
		return self._delete_image(image_id=image_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Core - Predictions

	@connect
	def _create_prediction(self, cursor: Cursor[Prediction], image_id: Image | int | UUID, model_id: Model | int | UUID, 
							label: int, score: float, box_tx: int, box_ty: int, box_bx: int, box_by: int, returning: bool) -> Optional[Prediction]:
		'''
		
		'''
		cursor.row_factory = class_row(Prediction)
		image = self._get_image(image_id) if image_id is not isinstance(image_id, Image) else image_id
		model = self._get_model(model_id) if model_id is not isinstance(model_id, Model) else model_id
		cursor.execute(sql.SQL(''' INSERT INTO core.predictions (image_id, model_id, label, score, box_tx, box_ty, 
									box_bx, box_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *; '''), 
									(cast(Image, image).image_id, cast(Model, model).model_id, label, score, box_tx, box_ty, box_bx, box_by))
		if returning:
			prediction = cursor.fetchone()
			return prediction

	def create_prediction(self, image_id: Image | int | UUID, model_id: Model | int | UUID, 
							label: int, score: float, box_tx: int, box_ty: int, box_bx: int, box_by: int, returning: bool) -> Optional[Prediction]:		   
		'''
		
		'''
		return self._create_prediction(image_id = image_id, model_id = model_id, label = label, score = score, box_tx = box_tx, box_ty = box_ty,
									box_bx = box_bx, box_by = box_by, returning = returning)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_prediction(self, cursor: Cursor[Prediction], prediction_ids: int | UUID | list[int | UUID]) -> Prediction | list[Prediction] | None:
		'''
		
		'''
		cursor.row_factory = class_row(Prediction)
		query = sql.SQL('SELECT * FROM core.predictions WHERE {id_field} = %s')
		match prediction_ids:
			case list() if isinstance(prediction_ids[0], int):
				cursor.executemany(query.format(id_field = sql.Identifier('pred_id')), [(prediction_id,) for prediction_id in prediction_ids])
			case list() if isinstance(prediction_ids[0], UUID):
				cursor.executemany(query.format(id_field = sql.Identifier('uuid')), [(prediction_id,) for prediction_id in prediction_ids])
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('pred_id')), (prediction_ids,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (prediction_ids,))
			case _:
				raise TypeError('prediction_ids must either an int, uuid, or list consisting of one of the two')
		return cursor.fetchall() if cursor.rowcount > 1 else cursor.fetchone()
	
	def get_prediction(self, prediction_ids: int | UUID | list[int | UUID]) -> Prediction | list[Prediction] | None:
		'''
		
		'''
		return self._get_prediction(prediction_ids = prediction_ids)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	# Core - Annotations

	@connect
	def _create_annotation(self, cursor: Cursor[Annotation], reviewed_area_id: int | UUID, parameters: dict) -> Annotation:
		'''
		
		'''
		if isinstance(parameters['user_id'], str):
			parameters['user_id'] = self._get_user(cursor, UUID(parameters['user_id'])).user_id

		if isinstance(parameters['herd_unit_id'], str):
			parameters['herd_unit_id'] = self._get_herd_unit(cursor, parameters['herd_unit_id']).herd_unit_id

		if isinstance(reviewed_area_id, str):
			reviewed_area_id = self._get_reviewed_area(cursor, reviewed_area_id).reveiwed_area_id

		parameters['uuid'] = UUID() if parameters['uuid'] is None else parameters['uuid']

		query_1 = sql.SQL(''' 
			INSERT INTO core.annotations (
				label_id, image_id, herd_unit_id, box_tx, box_ty, box_bx, box_by, created_by_user_id, uuid
			)
			VALUES (
				%(label_id)s, %(image_id)s, %(herd_unit_id)s, %(box_tx)s, %(box_ty)s, 
				%(box_bx)s, %(box_by)s, %(user_id)s, %(uuid)s
			) 
			RETURNING *; 
		''')
	
		cursor.row_factory = class_row(Annotation)
		cursor.execute(query_1, parameters)

		annotation = cursor.fetchone()

		if not annotation:
			raise FailedToCreate('Annotation')

		query_2 = sql.SQL('''
			INSERT INTO core.annotations_reviewed_area (
				reviewed_area_id, annotation_id
			)
			VALUES (
				%s, %s
			)
		''')

		cursor.execute(query_2, (reviewed_area_id, annotation.annotation_id))

		return annotation

	def create_annotation(self, reviewed_area_id: int | UUID, parameters: dict) -> Annotation:
		'''
		
		'''
		return self._create_annotation(reviewed_area_id, parameters)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# TODO: replace with create_annotation -- not a nessacary function 
	@connect
	def _insert_annotations(self, cursor: Cursor, annotations: list[Annotation] | Annotation, user_id: User | int | UUID) -> list[int]:
		'''
		
		'''
		user = self._get_user(user_id) if not isinstance(user_id, User) else user_id
		query = sql.SQL(''' INSERT INTO core.annotations (label_id, image_id, herd_unit_id, box_tx, box_ty, box_bx, box_by, created_by_user_id)
							VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING annotation_id; ''')
		match annotations:
			case list() if isinstance(annotations[0], Annotation):
				ids = []
				for annot in annotations:
					cursor.execute(query, (annot.label_id, annot.image_id, annot.herd_unit_id, annot.dimensions.top_left[0], annot.dimensions.top_left[1], 
									annot.dimensions.bottom_right[0], annot.dimensions.bottom_right[1], user.user_id))
					annot_id = cursor.fetchone()
					if annot_id is None:
						raise Exception('Failed to insert annotation')
					ids.append(annot_id[0])
				return ids 
			case Annotation():
				cursor.execute(query, (annotations.label_id, annotations.image_id, annotations.herd_unit_id, annotations.dimensions.top_left[0], annotations.dimensions.top_left[1], 
										annotations.dimensions.bottom_right[0], annotations.dimensions.bottom_right[1], user.user_id))
				annot_ids = cursor.fetchall() 
				ids = [annot_id[0] for annot_id in annot_ids]
				return ids
			case _:
				raise TypeError('annotations must be of type Annotation or a list consisting of Annotation objects')
	
	def insert_annotations(self, annotations: list[Annotation] | Annotation, user_id: User | int | UUID) -> list[int]:
		'''
	
		'''
		return self._insert_annotations(annotations = annotations, user_id = user_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_annotation(self, cursor: Cursor[Annotation], annotation_ids: int | UUID | list[int | UUID]) -> Annotation | list[Annotation] | None:
		'''
		
		''' 
		cursor.row_factory = class_row(Annotation)
		query = sql.SQL(''' SELECT * FROM core.annotations WHERE {id_field} = ANY(%s); ''')
		match annotation_ids:
			case list() if isinstance(annotation_ids[0], int):
				cursor.execute(query.format(id_field = sql.Identifier('annotation_id')), (annotation_ids,))
			case list() if isinstance(annotation_ids[0], UUID):
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (annotation_ids,))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('annotation_id')), ([annotation_ids],))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), ([annotation_ids],))
			case _: 
				raise TypeError('annotation_ids must be of type int or uuid or a list consisting of one of the two')
		annotations = cursor.fetchall()
		return annotations if isinstance(annotations, list) and all(isinstance(annot, Annotation) for annot in annotations) else annotations if isinstance(annotations, Annotation) else None

	def get_annotation(self, annotation_ids: int | UUID | list[int | UUID]) -> Annotation | list[Annotation] | None:
		'''
		
		'''
		return self._get_annotation(annotation_ids = annotation_ids)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _get_annotation_exists(self, cursor: Cursor, annotation_id: int | UUID) -> bool:
		'''

		'''
		query = sql.SQL(' SELECT EXISTS (SELECT image_id FROM core.annotations where {id_field} = %s); ')
		result = False
		match annotation_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('annotation_id')), (annotation_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (annotation_id,))

		result = cursor.fetchone()
		
		if result is None: 
			return False

		return result[0]

	def get_annotation_exists(self, anntoation_id: int | UUID):
		'''

		'''
		return self._get_annotation_exists(annotation_id=anntoation_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _update_annotation(self, cursor: Cursor, annotation_id: int | UUID, label_id: int | None, image_id: int | None, 
		pred_id: int | None, herd_unit_id: int | None, box_tx: int | None, box_ty: int | None, box_bx: int | None,
		box_by: int | None):
		'''

		'''
		query = sql.SQL(''' UPDATE core.annotations SET {augmented_field}, modified = CURRENT_TIMESTAMP
							WHERE {id_field} = %s; ''')

		# Generate comma separated string containing kwargs for use in update query
		kw_augmented_field = sql.SQL(',').join(
			[
				sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
				for key, value in locals().items()
				if key in set(['label_id', 'image_id', 'pred_id', 'herd_unit_id', 'box_tx', 'box_ty', 'box_bx', 'box_by'])
				and value is not None
			]
		)

		match annotation_id:
			case int():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('annotation_id')
				), (annotation_id,))
			case UUID():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('uuid')
				), (annotation_id,))
		
		return True

	def update_annotation(self, annotation_id: int | UUID, label_id: int | None=None, image_id: int | None=None, 
		pred_id: int | None=None, herd_unit_id: int | None=None, box_tx: int | None=None, box_ty: int | None=None, box_bx: int | None=None,
		box_by: int | None=None):
		'''

		'''
		return self._update_annotation(annotation_id, label_id, image_id, pred_id, herd_unit_id, box_tx, box_ty, box_bx, box_by)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _delete_annotation(self, cursor: Cursor, annotation_id: Annotation | int | UUID):
		'''

		'''
		query = sql.SQL(' DELETE FROM core.annotations WHERE {id_field} = %s; ')
		match annotation_id:
			case Annotation():
				cursor.execute(query.format(id_field = sql.Identifier('annotation_id')), (annotation_id.annotation_id,))
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('annotation_id')), (annotation_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (annotation_id,))
			case _:
				raise TypeError('annotation_id must be an Annotation, int, or uuid')
		return True

	def delete_annotation(self, annotation_id: Annotation | int | UUID):
		'''

		'''
		return self._delete_annotation(annotation_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Core - reviewed_area

	@connect
	def _create_reviewed_area(self, cursor: Cursor[ReviewedArea], image_id: Image | int | UUID, name: str, area_tx: int, area_ty: int, area_bx: int, area_by: int,
							user: User | int | UUID, returning: bool) -> ReviewedArea | None:
		'''
		
		'''
		cursor.row_factory = class_row(ReviewedArea)
		cursor.execute(sql.SQL('''INSERT INTO core.reviewed_area (image_id, name, area_tx, area_ty, area_bx, area_by, 
								reviewed_area_length_px, reviewed_area_width_px, reviewed_by_user_id)  VALUES (%s, %s, 
						%s, %s, %s, %s, %s, %s, %s)'''), (image_id, name, area_tx, area_ty, area_bx, area_by, 
								abs(area_ty - area_by), abs(area_tx - area_bx), cast(User, user).user_id))
		if returning:
			reviewed_area = cursor.fetchone()
			return reviewed_area if isinstance(reviewed_area, ReviewedArea) else None

	def create_reviewed_area(self, image_id: Image | int | UUID, name: str, area_tx: int, area_ty: int, area_bx: int, area_by: int,
							user: User | int | UUID, returning: bool) -> ReviewedArea | None:
		'''
		
		'''
		return self._create_reviewed_area(image_id = image_id, name = name, area_tx = area_tx, area_ty = area_ty, area_bx = area_bx,
										area_by = area_by, user = user, returning = returning)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _insert_reviewed_areas(self, cursor: Cursor, reviewed_areas: list[ReviewedArea]) -> int | list[int]:
		'''
		
		'''
		query = sql.SQL(''' INSERT INTO core.reviewed_area (image_id, name, area_tx, area_ty, area_bx, area_by, 
								reviewed_area_length_px, reviewed_area_width_px, reviewed_by_user_id, ra_key) VALUES (%s, %s, 
								%s, %s, %s, %s, %s, %s, %s, %s) RETURNING reviewed_area_id; ''')
		match reviewed_areas:
			case list() if isinstance(reviewed_areas[0], ReviewedArea):
				ids = []
				for ra in reviewed_areas:
					cursor.execute(query, (ra.image_id, ra.name, ra.dimensions.top_left[0], ra.dimensions.top_left[1], 
									ra.dimensions.bottom_right[0], ra.dimensions.bottom_right[1], ra.reviewed_area_length_px, 
									ra.reviewed_area_width_px, 0, ra.ra_key))
					ids.append(cursor.fetchone())
				return ids if len(ids) > 1 else ids[0]
			case ReviewedArea():
				cursor.execute(query, (reviewed_areas.image_id, reviewed_areas.name, reviewed_areas.dimensions.top_left[0], reviewed_areas.dimensions.top_left[1], 
									reviewed_areas.dimensions.bottom_right[0], reviewed_areas.dimensions.bottom_right[1], reviewed_areas.reviewed_area_length_px, 
									reviewed_areas.reviewed_area_width_px, 0, reviewed_areas.ra_key))
				ra_ids = cursor.fetchall()
				ids = [ra_id[0] for ra_id in ra_ids]
				return ids if len(ids) > 1 else ids[0]
			case _:
				raise TypeError('reviewed_areas must be of type ReviewedArea or a list consisting of ReviewedAreas')
	
	def insert_reviewed_areas(self, reviewed_areas: list[ReviewedArea] | ReviewedArea) -> int | list[int]:
		'''
		
		'''
		return self._insert_reviewed_areas(reviewed_areas = reviewed_areas)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_reviewed_area(self, cursor: Cursor[ReviewedArea], reviewed_area_id: int | UUID):
		'''
		'''
		cursor.row_factory = class_row(ReviewedArea)
		query = sql.SQL(' SELECT * FROM core.reviewed_area WHERE {id_field} = %s ')

		match reviewed_area_id:
			case int():
				cursor.execute(query.format(id_field = sql.Identifier('reviewed_area_id')), (reviewed_area_id,))
			case UUID():
				cursor.execute(query.format(id_field = sql.Identifier('uuid')), (reviewed_area_id,))
		
		reviewed_area = cursor.fetchone()
		if not reviewed_area:
			raise ObjectNotFound('Reviewed Area', reviewed_area_id)
		
		return reviewed_area

	def get_reviewed_area(self, reviewed_area_id: int | UUID) -> ReviewedArea:
		return self._get_reviewed_area(reviewed_area_id)


	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_reviewed_areas(self, cursor: Cursor[ReviewedArea], parameters: dict) -> List[ReviewedArea]:
		'''
		
		'''
		query = sql.SQL(''' 
			SELECT RA.* FROM core.reviewed_area RA
			JOIN core.images I on I.image_id = RA.image_id
			WHERE {parameter_field} 
		''')

		params = []
		placeholders: Dict[str, Union[List[int], date]] = {}

		if 'herd_unit_id' in parameters:
			params.append(sql.SQL('I.herd_unit_id = ANY(%(herd_unit_ids)s)'))
			placeholders['herd_unit_ids'] = parameters['herd_unit_id']

		if 'survey_id' in parameters:
			params.append(sql.SQL('I.survey_id = ANY(%(survey_ids)s)'))
			placeholders['survey_ids'] = parameters['survey_id']

		if not parameters['include_reviewed']:
			params.append(sql.SQL('RA.reviewed_by_user_id = 0'))
		
		if not parameters['include_opened']:
			params.append(sql.SQL('I.opened_by_user_id = 0'))

		query_params = sql.SQL(' AND ').join(params)

		if 'num' in parameters:
			query_params += sql.SQL(' LIMIT %(num)s ')
			placeholders['num'] = parameters['num']

		cursor.row_factory = class_row(ReviewedArea)
		cursor.execute(query.format(parameter_field = query_params), placeholders)

		return cursor.fetchall()
		

	def get_reviewed_areas(self, parameters: dict) -> List[ReviewedArea]:
		'''
		
		'''
		return self._get_reviewed_areas(parameters)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _update_reviewed_area(self, cursor: Cursor, reviewed_area_id: ReviewedArea | int | UUID, image_id: int | None, name: str | None, ra_key: str | None, 
		area_tx: int | None, area_ty: int | None, area_bx: int | None, area_by: int | None, reviewed_area_length_px: int | None, reviewed_area_width_px: int | None, 
		reviewed_by_user_id: int | None) -> bool:
		'''

		'''
		query = sql.SQL(''' UPDATE core.reviewed_area SET {augmented_field}, modified = CURRENT_TIMESTAMP
							WHERE {id_field} = %s; ''')

		kw_augmented_field = sql.SQL(',').join(
			[
				sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
				for key, value in locals().items()
				if key in set(['image_id', 'name', 'ra_key', 'area_tx', 'area_ty', 'area_bx', 'area_by', 
							'reviewed_area_length_px', 'reviewed_area_width_px', 'reviewed_by_user_id'])
				and value is not None
			]
		)
		match reviewed_area_id:
			case ReviewedArea():
				cursor.execute(query.format(
					augmented_field = sql.SQL(''), #TODO Finish this line
					id_field = sql.Identifier('reviewed_area_id')
				), (reviewed_area_id.reviewed_area_id,))
			case int():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('reviewed_area_id')
				), (reviewed_area_id,))
			case UUID():
				cursor.execute(query.format(
					augmented_field = kw_augmented_field,
					id_field = sql.Identifier('uuid')
				), (reviewed_area_id,))
			case _:
				raise TypeError('reviewed_area_id must be a ReviewedArea, int, or UUID')
		return True

	def update_reviewed_area(self, reviewed_area_id: ReviewedArea | int | UUID, image_id: int | None=None, name: str | None=None, ra_key: str | None=None, 
		area_tx: int | None=None, area_ty: int | None=None, area_bx: int | None=None, area_by: int | None=None, reviewed_area_length_px: int | None=None, reviewed_area_width_px: int | None=None, 
		reviewed_by_user_id: int | None=None) -> bool:
		'''

		'''
		return self._update_reviewed_area(reviewed_area_id, image_id, name, ra_key, area_tx, area_ty, area_bx, area_by, reviewed_area_length_px, reviewed_area_width_px, reviewed_by_user_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _get_project_users(self, cursor: Cursor[User], project_id: Project | int | UUID) -> list[User] | User | None:
		'''
		
		'''
		cursor.row_factory = class_row(User)
		query = sql.SQL('''
			SELECT users.user_id, username, external_auth_id, external_auth_provider, status, created, 
			modified, last_login, locale, uuid FROM usermanagement.users AS users JOIN projectmanagement.projects_users
			as projects_users ON projects_users.user_id = users.user_id WHERE projects_users.project_id = %s; ''')
		match project_id:
			case Project():
				cursor.execute(query, (project_id.project_id,))
			case int():
				cursor.execute(query, (project_id,))
			case _:
				project = self._get_project(project_id)
				cursor.execute(query, (project.project_id,))
		users = cursor.fetchall()
		return users[0] if len(users) == 1 and isinstance(users[0], User) else users if all(isinstance(user, User) for user in users) else None
	
	def get_project_users(self, project_id: Project | int | UUID) -> list[User] | User | None:
		'''
		
		'''
		return self._get_project_users(project_id = project_id)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_user_projects(self, cursor: Cursor[Project], user_id: User | int | UUID) -> list[Project]:
		'''
		
		'''
		cursor.row_factory = class_row(Project)
		query = sql.SQL(''' 
			SELECT projects.project_id, name, created, modified, uuid FROM projectmanagement.projects as projects JOIN 
			projectmanagement.projects_users AS projects_users ON projects_users.project_id = projects.project_id
			WHERE projects_users.user_id = %s; ''')
		match user_id:
			case User():
				cursor.execute(query, (user_id.user_id,))
			case int():
				cursor.execute(query, (user_id,))
			case _:
				user = self._get_user(user_id)
				cursor.execute(query, (user.user_id,))
		projects = cursor.fetchall()
		if projects is None:
			raise Exception('User has no projects')
		return projects 

	def get_user_projects(self, user_id: User | int | UUID) -> list[Project]:
		'''
		
		'''
		return self._get_user_projects(user_id = user_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect
	def _get_project_schemas(self, cursor: Cursor[Schema], project_id: Project | int | UUID) -> list[Schema] | None:
		'''
		
		'''
		cursor.row_factory = class_row(Schema)
		query = sql.SQL('''
			SELECT schemas.schema_id, name, created, modified, uuid FROM projectmanagement.schemas AS schemas 
			JOIN projectmanagement.projects_schemas AS projects_schemas ON projects_schemas.schema_id = schemas.schema_id 
			WHERE projects_schemas.project_id =  %s; ''')
		match project_id:
			case Project():
				cursor.execute(query, (cast(Project, project_id).project_id,))
			case int():
				cursor.execute(query, (project_id,))
			case _:
				project = self._get_project(project_id)
				cursor.execute(query, (project.project_id,))
		schemas = cursor.fetchall()
		return schemas
	
	def get_project_schemas(self, project_id: Project | int | UUID) -> list[Schema] | None:
		'''
		
		'''
		return self._get_project_schemas(project_id = project_id)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Relationship Management - projectmanagement <-> projectmanagement: surveys <-> herdunits

	@connect
	def _get_cropping_herd_units(self, cursor: Cursor[HerdUnit], survey_id: Survey | int | UUID) -> list[HerdUnit]:
		'''
		
		'''
		cursor.row_factory = class_row(HerdUnit)
		survey = self._get_survey(survey_id) if not isinstance(survey_id, Survey) else survey_id
		query = sql.SQL('''
			SELECT herd_units.herd_unit_id, name, created, modified, uuid FROM projectmanagement.herd_units as herd_units JOIN
			projectmanagement.surveys_herd_units AS surveys_herd_units ON surveys_herd_units.herd_unit_id = herd_units.herd_unit_id
			WHERE surveys_herd_units.survey_id = %s; ''')
		cursor.execute(query, (survey.survey_id,))
		herd_units = cursor.fetchall()
		if herd_units is None:
			raise Exception('No herd units found')
		return herd_units

	def get_cropping_herd_units(self, survey_id: Survey | int | UUID) -> list[HerdUnit]:
		'''
		
		'''
		return self._get_cropping_herd_units(survey_id = survey_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Relationship Management - projectmanagement <-> projectmanagement: projects <-> surveys

	@connect 
	def _get_project_surveys(self, cursor: Cursor[Survey], project_id: Project | int | UUID) -> list[Survey]:
		'''
		
		'''
		cursor.row_factory = class_row(Survey)
		project = self._get_project(project_id) if not isinstance(project_id, Project) else project_id
		query = sql.SQL('''
			SELECT surveys.survey_id, survey_date, name, additional_info, created, modified, uuid from projectmanagement.surveys AS surveys
			JOIN projectmanagement.projects_surveys AS projects_surveys ON projects_surveys.survey_id = surveys.survey_id 
			WHERE projects_surveys.project_id = %s; ''')
		cursor.execute(query, (project.project_id,))
		surveys = cursor.fetchall()
		if surveys is None:
			raise Exception('Could not find surveys for project')
		return surveys
				
	def get_project_surveys(self, project_id: Project | int | UUID) -> list[Survey]:
		'''
		
		'''
		return self._get_project_surveys(project_id = project_id)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Relationship Management - projectmanagement <-> projectmanagement: schemas, herdunits, and surveys 

	@connect
	def _get_cropping_models(self, cursor: Cursor[Model], survey_id: Schema | int | UUID, herd_unit_id: HerdUnit | int | UUID, schema_id: Schema | int | UUID) -> list[Model]:
		'''
		
		'''
		survey = self._get_survey(survey_id) if not isinstance(survey_id, Survey) else survey_id
		herd_unit = self._get_herd_unit(herd_unit_id) if not isinstance(herd_unit_id, HerdUnit) else herd_unit_id
		schema = self._get_schema(schema_id) if not isinstance(schema_id, Schema) else schema_id
		cursor.row_factory = class_row(Model)
		query = sql.SQL(''' SELECT models.model_id, name, created, modified, uuid, schema_id FROM projectmanagement.models AS models
							JOIN projectmanagement.surveys_models AS surveys_models ON surveys_models.model_id = models.model_id
							JOIN projectmanagement.herd_units_models AS herd_units_models ON herd_units_models.model_id = models.model_id
							WHERE surveys_models.survey_id = %s AND herd_units_models.herd_unit_id = %s AND models.schema_id = %s; ''')
		cursor.execute(query, (survey.survey_id, herd_unit.herd_unit_id, schema.schema_id))
		models = cursor.fetchall()
		if models is None:
			raise Exception('Could not find models for selection')
		return models

	def get_cropping_models(self, survey_id: Schema | int | UUID, herd_unit_id: HerdUnit | int | UUID, schema_id: Schema | int | UUID) -> list[Model]:
		'''
		
		'''
		return self._get_cropping_models(survey_id = survey_id, herd_unit_id = herd_unit_id, schema_id = schema_id)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Relationship Management - core <-> core: reviewed_area <-> annotations

	@connect
	def _add_reviewed_area_annotations(self, cursor: Cursor, reviewed_area_id: ReviewedArea | int | UUID, annotation_ids: Annotation | int | UUID | list[Annotation] | list[int] | list[UUID]) -> bool:
		'''
		
		'''
		query = sql.SQL(' INSERT INTO core.annotations_reviewed_area (annotation_id, reviewed_area_id) VALUES (%s, %s); ')
		reviewed_area = self._get_reviewed_area(reviewed_area_id) if not isinstance(reviewed_area_id, ReviewedArea) else reviewed_area_id
		if isinstance(annotation_ids, list):
			annotations = self._get_annotation(annotation_ids) if not isinstance(annotation_ids[0], Annotation) else annotation_ids
		else:
			annotations = self._get_annotation(annotation_ids) if not isinstance(annotation_ids, Annotation) else annotation_ids
		match annotations:
			case list() if isinstance(annotations[0], Annotation):
				cursor.executemany(query, [(annotation.annotation_id, reviewed_area.reviewed_area_id) for annotation in annotations]) #type: ignore
			case Annotation():
				cursor.execute(query, (annotations.annotation_id, reviewed_area.reviewed_area_id))
			case _:
				raise TypeError('reveiwed_area_id or annotation_ids are of an unexpected type')
		return True if cursor.rowcount > 0 else False

	def add_reviewed_area_annotations(self, reviewed_area_id: ReviewedArea | int | UUID, annotation_ids: Annotation | int | UUID | list[Annotation] | list[int] | list[UUID]) -> bool:
		'''

		'''
		return self._add_reviewed_area_annotations(reviewed_area_id = reviewed_area_id, annotation_ids = annotation_ids)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Access Control - User Can Access

	@connect
	def _check_user_can_access_project(self, cursor: Cursor, user_id: User |int | UUID, project_id: Project | int | UUID) -> bool:
		'''
		
		'''
		query = sql.SQL(' SELECT EXISTS (SELECT * FROM projectmanagement.projects_users WHERE user_id = %s AND project_id = %s); ')
		user = self._get_user(user_id) if not isinstance(user_id, User) else user_id
		project = self._get_project(project_id) if not isinstance(project_id, Project) else project_id
		if not user or not project:
			return False # A user cannot access a project that does not exist
		cursor.execute(query, (user.user_id, project.project_id))
		response = cursor.fetchone()
		if response is None:
			raise Exception('No response from db')
		return response[0]
	
	def check_user_can_access_project(self, user_id: User |int | UUID, project_id: Project | int | UUID) -> bool:
		'''
		
		'''
		return self._check_user_can_access_project(user_id = user_id, project_id = project_id)
			
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Functionality - Get Batch of images

	@connect
	def _get_auto_crop_batch(self, cursor: Cursor[dict], survey_id: Survey | int | UUID, herd_unit_id: HerdUnit | int | UUID, 
					batch_size: int, labels: list[int], score: float, model_id: Model | int | UUID, user_id: User | int | UUID) -> dict[str, Union[str, int, List[int]]]:
		'''
		
		'''
		herd_unit = self._get_herd_unit(cursor, herd_unit_id) if not isinstance(herd_unit_id, HerdUnit) else herd_unit_id
		survey = self._get_survey(cursor, survey_id) if not isinstance(survey_id, Survey) else survey_id
		user = self._get_user(cursor, user_id) if not isinstance(user_id, User) else user_id
		model = self._get_model(cursor, model_id) if not isinstance(model_id, Model) else model_id
		if not herd_unit or not survey or not user or not model:
			raise Exception('Could not fetch batch')

		cursor.row_factory = dict_row
		query = sql.SQL(''' 
            WITH SelectedImageIds AS (
                SELECT DISTINCT I.image_id, I.herd_unit_id, I.survey_id, P.score
                FROM core.images I
                INNER JOIN core."predictions_by_confidence" P ON I.image_id = P.image_id
                WHERE I.herd_unit_id = %(herd_unit_id)s
					AND I.survey_id = %(survey_id)s
					AND I.opened_by_user_id = 0
					AND P.model_id = %(model_id)s
					AND P.reviewed_by_user_id = 0  
					AND P.label = ANY(%(labels)s)
					AND P.score > %(score)s
				ORDER BY P.score DESC
                LIMIT %(batch_size)s
            )
            SELECT json_agg(row_to_json(img_preds))
            FROM (
                SELECT
					I.image_id,
                    I.name,
                    I.in_training,
					I.crops_generated,
					I.created,
					I.modified,
					I.image_length_px,
					I.image_width_px,
					I.uuid,
                    json_agg(
                        json_build_object(
							'pred_id', P.pred_id,
							'image_id', P.image_id,
							'model_id', P.model_id,
							'dimensions', json_build_object('top_left', json_build_array(P.box_tx, P.box_ty), 'bottom_right', json_build_array(P.box_bx, P.box_by)),
                            'score', P.score,
                            'label', P.label,
							'created', P.created,
							'uuid', P.uuid
                        )
                        ORDER BY P.score DESC
                    ) AS predictions
                FROM core.images I
                INNER JOIN core."predictions_by_confidence" P ON I.image_id = P.image_id
                WHERE I.image_id IN (SELECT image_id FROM SelectedImageIds)
                    AND P.label = ANY(%(labels)s)
                    AND P.score > %(score)s
                    AND P.model_id = %(model_id)s
				GROUP BY I.image_id 
            ) AS img_preds;
        ''')
		params = {
			'herd_unit_id': herd_unit.herd_unit_id,
			'survey_id': survey.survey_id,
			'model_id': model.model_id,
			'labels': labels, 
			'score': score,
			'batch_size': batch_size
		}
		try:
			cursor.execute(query, params)
		except Exception as e:
			print(e)
		results = cursor.fetchone()
		if results is None:
			raise Exception('Failed to fetch batch')
		ids = []
		for row in cast(dict, results)['json_agg']: 
			ids.append((user.user_id, row['image_id']))
		cursor.executemany(sql.SQL('UPDATE core.images SET opened_by_user_id = %s WHERE image_id = %s'), ids)
		return cast(dict, results)['json_agg']

	def get_auto_crop_batch(self,survey_id: Survey | int | UUID, herd_unit_id: HerdUnit | int | UUID, 
					batch_size: int, labels: list[int], score: float, model_id: Model | int | UUID, 
					user_id: User | int | UUID) -> dict[str, Union[str, int, List[int]]]:
		'''

		'''
		return self._get_auto_crop_batch(survey_id = survey_id, herd_unit_id = herd_unit_id, batch_size = batch_size, user_id = user_id, labels = labels, score = score, model_id = model_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Functionality - Delcare predictions as reviewed

	@connect
	def _set_predictions_reviewed(self, cursor: Cursor, pred_ids: list[Prediction] | list[int] | list[UUID], user_id: int) -> bool:
		'''
		
		'''
		query = sql.SQL(' UPDATE core.predictions SET reviewed_by_user_id = %s WHERE {id_field} = %s ')
		match pred_ids:
			case list() if isinstance(pred_ids[0], int):
				cursor.executemany(query.format(id_field = sql.Identifier('pred_id')), [(user_id, pred_id) for pred_id in pred_ids])
			case list() if isinstance(pred_ids[0], Prediction):
				cursor.executemany(query.format(id_field = sql.Identifier('pred_id')), [(user_id, cast(Prediction, pred).pred_id) for pred in pred_ids])
			case list() if isinstance(pred_ids[0], UUID):
				cursor.executemany(query.format(id_field = sql.Identifier('uuid')), [(user_id, uuid) for uuid in pred_ids])
			case _:
				raise TypeError('pred_ids must be a list of ints, Predictions, or UUIDS')
		return True if cursor.rowcount > 0 else False

	def set_predictions_reviewed(self, pred_ids: list[Prediction] | list[int] | list[UUID], user_id: int) -> bool:
		'''
		
		'''
		return self._set_predictions_reviewed(pred_ids = pred_ids, user_id = user_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Functionality - Close previously opened images

	@connect
	def _close_user_images(self, cursor: Cursor, user_id: int | UUID) -> bool:
		'''
		
		'''
		query = sql.SQL(' UPDATE core.images SET opened_by_user_id = 0 WHERE opened_by_user_id = %s; ')
		match user_id:
			case int():
				cursor.execute(query, (user_id,))
			case UUID():
				user = self._get_user(user_id)
				cursor.execute(query, (user.user_id,))

		return True if cursor.rowcount > 0 else False
	
	def close_user_images(self, user_id: int | UUID) -> bool:
		'''
		
		'''
		return self._close_user_images(user_id = user_id)
	
	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Functionality - Get Images by survey

	@connect 
	def _get_survey_images(self, cursor: Cursor[Image], survey_id: Survey | int | UUID) -> list[Image] | Image:
		'''
		
		'''
		cursor.row_factory = class_row(Image)
		query = sql.SQL(' SELECT * FROM core.images WHERE survey_id = %s; ')
		match survey_id:
			case Survey():
				cursor.execute(query, (survey_id.survey_id,))
			case int():
				cursor.execute(query, (survey_id,))
			case UUID():
				survey = self._get_survey(survey_id)
				cursor.execute(query, (survey.survey_id,))
			case _:
				raise TypeError('survey_id must be of type Survey, int, or UUID')
		
		return cursor.fetchall()

	def get_survey_images(self, survey_id: Survey | int | UUID) -> list[Image]:
		'''
		
		'''
		return self._get_survey_images(survey_id = survey_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Functionality - Get crops to review

	@connect
	def _get_crop_to_review(self, cursor: Cursor[ReviewedArea], parameters: dict, user_id: int | UUID) -> List[ReviewedArea]:
		''' Fetch a batch of reviewed areas that have yet to be reviewed.

		'''
		reviewed_areas = self._get_reviewed_areas(cursor, parameters)

		if len(reviewed_areas) > 0:
			self._update_image(cursor, reviewed_areas[0].image_id, {'opened_by_user_id': user_id})

		return reviewed_areas
	
	def get_crop_to_review(self, parameters: dict, user_id: int | UUID) -> List[ReviewedArea]:
		'''

		'''
		return self._get_crop_to_review(parameters, user_id)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

	@connect 
	def _get_crop_to_review_selection_count(self, cursor, paramaters: dict) -> int:
		'''

		'''
		return len(self._get_reviewed_areas(cursor, paramaters))

	def get_crop_to_review_selection_count(self, paramaters: dict) -> int:
		'''

		'''
		return self._get_crop_to_review_selection_count(paramaters)

	#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# Functionality - Get annotations for crop 

	@connect
	def _get_crop_annotations(self, cursor: Cursor[Annotation], ra_id: ReviewedArea | int | UUID) -> list[Annotation]: 
		'''
		'''
		cursor.row_factory = class_row(Annotation)
		query = sql.SQL(''' SELECT * FROM core.annotations WHERE annotation_id IN (
								SELECT annotation_id FROM core.annotations_reviewed_area
								WHERE reviewed_area_id = %s ); ''')
		match ra_id:
			case ReviewedArea():
				cursor.execute(query, (ra_id.reviewed_area_id,))
			case int():
				cursor.execute(query, (ra_id,))
			case UUID():
				ra = self._get_reviewed_area(ra_id)
				cursor.execute(query, (ra.reviewed_area_id,))

		annotations = cursor.fetchall()
		if annotations is None:
			raise Exception('Crop has no annotations')
		return annotations

	def get_crop_annotations(self,  ra_id: ReviewedArea | int | UUID) -> list[Annotation]:
		'''
		'''
		return self._get_crop_annotations(ra_id=ra_id)