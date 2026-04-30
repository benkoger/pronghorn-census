# Psycopg3 database abstraction layer for airial_api
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------#

import os
import uuid
from datetime import date, datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Iterable, List, Tuple, Union, cast
from uuid import UUID

import psycopg.sql as sql
from authzed.api.v1 import (
    BulkCheckPermissionRequest,
    BulkCheckPermissionRequestItem,
    CheckPermissionRequest,
    CheckPermissionResponse,
    InsecureClient,
    LookupResourcesRequest,
    ObjectReference,
    Relationship,
    RelationshipUpdate,
    SubjectReference,
    WriteRelationshipsRequest,
)
from grpc import ChannelCredentials
from psycopg import Cursor
from psycopg.rows import class_row, dict_row
from psycopg_pool import ConnectionPool
from werkzeug.security import generate_password_hash

from database.object_models.core.images import (
    CreateReviewedAreaReq,
    RAQuery,
    UpdateReviewedAreaReq,
)

from .errors import (
    AuthorizationFailure,
    BulkAuthorizationFailure,
    FailedToCreate,
    ObjectNotFound,
    UserNotFound,
)
from .object_models import (
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
from .object_models.autocropper import AutoCropperBatchQuery
from .object_models.core import (
    CreateAnnotationReq,
    CreatePredictionReq,
    PredictionQuery,
    UpdateImageReq,
    UpdateAnnotationReq,
)
from .object_models.project_management import (
    CreateHerdUnitReq,
    LabelQuery,
    ProjectQuery,
)
from .object_models.user_management import (
    CreateUserReq,
    RoleQuery,
    UpdateOrganizationReq,
)
from .query_builder import QueryBuilder

EXT_KEY = "base"

# ---------------------------------------------------------------------------------------------------------------------------#


class Database:
    """A psycopg3 based database abstraction layer for the airial_api package"""

    def __init__(
        self,
        db_config: Dict[str, str],
        spice_config: Dict[str, Union[str, ChannelCredentials]],
    ):
        self._config = db_config
        self._pool = None
        self._spice_client = InsecureClient(
            cast(str, spice_config["spice_url"]),
            cast(str, spice_config["bearer_token"]),
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def init_app(self, app, app_attribute_name="database"):
        """ """
        if not hasattr(app, "extensions"):
            app.extensions = {}
        app.extensions[EXT_KEY] = self

        setattr(app, app_attribute_name, self)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def create_pool(self, min_size: int = 2, max_size: int = 4):
        if self._pool is not None:  # dispose of existing pool
            self.close_pool()

        self.pool_uuid = uuid.uuid4()
        self._pool = ConnectionPool(
            kwargs=self._config,
            min_size=min_size,
            max_size=max_size,
            open=True,
            max_lifetime=290,
            check=ConnectionPool.check_connection,
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def close_pool(self):
        if self._pool:
            self._pool.close()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def connect(fn: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore
        """Wrapper function for handling connection context

        Args:
                fn: method of Database class that needs to interact with the database
        """

        @wraps(fn)
        def wrapper(self, *args, **kwargs):

            has_cursor = "cursor" in kwargs or (
                len(args) > 0 and args[0].__class__.__name__ == "Cursor"
            )

            if has_cursor:
                return fn(self, *args, **kwargs)

            if not self._pool:
                self.create_pool()
            with self._pool.connection() as conn:
                with conn.cursor() as cursor:
                    return fn(self, cursor, *args, **kwargs)

        return wrapper

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def write_spice_relationships(self, updates: List[RelationshipUpdate]):
        """ """
        return self._spice_client.WriteRelationships(
            WriteRelationshipsRequest(updates=updates)
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def create_spice_update(
        self,
        object_type: str,
        object_id: str,
        subject_type: str,
        subject_id: str,
        relation: str,
    ) -> RelationshipUpdate:
        """ """
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
                ),
            ),
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def create_bulk_check_request(
        self, object_type: str, object_id: str, subject_id: str, permission: str
    ):
        """ """
        return BulkCheckPermissionRequestItem(
            resource=ObjectReference(object_type=object_type, object_id=object_id),
            permission=permission,
            subject=SubjectReference(
                object=ObjectReference(object_type="user", object_id=subject_id)
            ),
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def bulk_check_permission(
        self, permissions: Iterable[BulkCheckPermissionRequestItem]
    ):
        """ """
        return self._spice_client.BulkCheckPermission(
            BulkCheckPermissionRequest(
                items=permissions,
            )
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def check_permission(
        self, object_type: str, object_id: str, subject_id: str, permission: str
    ):
        """ """
        return self._spice_client.CheckPermission(
            CheckPermissionRequest(
                resource=ObjectReference(object_type=object_type, object_id=object_id),
                permission=permission,
                subject=SubjectReference(
                    object=ObjectReference(
                        object_type="user",
                        object_id=subject_id,
                    )
                ),
            )
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def create_lookup_resource(
        self, resource_type: str, permission: str, subject_id: str
    ):
        """ """
        return self._spice_client.LookupResources(
            LookupResourcesRequest(
                resource_object_type=resource_type,
                permission=permission,
                subject=SubjectReference(
                    object=ObjectReference(object_type="user", object_id=subject_id)
                ),
            )
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _bootstrap(self, cursor: Cursor) -> bool:
        try:
            with open(
                os.path.join(os.path.dirname(__file__), "db_definitions.sql")
            ) as script:
                sql_script = script.read()
                # pyright: ignore[reportArgumentType]
                cursor.execute(sql_script)  # type: ignore
        except Exception as e:
            print(e)
            return False
        return True

    def bootstrap(self) -> bool:
        """Create tables detailed in sql file"""
        return self._bootstrap()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Project Management - Organizations
    @connect
    def _create_organization(
        self, cursor: Cursor[Organization], name: str, logo_url: str | None = None
    ) -> Organization | None:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Organization)
        cursor.execute(
            sql.SQL(
                "INSERT INTO usermanagement.organizations (name, logo_url) VALUES (%s, %s) RETURNING *; "
            ),
            (name, logo_url),
        )
        org = cursor.fetchone()
        return org

    def create_organizaztion(
        self, name: str, logo_url: Union[str, None] = None
    ) -> Organization:

        return self._create_organization(name=name, logo_url=logo_url)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_organization(
        self, cursor: Cursor[Organization], organization_id: int | UUID
    ) -> Organization:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Organization)
        query = sql.SQL(
            "SELECT * FROM usermanagement.organizations WHERE {id_field} = %s; "
        )
        match organization_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("organization_id")),
                    (organization_id,),
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (organization_id,)
                )

        organization = cursor.fetchone()

        if not organization:
            raise ObjectNotFound("organization", str(organization_id))

        return organization

    def get_organization(self, organization_id: int | UUID) -> Organization:
        """Request an organization, or organizations object(S) from the database

        Args:
                organization_ids: an integer, uuid, or role name, or a list consisting entirely of one of those 3 types
        """
        return self._get_organization(organization_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_many_organizations(
        self, cursor: Cursor[Organization], organization_ids: List[Union[int, UUID]]
    ) -> List[Organization]:
        """ """
        cursor.row_factory = class_row(Organization)
        ints = [i for i in organization_ids if isinstance(i, int)]
        uuids = [str(i) for i in organization_ids if not isinstance(i, int)]
        query = sql.SQL("""
			SELECT * FROM usermanagement.organizations
			WHERE organization_id = ANY(%s)
			OR uuid = ANY(%s::uuid[])
			)
		""")

        cursor.execute(query, (ints, uuids))

        return cursor.fetchall()

    def get_many_organizations(
        self, organization_ids: List[Union[int, UUID]]
    ) -> List[Organization]:
        """ """
        return self._get_many_organizations(organization_ids)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_organization_projects(
        self, cursor: Cursor[Project], org_id: Union[int, UUID]
    ) -> List[Project]:
        """ """
        query = sql.SQL("""
			SELECT P.* FROM projectmanagement.projects AS P
			JOIN usermanagement.organizations_projects AS OP ON OP.project_id = P.project_id
			WHERE OP.orgnaization_id = %s;
		""")

        org = self._get_organization(cursor, org_id)
        cursor.row_factory = class_row(Project)
        cursor.execute(query, (org.organization_id,))

        return cursor.fetchall()

    def get_organization_projects(self, org_id: Union[int, UUID]) -> List[Project]:
        """ """
        return self._get_organization_projects(org_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _update_organization(
        self,
        cursor: Cursor[Organization],
        organization_id: Union[int, UUID],
        req: UpdateOrganizationReq,
    ) -> Organization:
        """Internal helper function, do not call directly"""
        query = sql.SQL(""" 
            UPDATE usermanagement.organizations SET {augmented_field}, 
            modified = CURRENT_TIMESTAMP
		    WHERE uuid = %s
            RETURNING *; 
        """)
        kw_augmented_field = sql.SQL(",").join(
            [
                sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
                for key, value in req.model_dump().items()
                if key in set(["name", "logo_url"]) and value is not None
            ]
        )

        org = cursor.execute(
            query.format(augmented_field=kw_augmented_field), (organization_id,)
        ).fetchone()

        if not org:
            raise ObjectNotFound("organization", str(organization_id))

        return org

    def update_organization(
        self, organization_id: UUID, req: UpdateOrganizationReq, user: User
    ) -> Organization:
        """Augment an organization in the database by providing either a modified Organization object or a valid id and a new name and or a new logo_url

        Args:
        """
        org_id = str(organization_id)

        res = self.check_permission("organization", org_id, user.id, "modify")

        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._update_organization(organization_id, req)
        else:
            raise AuthorizationFailure(
                user.id, "modify", "organization", str(organization_id)
            )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _delete_organization(
        self,
        cursor: Cursor[Organization],
        organization_ids: Organization | int | UUID | list[int | UUID],
    ) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(
            " DELETE FROM usermanagement.organizations WHERE {id_field} = %s; "
        )
        match organization_ids:
            case list() if isinstance(organization_ids[0], Organization):
                cursor.executemany(
                    query.format(id_field=sql.Identifier("organization_id")),
                    [
                        (cast(Organization, org).organization_id,)
                        for org in organization_ids
                    ],
                )
            case list() if isinstance(organization_ids[0], int):
                cursor.executemany(
                    query.format(id_field=sql.Identifier("organization_id")),
                    [(org_id,) for org_id in organization_ids],
                )
            case list() if isinstance(organization_ids[0], UUID):
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), organization_ids
                )
            case Organization():
                cursor.execute(
                    query.format(id_field=sql.Identifier("organization_id")),
                    (organization_ids.organization_id,),
                )
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("organization_id")),
                    (organization_ids,),
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (organization_ids,)
                )
            case _:
                raise TypeError(
                    "organization_ids must be an Organization, int, uuid, string, or a list consisting of ONE of the three"
                )
        return True if cursor.rowcount > 0 else False

    def delete_organization(
        self, organization_ids: Organization | int | UUID | list[int | UUID]
    ) -> bool:
        """Delete an organization object from the database

        Args:
                organization_id: either an Organization object, a database id, or a universally unique identifier
        """
        return self._delete_organization(organization_ids=organization_ids)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Project Management - Roles

    @connect
    def _create_role(self, cursor: Cursor[Role], name: str) -> Role | None:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Role)
        cursor.execute(
            sql.SQL(
                " INSERT INTO usermanagement.roles (name) VALUES (%s) RETURNING *; "
            ),
            (name,),
        )
        role = cursor.fetchone()
        return role

    def create_role(self, name: str) -> Role:
        """Insert a new role object into the database

        Args:
                role: The human readable role version
        """
        return self._create_role(name=name)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_role(self, cursor: Cursor[Role], role_id: int | UUID | str) -> Role:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Role)
        query = sql.SQL(" SELECT * FROM usermanagement.roles WHERE {id_field} = %s; ")
        match role_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("role_id")), (role_id,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (role_id,)
                )
            case str():
                cursor.execute(
                    query.format(id_field=sql.Identifier("name")), (role_id,)
                )

        role = cursor.fetchone()

        if not role:
            raise ObjectNotFound("Role", str(role_id))

        return role

    def get_role(self, role_id: int | UUID | str) -> Role:
        """ """
        return self._get_role(role_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_many_roles(self, cursor: Cursor[Role], req: RoleQuery) -> List[Role]:
        """ """
        cursor.row_factory = class_row(Role)

        query = sql.SQL("""
			SELECT * FROM usermanagement.roles
			WHERE  role_id = ANY(%s)
				OR uuid = ANY(%s::uuid[])
		""")

        model = req.model_dump()

        query += sql.SQL("""
			
		""")

        ints = [i for i in model["role_id"] if isinstance(i, int)]
        uuids = [str(i) for i in model["role_id"] if not isinstance(i, int)]

        return cursor.execute(query, (ints, uuids)).fetchall()

    def get_many_roles(self, req: RoleQuery) -> List[Role]:
        """ """
        return self._get_many_roles(req)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _update_role(
        self,
        cursor: Cursor[Role],
        role_id: Role | int | UUID | str,
        name: str | None = None,
    ) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(
            """ UPDATE usermanagement.roles SET name = %s, modified = CURRENT_TIMESTAMP
							WHERE {id_field} = %s; """
        )
        match role_id:
            case Role():
                cursor.execute(
                    query.format(id_field=sql.Identifier("role_id")),
                    (role_id.name, role_id.role_id),
                )
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("role_id")), (name, role_id)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (name, role_id)
                )
            case str():
                cursor.execute(
                    query.format(id_field=sql.Identifier("name")), (name, role_id)
                )

        return True if cursor.rowcount > 0 else False

    def update_role(self, role_id: Role | int | UUID, name: str | None = None) -> Role:
        return self._update_role(role_id=role_id, name=name)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _delete_role(self, cursor: Cursor[Role], role_ids: int | UUID | str) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(" DELETE FROM usermanagement.roles WHERE {id_field} = %s; ")
        match role_ids:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("role_id")), (role_ids,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (role_ids,)
                )
            case str():
                cursor.execute(
                    query.format(id_field=sql.Identifier("role")), (role_ids,)
                )

        return True if cursor.rowcount > 0 else False

    def delete_role(self, role_ids: Role | int | UUID) -> bool:
        """Delete a role object from the database

        Args:
                role_id: either a Role object, a database id, or a universally unique identifier

        """
        return self._delete_role(role_ids=role_ids)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # User Management - Users

    @connect
    def _create_user(
        self, cursor: Cursor[User], req: CreateUserReq, organization: Organization
    ) -> User:
        """Internal helper function, do not call directly"""
        query_1 = sql.SQL("""
			INSERT INTO usermanagement.users (
				username, email, external_auth_id, external_auth_provider,
				status, locale, passowrd_hash
			)
			VALUES (
				%(username)s, %(email)s, %(external_auth_id)s, %(external_auth_provider)s, 
				%(status)s, %(locale)s, %(password_hash)s
			)No
			RETURNING *;
		""")

        query_2 = sql.SQL("""
			INSERT INTO usermanagement.organizations_users (
				user_id, organziation_id, role_id
			)
			VALUES (
				%s, %s, %s
			)
		""")

        placeholders = req.model_dump()

        placeholders["password_hash"] = generate_password_hash(placeholders["password"])

        cursor.row_factory = class_row(User)
        cursor.execute(query_1, req.model_dump())

        user = cursor.fetchone()

        if not user:
            raise FailedToCreate("user")

        # Organizations and Ids should be equal length and appear in the same order
        roles = self._get_many_roles(cursor, RoleQuery(role_id=req.role_ids))

        cursor.executemany(
            query_2,
            [
                (user.user_id, organization.organization_id, role.role_id)
                for role in roles
            ],
        )

        return user

    def create_user(self, req: CreateUserReq) -> User:
        """ """
        org = self._get_organization(req.organization_id)
        res = self.check_permission(
            "organization", str(org.uuid), str(req.current_user), "manage"
        )
        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._create_user(req, org)
        else:
            raise AuthorizationFailure(
                str(req.current_user), "manage", "organization", str(org.uuid)
            )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_user(self, cursor: Cursor[User], user_id: Union[int, UUID, str]) -> User:
        """Internal helper function, do not call directly"""

        query = sql.SQL("""
			SELECT U.* FROM usermanagement.users AS U 
			WHERE U.{id_field} = %s
		""")

        cursor.row_factory = class_row(User)
        match user_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("user_id")), (user_id,)
                )
            case str():
                cursor.execute(
                    query.format(id_field=sql.Identifier("email")), (user_id,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (user_id,)
                )

        user = cursor.fetchone()
        if not user:
            raise UserNotFound

        return user

    def get_user(self, user_id: Union[int, UUID, str]) -> User:
        """Query the database for a user

        Args:
                user_id: The user's unique database id
        """
        return self._get_user(user_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # TODO: Users should be queried by organization
    @connect
    def _get_users(self, cursor: Cursor[User]) -> List[User]:
        """

        self.crddeate_bulk_check_request('')
        """
        cursor.row_factory = class_row(User)
        query = sql.SQL("SELECT * FROM usermanagement.users WHERE user_id != 0;")

        return cursor.execute(query).fetchall()

    def get_users(self):
        return self._get_users()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_user_roles(
        self, cursor: Cursor[Role], user_id: Union[int, UUID], org_id: Union[int, UUID]
    ) -> list[Role]:
        """Internal helper function, do not call directly"""
        if isinstance(org_id, UUID):
            org_id = self._get_organization(cursor, org_id).organization_id

        query = sql.SQL(""" 
			SELECT R.* FROM usermanagement.roles AS R 
			JOIN usermanagement.organizations_users AS OU ON OU.role_id = R.role_id 
			WHERE OU.user_id = %s
			AND OU.organization_id = %s;
			""")
        match user_id:
            case int():
                cursor.execute(query, (user_id, org_id))
            case _:
                user = self._get_user(cursor, user_id)
                cursor.execute(query, (user.user_id, org_id))

        cursor.row_factory = class_row(Role)
        roles = cursor.fetchall()
        return roles

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_user_roles(
        self, user_id: Union[int, UUID], org_id: Union[int, UUID]
    ) -> list[Role]:
        """Request all roles associated with a user

        Args:
                user_id: The user's unique database id
        """
        return self._get_user_roles(user_id, org_id)

    @connect
    def _get_user_organizations(
        self, cursor: Cursor[Organization], user_id: int | UUID
    ) -> list[Organization]:
        """ """
        query = sql.SQL("""
			SELECT O.* FROM usermanagement.organizations AS O
			JOIN usermanagement.organizations_users AS OU ON OU.organization_id = O.organization_id
			WHERE OU.user_id = %s; 
		""")
        match user_id:
            case int():
                cursor.execute(query, (user_id,))
            case _:
                user = self._get_user(cursor, user_id)
                cursor.execute(query, (user.user_id,))

        cursor.row_factory = class_row(Organization)
        return cursor.fetchall()

    def get_user_organizations(self, user_id: int | UUID) -> list[Organization]:
        """ """
        return self._get_user_organizations(user_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _activate_user(
        self,
        cursor: Cursor,
        email: str,
        user_id: int | UUID,
        external_id: str,
        provider: str,
    ) -> None:
        """ """
        if isinstance(user_id, UUID):
            user_id = self._get_user(cursor, user_id).user_id

        self._update_user(
            cursor,
            user_id,
            {
                "status": "active",
                "email": email,
                "external_auth_id": external_id,
                "external_auth_provider": provider,
                "last_login": datetime.now(timezone.utc),
            },
        )

        return

    def activate_user(
        self, email: str, user_id: int | UUID, external_id: str, provider: str
    ) -> None:
        """ """
        return self._activate_user(email, user_id, external_id, provider)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _login_user(self, cursor: Cursor[User], user_id: int | UUID) -> None:
        """Internal helper function, do not call directly"""

        self._update_user(
            cursor,
            user_id,
            {"last_login": datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")},
        )

    def login_user(self, user_id: int | UUID) -> None:
        """ """
        return self._login_user(user_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _update_user(
        self, cursor: Cursor[User], user_id: int | UUID, parameters: dict
    ) -> User:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(User)
        query = sql.SQL(""" 
			UPDATE usermanagement.users SET {augmented_field}, modified = CURRENT_TIMESTAMP 
			WHERE {id_field} = %s
			RETURNING *; 
		""")
        kw_augmented_field = sql.SQL(",").join(
            [
                sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
                for key, value in parameters.items()
                if key
                in set(
                    [
                        "username",
                        "external_auth_id",
                        "external_auth_provider",
                        "status",
                        "locale",
                        "last_login",
                        "email",
                        "password_hash",
                    ]
                )
                and value is not None
            ]
        )
        match user_id:
            case int():
                cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("user_id"),
                    ),
                    (user_id,),
                )
            case UUID():
                cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("uuid"),
                    ),
                    (user_id,),
                )

        user = cursor.fetchone()

        if not user:
            raise UserNotFound

        return user

    def update_user(self, user_id: int | UUID, parameters: dict) -> bool:
        """ """
        return self._update_user(user_id, parameters)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _delete_user(
        self,
        cursor: Cursor[User],
        user_ids: User | int | UUID | list[User | int | UUID],
    ) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(" DELETE FROM usermanagement.users WHERE {id_field} = %s")
        match user_ids:
            case list() if isinstance(user_ids[0], User):
                cursor.executemany(
                    query.format(id_field=sql.Identifier("user_id")),
                    [(cast(User, user).user_id,) for user in (user_ids)],
                )
            case list() if isinstance(user_ids[0], int):
                cursor.executemany(
                    query.format(id_field=sql.Identifier("user_id")),
                    [(user_id,) for user_id in user_ids],
                )
            case list() if isinstance(user_ids[0], UUID):
                cursor.executemany(
                    query.format(id_field=sql.Identifier("uuid")),
                    [(user_id,) for user_id in user_ids],
                )
            case User():
                cursor.execute(
                    query.format(id_field=sql.Identifier("user_id")),
                    (user_ids.user_id,),
                )
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("user_id")), (user_ids,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (user_ids,)
                )
            case _:
                raise TypeError(
                    "user_ids must be a User, int, uuid, , or a list consisting of ONE of the two"
                )
        return True if cursor.rowcount > 0 else False

    def delete_user(self, user_ids: User | int | UUID) -> bool:
        """Delete a user object from the database

        Args:
                user_ids: either a user object, a database id, or a universally unique identifier or a list consisting of ONE of the two
        """
        return self._delete_user(user_ids=user_ids)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Project Management - Projects
    @connect
    def _create_project(
        self,
        cursor: Cursor[Project],
        name: str,
    ) -> Project:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Project)
        cursor.execute(
            sql.SQL(
                " INSERT INTO projectmanagement.projects (name) VALUES (%s) RETURNING *; "
            ),
            (name,),
        )
        project = cursor.fetchone()
        if project is None:
            raise Exception("Failed to create project")
        return project

    def create_project(self, name: str) -> Project:
        """Insert a new project object into the database

        Args:
                name: The name of the project you want to create
        """
        return self._create_project(name=name)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_project(self, cursor: Cursor[Project], project_id: int | UUID) -> Project:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Project)
        query = sql.SQL(
            " SELECT * FROM projectmanagement.projects WHERE {id_field} = %s "
        )
        match project_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("project_id")), (project_id,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (project_id,)
                )

        project = cursor.fetchone()
        if not project:
            raise ObjectNotFound("Project", str(project_id))

        return project

    def get_project(self, project_id: int | UUID) -> Project:
        """Query the database for a project

        Args:
                project_id: either the project's internal database id or its universally unique identifier
        """
        return self._get_project(project_id=project_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_projects(
        self, cursor: Cursor[Project], req: ProjectQuery, org: Organization
    ) -> List[Project]:
        """ """
        query = sql.SQL("""
			SELECT P.* FROM projectmanagement.projects as P
			JOIN usermanagement.organizations_projects as OP ON OP.project_id = P.project_id
			WHERE OP.organization_id = %(org_id)s
		""")

        if req.project_id:
            p_filters, data = QueryBuilder.filter_by_object_ids(
                "P", "project_id", req.project_id
            )
            cursor.row_factory = class_row(Project)
            return cursor.execute(
                query + sql.SQL("AND") + p_filters,
                {**data, "org_id": org.organization_id},
            ).fetchall()

        else:
            cursor.row_factory = class_row(Project)
            return cursor.execute(query, {"org_id": org.organization_id}).fetchall()

    def get_projects(
        self, req: ProjectQuery, org: Organization, user: User
    ) -> List[Project]:
        """ """
        if req.project_id:
            res = self.bulk_check_permission(
                [
                    self.create_bulk_check_request(
                        "project", str(project_id), user.id, "access"
                    )
                    for project_id in req.project_id
                ]
            )

            if all(
                pair.item.permissionship
                == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
                for pair in res.pairs
            ):
                return self._get_projects(req, org)
            else:
                raise BulkAuthorizationFailure(user.id, "access")
        else:
            return self._get_projects(req, org)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_project_models(
        self, cursor: Cursor[Model], project_id: UUID
    ) -> List[Model]:
        """ """
        project = self._get_project(cursor, project_id)
        query = sql.SQL(""" 
			SELECT m.* FROM projectmanagement.models M
			JOIN projectmanagement.projects_models PM ON PM.model_id = M.model_id
			WHERE PM.project_id = %s; 
		""")

        cursor.row_factory = class_row(Model)
        cursor.execute(query, (project.project_id,))

        return cursor.fetchall()

    def get_project_models(self, project_id: UUID, user: User) -> List[Model]:
        """ """
        res = self.check_permission(
            "project", str(project_id), str(user.uuid), "access"
        )
        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_project_models(project_id)
        else:
            raise AuthorizationFailure(
                str(user.uuid), "access", "project", str(project_id)
            )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_project_herd_units(
        self, cursor: Cursor[HerdUnit], project_id: UUID
    ) -> list[HerdUnit]:
        """ """
        project = self._get_project(cursor, project_id)
        query = sql.SQL("""
			SELECT HU.* FROM projectmanagement.herd_units HU JOIN
			projectmanagement.projects_herd_units PHU ON PHU.herd_unit_id = HU.herd_unit_id
			WHERE PHU.project_id = %s; 
		""")

        cursor.row_factory = class_row(HerdUnit)
        cursor.execute(query, (project.project_id,))

        return cursor.fetchall()

    def get_project_herd_units(self, project_id: UUID, user: User) -> list[HerdUnit]:
        """ """
        res = self.check_permission(
            "project", str(project_id), str(user.uuid), "access"
        )
        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_project_herd_units(project_id)
        else:
            raise AuthorizationFailure(
                str(user.uuid), "access", "project", str(project_id)
            )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _update_project(
        self,
        cursor: Cursor[Project],
        project_id: Project | int | UUID,
        name: str | None = None,
    ) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(
            " UPDATE projectmanagement.projects SET name = %s, modified = CURRENT_TIMESTAMP WHERE {id_field} = %s; "
        )
        match project_id:
            case Project():
                cursor.execute(
                    query.format(id_field=sql.Identifier("project_id")),
                    (project_id.name, project_id.project_id),
                )
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("project_id")),
                    (name, project_id),
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (name, project_id)
                )

        return True if cursor.rowcount > 0 else False

    def update_project(
        self, project_id: Project | int | UUID, name: str | None = None
    ) -> bool:
        """Augment a project in the database by providing either a modified Project object or a valid id and a new name

        Args:
                project_id: either a project object, a database id, or a universally unique identifier
                name: the new name for the project
        """
        return self._update_project(project_id=project_id, name=name)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _delete_project(
        self, cursor: Cursor[Project], project_id: Project | int | UUID
    ) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(
            " DELETE FROM projectmanagement.projects WHERE {id_field} = %s; "
        )
        match project_id:
            case Project():
                cursor.execute(
                    query.format(id_field=sql.Identifier("project_id")),
                    (project_id.project_id,),
                )
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("project_id")), (project_id,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (project_id,)
                )

        return True if cursor.rowcount > 0 else False

    def delete_project(self, project_id: Project | int | UUID) -> bool:
        """Delete a project object from the database

        Args:
                project_id: either a project object, a database id, or a universally unique identifier
        """
        return self._delete_project(project_id=project_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Project Management - Schemas

    @connect
    def _create_schema(self, cursor: Cursor[Schema], name: str) -> Schema | None:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Schema)
        cursor.execute(
            sql.SQL(
                " INSERT INTO projectmanagement.schemas (name) VALUES (%s) RETURNING *; "
            ),
            (name,),
        )
        schema = cursor.fetchone()
        return schema if isinstance(schema, Schema) else None

    def create_schema(self, name: str) -> Schema | None:
        """Insert a new schema object into the database

        Args:
                name: the schema name
        """
        return self._create_schema(name=name)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_schema(self, cursor: Cursor[Schema], schema_id: int | UUID) -> Schema:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Schema)
        query = sql.SQL(
            "  SELECT * FROM projectmanagement.schemas WHERE {id_field} = %s "
        )
        match schema_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("schema_id")), (schema_id,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (schema_id,)
                )

        schema = cursor.fetchone()
        if not schema:
            raise ObjectNotFound("Schema", str(schema_id))

        return schema

    def get_schema(self, schema_id: UUID) -> Schema:
        """Query the database for a schema

        Args:
                schema_id: either the schema's internal database id or its universally unique identifier
        """
        return self._get_schema(schema_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_schema_labels(
        self, cursor: Cursor[Label], schema_id: int | UUID
    ) -> list[Label]:
        """ """
        schema = self._get_schema(cursor, schema_id)
        query = sql.SQL(
            " SELECT * FROM projectmanagement.labels WHERE schema_id = %s; "
        )

        cursor.row_factory = class_row(Label)
        cursor.execute(query, (schema.schema_id,))
        labels = cursor.fetchall()
        if len(labels) == 0:
            raise ObjectNotFound("labels for schema", str(schema_id))
        return labels

    def get_schema_labels(self, schema_id: UUID, user: User) -> list[Label]:
        """ """
        res = self.check_permission("schema", str(schema_id), str(user.uuid), "access")
        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_schema_labels(schema_id)
        else:
            raise AuthorizationFailure(
                str(user.uuid), "access", "schema", str(schema_id)
            )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _update_schema(
        self,
        cursor: Cursor[Schema],
        schema_id: Schema | int | UUID,
        name: str | None = None,
    ) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(
            " UPDATE projectmanagement.schemas SET name =%s, modified = CURRENT_TIMESTAMP WHERE {id_field} = %s; "
        )
        match schema_id:
            case Schema():
                cursor.execute(
                    query.format(id_field=sql.Identifier("shcema_id")),
                    (schema_id.name, schema_id.schema_id),
                )
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("schema_id")),
                    (name, schema_id),
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (name, schema_id)
                )

        return True if cursor.rowcount > 0 else False

    def update_schema(self, schema_id: Schema | int | UUID, name: str):
        """Augment a schema in the database by providing a modified Project object

        Args:
                schema: A schema object
        """
        return self._update_schema(schema_id=schema_id, name=name)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _delete_schema(
        self, cursor: Cursor[Schema], schema_id: Schema | int | UUID
    ) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(
            " DELETE FROM projectmanagement.schemas WHERE {id_field} = %s; "
        )
        match schema_id:
            case Schema():
                cursor.execute(
                    query.format(id_field=sql.Identifier("schema_id")),
                    (schema_id.schema_id,),
                )
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("schema_id")), (schema_id,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (schema_id,)
                )

        return True if cursor.rowcount > 0 else False

    def delete_schema(self, schema_id: Schema | int | UUID):
        """Delete a scehma object from the database

        Args:
                schema: A schema object
        """
        return self._delete_schema(schema_id=schema_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # Project Management - labels
    @connect
    def _create_label(
        self,
        cursor: Cursor[Label],
        name: str,
        label: int,
        color: str | None = None,
        image_link: str | None = None,
    ) -> Label | None:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Label)
        cursor.execute(
            sql.SQL(
                " INSERT INTO projectmanagement.labels (name, label, color, image_link) VALUES (%s, %s, %s) RETURNING *; "
            ),
            (name, label, color, image_link),
        )
        lbl = cursor.fetchone()
        return lbl if isinstance(lbl, Label) else None

    def create_label(self, name: str, label: int, image_link: str) -> Label | None:
        """Insert a new label object into the database

        Args:
                name: The name of the label you want to create
                label: the integer value associated to the class being labeled
                image_link: optional parameter for the generator to grab an image representing the class
        """
        return self._create_label(name=name, label=label, image_link=image_link)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_label(self, cursor: Cursor[Label], label_id: Union[int, UUID]) -> Label:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Label)

        query = sql.SQL(
            " SELECT * FROM projectmanagement.labels WHERE {id_field} = %s; "
        )

        match label_id:
            case int():
                label = cursor.execute(
                    query.format(id_field=sql.Identifier("label_id")), (label_id,)
                ).fetchone()
            case UUID():
                label = cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (label_id,)
                ).fetchone()

        if label is None:
            raise ObjectNotFound("label", str(label_id))

        return label

    def get_label(self, label_id: UUID, user: User):
        """Query the database for a label

        Args:
                label_id: either the label's internal database id or its universally unique identifier
        """
        lbl_id = str(label_id)

        res = self.check_permission("label", lbl_id, user.id, "access")
        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_label(label_id=label_id)
        else:
            raise AuthorizationFailure(user.id, "access", "label", lbl_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_labels(self, cursor: Cursor[Label], req: LabelQuery) -> List[Label]:
        """ """
        query = sql.SQL("SELECT l.* FROM projectmanagement.labels as l")
        l_filters, data = QueryBuilder.filter_by_object_ids(
            "l", "label_id", req.label_id
        )

        cursor.row_factory = class_row(Label)
        return cursor.execute(
            sql.SQL("{q} WHERE {p}").format(q=query, p=l_filters), data
        ).fetchall()

    def get_labels(self, req: LabelQuery, user: User) -> List[Label]:
        """ """
        usr_id = str(user.uuid)

        res = self.bulk_check_permission(
            [
                self.create_bulk_check_request("label", str(lbl_uuid), usr_id, "access")
                for lbl_uuid in req.label_id
            ]
        )

        if all(
            pair.item.permissionship
            == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
            for pair in res.pairs
        ):
            return self._get_labels(req)
        else:
            raise BulkAuthorizationFailure(usr_id, "access")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # todo: update to use pydantic class
    @connect
    def _update_label(
        self,
        cursor: Cursor[Label],
        label_id: Label | int | UUID,
        name: str | None = None,
        label: int | None = None,
        color: str | None = None,
        image_link: str | None = None,
    ) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(
            """ UPDATE projectmanagement.labels SET {augmented_field}, modified = CURRENT_TIMESTAMP  
							WHERE {id_field} = %s; """
        )
        kw_augmented_field = sql.SQL(",").join(
            [
                sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
                for key, value in locals().items()
                if key in set(["name", "label,image_link", "color"])
                and value is not None
            ]
        )
        match label_id:
            case int():
                cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("label_id"),
                    ),
                    (label_id,),
                )
            case UUID():
                cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("uuid"),
                    ),
                    (label_id,),
                )
            case _:
                raise TypeError("label_id must be a Label, int, or UUID")
        return True if cursor.rowcount > 0 else False

    def update_label(
        self,
        label_id: Label | int | UUID,
        name: str | None = None,
        label: int | None = None,
        image_link: str | None = None,
        **kwargs,
    ) -> bool:
        """Augment a label in the database by providing a modified Label object or a valid id and a new name, and or label, and or image_link

        Args:
                label_id: either a Label object, a database id, or a universally unique identifier
                label: the integer value representing the label in models
                name: the new name for the label
                image_link: a link to an example image of the object the label represents
        """
        return self._update_label(
            label_id=label_id, name=name, label=label, image_link=image_link
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _delete_label(
        self,
        cursor: Cursor[Label],
        label_ids: Label | int | UUID | list[int | UUID | str],
    ) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(" DELETE FROM projectmanagement.labels WHERE {id_field} = %s; ")
        match label_ids:
            case list() if isinstance(label_ids[0], Label):
                cursor.executemany(
                    query.format(id_field=sql.Identifier("label_id")),
                    [(cast(Label, label).label_id,) for label in label_ids],
                )
            case list() if isinstance(label_ids[0], int):
                cursor.executemany(
                    query.format(id_field=sql.Identifier("label_id")),
                    [(label_id,) for label_id in label_ids],
                )
            case list() if isinstance(label_ids[0], UUID):
                cursor.executemany(
                    query.format(id_field=sql.Identifier("uuid")),
                    [(label_id,) for label_id in label_ids],
                )
            case Label():
                cursor.execute(
                    query.format(id_field=sql.Identifier("label_id")),
                    (label_ids.label_id,),
                )
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("label_id")), (label_ids,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (label_ids,)
                )
            case _:
                raise TypeError("label_id must be a Label, int, uuid, string")
        return True if cursor.rowcount > 0 else False

    def delete_label(self, label_ids: Label | int | UUID) -> bool:
        """Delete a label object from the database

        Args:
                label: either a label object, a database id, or a universally unique identifier
        """

        return self._delete_label(label_ids=label_ids)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Project Management - Herd Units

    @connect
    def _create_herd_unit(
        self, cursor: Cursor[HerdUnit], req: CreateHerdUnitReq
    ) -> HerdUnit:
        """Internal helper function, do not call directly"""

        project = self._get_project(cursor, req.project_id)

        query_1 = sql.SQL("""
			INSERT INTO projectmanagement.herd_units (
				name
			) 
			VALUES (
				%(name)s
			)
			RETURNING *; """)

        cursor.row_factory = class_row(HerdUnit)
        cursor.execute(query_1, req.model_dump())

        herd_unit = cursor.fetchone()
        if not herd_unit:
            raise Exception("Failed to create herd unit")

        query_2 = sql.SQL("""
			INSERT INTO projectmanagement.projects_herd_units (
				project_id, herd_unit_id 
			)
			VALUES (
				%s, %s
			);
		""")

        cursor.execute(query_2, (project.project_id, herd_unit.herd_unit_id))

        self.write_spice_relationships(
            [
                self.create_spice_update(
                    "herd_unit",
                    str(herd_unit.uuid),
                    "project",
                    str(project.uuid),
                    "parent",
                )
            ]
        )

        return herd_unit

    def create_herd_unit(self, req: CreateHerdUnitReq, user: User) -> HerdUnit:
        """Insert a new herd unit object into the database

        Args:
                name: the herd unit name
        """
        usr_id = str(user.uuid)
        project_id = str(req.project_id)

        res = self.check_permission("project", project_id, usr_id, "access")
        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._create_herd_unit(req)
        else:
            raise AuthorizationFailure(usr_id, "access", "project", project_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_herd_unit(self, cursor: Cursor[HerdUnit], herd_unit_id: UUID) -> HerdUnit:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(HerdUnit)
        query = sql.SQL(" SELECT * FROM projectmanagement.herd_units WHERE uuid = %s; ")

        herd_unit = cursor.execute(query, (herd_unit_id,)).fetchone()

        if not herd_unit:
            raise Exception("Herd Unit was not found")

        return herd_unit

    def get_herd_unit(self, herd_unit_id: UUID, user: User) -> HerdUnit:
        """Query the database for a herd unit

        Args:
        herd_unit_id: A universally unique identifier
        """
        res = self.check_permission(
            "herd_unit", str(herd_unit_id), str(user.uuid), "access"
        )

        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_herd_unit(herd_unit_id=herd_unit_id)
        else:
            raise AuthorizationFailure(
                str(user.uuid), "access", "herd_unit", str(herd_unit_id)
            )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_herd_unit_surveys(
        self, cursor: Cursor[Survey], herd_unit_id: UUID
    ) -> list[Survey]:
        """ """
        herd_unit = self._get_herd_unit(herd_unit_id)

        cursor.row_factory = class_row(Survey)
        query = sql.SQL("""
			SELECT S.* FROM projectmanagement.surveys as S JOIN
			projectmanagement.surveys_herd_units AS SHU ON SHU.survey_id = S.survey_id
			WHERE SHU.herd_unit_id = %s; """)
        cursor.execute(query, (herd_unit.herd_unit_id,))
        surveys = cursor.fetchall()
        if len(surveys) == 0:
            raise ObjectNotFound("Surveys for herd unit", str(herd_unit_id))

        return surveys

    def get_herd_unit_surveys(self, herd_unit_id: UUID, user: User) -> list[Survey]:
        """ """
        res = self.check_permission(
            "herd_unit", str(herd_unit_id), str(user.uuid), "access"
        )
        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_herd_unit_surveys(herd_unit_id)
        else:
            raise AuthorizationFailure(
                str(user.uuid), "access", "herd_unit", str(herd_unit_id)
            )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _update_herd_unit(
        self,
        cursor: Cursor[HerdUnit],
        herd_unit_id: HerdUnit | int | UUID,
        name: str | None = None,
    ) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(
            """ UPDATE projectmanagement.herd_units SET name = %s, modified = CURRENT_TIMESTAMP
							WHERE {id_field} = %s; """
        )
        match herd_unit_id:
            case HerdUnit():
                cursor.execute(
                    query.format(id_field=sql.Identifier("herd_unit_id")),
                    (herd_unit_id.name, herd_unit_id.herd_unit_id),
                )
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("herd_unit_id")),
                    (name, herd_unit_id),
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (name, herd_unit_id)
                )

        return True if cursor.rowcount > 0 else False

    def update_herd_unit(
        self, herd_unit_id: HerdUnit | int | UUID, name: str | None = None
    ) -> bool:
        """Augment a herd unit in the database by providing a modified HerdUnit object or a valid id and a new name

        Args:
                herd_unit_id: either a HerdUnit object, a database id, or a universally unique identifier
                name: the new name for the herd unit
        """
        return self._update_herd_unit(herd_unit_id=herd_unit_id, name=name)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _delete_herd_unit(
        self, cursor: Cursor[HerdUnit], herd_unit_ids: HerdUnit | int | UUID
    ) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(
            " DELETE FROM projectmanagement.herd_units WHERE {id_field} = %s; "
        )
        match herd_unit_ids:
            case HerdUnit():
                cursor.execute(
                    query.format(id_field=sql.Identifier("herd_unit_id")),
                    (herd_unit_ids.herd_unit_id,),
                )
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("herd_unit_id")),
                    (herd_unit_ids,),
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (herd_unit_ids,)
                )

        return True if cursor.rowcount > 0 else False

    def delete_herd_unit(self, herd_unit_ids: HerdUnit | int | UUID) -> bool:
        """Delete a herd unit object from the database

        Args:
                herd_unit_id: either a herd unit object, a database id, or a universally unique identifier
        """
        return self._delete_herd_unit(herd_unit_ids=herd_unit_ids)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Project Management - Models

    @connect
    def _create_model(self, cursor: Cursor[Model], parameters: dict) -> Model:
        """Internal helper function, do not call directly"""
        project = self._get_project(cursor, parameters["project_id"])
        schema = self._get_schema(cursor, parameters["schema_id"])

        # TODO: create method to get list of surveys
        survey_ids = [
            survey_id if isinstance(survey_id, int) else UUID(survey_id)
            for survey_id in parameters["survey_ids"]
        ]

        if not schema:
            raise Exception("Schema not found")
        if len(survey_ids) == 0:
            raise Exception("no surveys were found")

        query_1 = sql.SQL(""" 
			INSERT into projectmanagement.models (
				name, schema_id
			)
			VALUES (
				%(name)s, %(schema_id)s
			)
			RETURNING *; 
		""")

        cursor.execute(query_1, parameters)
        cursor.row_factory = class_row(Model)
        model = cursor.fetchone()
        if not model:
            raise Exception("Failed to create model")

        query_2 = sql.SQL(""" 
			INSERT INTO projectmanagement.projects_models (
				project_id, model_id
			) 
			VALUES (
				%s, %s
			); 
		""")

        cursor.execute(query_2, (project.project_id, model.model_id))

        query_3 = sql.SQL("""
			INSERT INTO projectmanagement.surveys_models (
				survey_id, model_id
			)
			VALUES (
				%s, %s	
			);
		""")

        cursor.executemany(
            query_3, [(survey_id, model.model_id) for survey_id in survey_ids]
        )

        return model

    def create_model(self, parameters: dict) -> Model:
        """Insert a new model object into the database

        Args:
                name: the model name
        """
        return self._create_model(parameters)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_model(self, cursor: Cursor[Model], model_id: int | UUID) -> Model:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Model)
        query = sql.SQL(
            " SELECT * FROM projectmanagement.models WHERE {id_field} = %s; "
        )
        match model_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("model_id")), (model_id,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (model_id,)
                )

        model = cursor.fetchone()
        if not model:
            raise ObjectNotFound("Model", str(model_id))

        return model

    def get_model(self, model_id: int | UUID) -> Model:
        """Query the database for a model

        Args:
                model_id: either the models's internal database id or its universally unique identifier
        """
        return self._get_model(model_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_model_schema(self, cursor: Cursor[Schema], model_id: UUID) -> Schema:
        """ """
        model = self._get_model(model_id)

        cursor.row_factory = class_row(Schema)
        query = sql.SQL(
            " SELECT * FROM projectmanagement.schemas WHERE schema_id = %s; "
        )
        cursor.execute(query, (model.schema_id,))

        schema = cursor.fetchone()
        if not schema:
            raise ObjectNotFound("Schema for model", str(model_id))

        return schema

    def get_model_schema(self, model_id: UUID, user: User) -> Schema:
        """ """
        res = self.check_permission("model", str(model_id), str(user.uuid), "access")
        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_model_schema(model_id)
        else:
            raise AuthorizationFailure(str(user.uuid), "access", "model", str(model_id))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _update_model(
        self, cursor: Cursor[Model], model_id: int | UUID, parameters: dict
    ) -> Model:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Model)
        query = sql.SQL(
            """ UPDATE projectmanagement.models SET {augmented_field}, modified = CURRENT_TIMESTAMP 
							WHERE {id_field} = %s RETURNING *; """
        )
        kw_augmented_field = sql.SQL(",").join(
            [
                sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
                for key, value in parameters.items()
                if key in set(["survey_id", "survey_date", "name", "additional_info"])
                and value is not None
            ]
        )
        match model_id:
            case int():
                cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("model_id"),
                    ),
                    (model_id,),
                )
            case UUID():
                cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("uuid"),
                    ),
                    (model_id,),
                )
            case _:
                raise TypeError("model_id MUST be an integer, or UUID")

        model = cursor.fetchone()

        if model:
            return model
        else:
            raise Exception("failed to update the model")

    def update_model(self, model_id: int | UUID, parameters: dict) -> Model:
        """Augment a model in the database by providing a modified Model object or a valid id and a new name

        Args:
                model: either a Model object, a database id, or a universally unique identifier
                name: the new name for the model
        """
        return self._update_model(model_id, parameters)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _delete_model(
        self, cursor: Cursor[Model], model_ids: Model | int | UUID
    ) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(" DELETE FROM projectmanagement.models WHERE {id_field} = %s; ")
        match model_ids:
            case Model():
                cursor.execute(
                    query.format(id_field=sql.Identifier("model_id")),
                    (model_ids.model_id,),
                )
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("model_id")), (model_ids,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (model_ids,)
                )

        return True if cursor.rowcount > 0 else False

    def delete_model(self, model_ids: Model | int | UUID) -> bool:
        """Delete a model object from the database

        Args:
                model_id: either a model object, a database id, or a universally unique identifier
        """
        return self._delete_model(model_ids=model_ids)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_model_training_data(
        self,
        cursor: Cursor[dict],
        label_ids: List[int],
        date_range: Tuple[date, date] | None,
        survey_ids: List[int] | None,
        herd_unit_ids: List[int] | None,
    ):
        """ """
        cursor.row_factory = dict_row

        params_1 = []
        placeholders: Dict[str, Union[List[int], date]] = {"label_ids": label_ids}

        if survey_ids:
            params_1.append(sql.SQL("i.survey_id = ANY(%(survey_ids)s)"))
            placeholders["survey_ids"] = survey_ids

        if herd_unit_ids:
            params_1.append(sql.SQL("i.herd_unit_id = ANY(%(herd_unit_ids)s)"))
            placeholders["herd_unit_ids"] = herd_unit_ids

        if date_range:
            params_1.append(
                sql.SQL(
                    "i.created BETWEEN %(date_range_lower)s AND %(date_range_upper)s"
                )
            )
            placeholders["date_range_lower"] = date_range[0]
            placeholders["date_range_upper"] = date_range[1]

        image_params = sql.SQL(" AND ").join(params_1)

        query = sql.SQL("""
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
		""")

        try:
            cursor.execute(query.format(image_args=image_params), placeholders)
        except Exception as e:
            print(e)
        results = cursor.fetchone()

        return results

    def get_model_training_data(
        self,
        label_ids: List[int],
        date_range: Tuple[date, date] | None,
        survey_ids: List[int] | None,
        herd_unit_ids: List[int] | None,
    ):
        """ """
        return self._get_model_training_data(
            label_ids, date_range, survey_ids, herd_unit_ids
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Project Management - Surveys

    @connect
    def _create_survey(self, cursor: Cursor[Survey], parameters: dict) -> Survey:
        """Internal helper function, do not call directly"""

        project = self._get_project(cursor, parameters["project_id"])

        # TODO: create method to get list of herd units
        herd_unit_ids = [
            herd_unit_id if isinstance(herd_unit_id, int) else UUID(herd_unit_id)
            for herd_unit_id in parameters["herd_unit_ids"]
        ]

        # TODO: Remove this after methods get updated for these objects
        if not project:
            raise Exception("Project not found")
        if len(herd_unit_ids) == 0:
            raise Exception("no herd units were found")

        query_1 = sql.SQL(""" 
			INSERT into projectmanagement.surveys (
				survey_date, name, additional_info
			) 
			VALUES (
				%(survey_date)s, %(name)s, %(additional_info)s
			) 
			RETURNING *; """)

        cursor.row_factory = class_row(Survey)
        cursor.execute(query_1, parameters)
        survey = cursor.fetchone()
        if not survey:
            raise Exception("Failed to create survey")

        query_2 = sql.SQL("""
			INSERT INTO projectmanagement.projects_surveys (
				project_id, survey_id
			)
			VALUES (
				%s, %s
			);
		""")

        cursor.execute(query_2, (project.project_id, survey.survey_id))

        query_3 = sql.SQL("""
			INSERT INTO projectmanagement.surveys_herd_units (
				survey_id, herd_unit_id
			)
			VALUES (
				%s, %s
			);
		""")

        cursor.executemany(
            query_3, [(survey.survey_id, herd_id) for herd_id in herd_unit_ids]
        )

        return survey

    def create_survey(self, parameters: dict) -> Survey:
        """Insert a new survey object into the database

        Args:
                survey_date: the year of the survey
                name: the survey name
                additional_info: any information that may be important regarding the survey (can be null)
        """
        return self._create_survey(parameters)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_survey(self, cursor: Cursor[Survey], survey_id: int | UUID) -> Survey:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Survey)
        query = sql.SQL(
            " SELECT * FROM projectmanagement.surveys WHERE {id_field} = %s; "
        )
        match survey_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("survey_id")), (survey_id,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (survey_id,)
                )
            case _:
                raise TypeError("survey_id MUST be an integer or a UUID")
        survey = cursor.fetchone()
        if not survey:
            raise Exception("Could not find survey")
        else:
            return survey

    def get_survey(self, survey_id: int | UUID) -> Survey:
        """Query the database for a survey

        Args:
                survey_id: either the survey's internal database id or its universally unique identifier
        """
        return self._get_survey(survey_id=survey_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_survey_annotations(
        self, cursor: Cursor[Annotation], survey_id: int | UUID
    ) -> List[Annotation]:
        """ """
        cursor.row_factory = class_row(Annotation)
        query = sql.SQL("""
			SELECT A.* FROM core.annotations A
			JOIN core.images I ON I.image_id = A.image_id
			WHERE I.survey_id = %s;
		""")

        match survey_id:
            case int():
                cursor.execute(query, (survey_id,))
            case UUID():
                db_id = self.get_survey(survey_id).survey_id
                cursor.execute(query, (db_id,))

        return cursor.fetchall()

    def get_survey_annotations(self, survey_id: int | UUID) -> List[Annotation]:
        """ """
        return self._get_survey_annotations(survey_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_survey_annotated_images(
        self,
        cursor: Cursor[dict],
        label_ids: List[int],
        date_range: Tuple[date, date] | None,
        survey_ids: List[int] | None,
        herd_unit_ids: List[int] | None,
    ):
        """ """
        cursor.row_factory = dict_row

        params_1 = []
        placeholders: Dict[str, Union[List[int], date]] = {"label_ids": label_ids}

        if survey_ids is not None:
            params_1.append(sql.SQL("i.survey_id = ANY(%(survey_ids)s)"))
            placeholders["survey_ids"] = survey_ids

        if herd_unit_ids is not None:
            params_1.append(sql.SQL("i.herd_unit_id = ANY(%(herd_unit_ids)s)"))
            placeholders["herd_unit_ids"] = herd_unit_ids

        if date_range is not None:
            params_1.append(
                sql.SQL(
                    "i.created BETWEEN %(date_range_lower)s AND %(date_range_upper)s"
                )
            )
            placeholders["date_range_lower"] = date_range[0]
            placeholders["date_range_upper"] = date_range[1]

        image_params = sql.SQL(" AND ").join(params_1)

        query = sql.SQL("""
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
		""")

        try:
            cursor.execute(query.format(image_args=image_params), placeholders)
        except Exception as e:
            print(e)
        results = cursor.fetchall()
        return results

    def get_survey_annotated_images(
        self,
        label_ids: List[int],
        date_range: Tuple[date, date] | None,
        survey_ids: List[int] | None,
        herd_unit_ids: List[int] | None,
    ):
        """ """
        return self._get_survey_annotated_images(
            label_ids, date_range, survey_ids, herd_unit_ids
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_survey_herd_units(
        self, cursor: Cursor[HerdUnit], survey_id: int | UUID
    ) -> list[HerdUnit]:
        """ """
        survey = self._get_survey(cursor, survey_id)

        cursor.row_factory = class_row(HerdUnit)
        query = sql.SQL("""
			SELECT H.* FROM projectmanagement.herd_units as H JOIN
			projectmanagement.surveys_herd_units AS SHU ON SHU.herd_unit_id = H.herd_unit_id
			WHERE SHU.survey_id = %s; """)
        cursor.execute(query, (survey.survey_id,))
        herd_units = cursor.fetchall()
        if len(herd_units) == 0:
            raise ObjectNotFound("Herd units for survey", str(survey_id))
        return herd_units

    def get_survey_herd_units(self, survey_id: int | UUID) -> list[HerdUnit]:
        """ """
        return self._get_cropping_herd_units(survey_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _update_survey(
        self, cursor: Cursor[Survey], survey_id: int | UUID, parameters: dict
    ) -> Survey:
        """Internal helper function, do not call directly"""
        cursor.row_factory = class_row(Survey)
        query = sql.SQL(
            """ UPDATE projectmanagement.surveys SET {augmented_field}, modified = CURRENT_TIMESTAMP
							WHERE {id_field} = %s
							RETURNING *; """
        )
        kw_augmented_field = sql.SQL(",").join(
            [
                sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
                for key, value in parameters.items()
                if key
                in set(
                    [
                        "survey_date",
                        "name",
                        "additional_info",
                    ]
                )
                and value is not None
            ]
        )
        match survey_id:
            case int():
                cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("survey_id"),
                    ),
                    (survey_id,),
                )
            case UUID():
                cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("uuid"),
                    ),
                    (survey_id,),
                )
            case _:
                raise TypeError("survey_id must be an integer, or uuid")

        survey = cursor.fetchone()

        if survey is None:
            raise Exception("Failed to update sruvey!")

        return survey

    def update_survey(self, survey_id: int | UUID, parameters: dict):
        """Augment a survey in the database by providing a modified Survey object or a valid id and a new name, and or survey_date, and or additional_info

        Args:
                survey_id: either a Survey object, a database id, or a universally unique identifier
                survey_date: the date the survey was conducted
                name: the new name for the survey
                additional_info: a link to an additional info regarding the survey
        """
        return self._update_survey(survey_id=survey_id, parameters=parameters)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _delete_survey(self, cursor: Cursor[Survey], survey_id: int | UUID) -> bool:
        """Internal helper function, do not call directly"""
        query = sql.SQL(
            " DELETE FROM projectmanagement.surveys WHERE {id_field} = %s; "
        )
        match survey_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("survey_id")), (survey_id,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (survey_id,)
                )
            case _:
                raise TypeError("survey_id must be a Survey, int, uuid")

        return True if cursor.rowcount > 0 else False

    def delete_survey(self, survey_id: int | UUID) -> bool:
        """Delete a survey object from the database

        Args:
                survey_id: either a survey object, a database id, or a universally unique identifier
        """
        return self._delete_survey(survey_ids=survey_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Core - Images

    @connect
    def _create_image(self, cursor: Cursor[Image], parameters: dict) -> Image:
        """ """
        if isinstance(parameters["survey_id"], str):
            parameters["survey_id"] = self._get_survey(
                cursor, UUID(parameters["survey_id"])
            ).survey_id

        if isinstance(parameters["herd_unit_id"], str):
            parameters["herd_unit_id"] = self._get_herd_unit(
                cursor, UUID(parameters["herd_unit_id"])
            ).herd_unit_id

        query = sql.SQL(""" 
			INSERT INTO core.images (
				herd_unit_id, survey_id, name, img_key, image_length_px, image_width_px,
				area, viewshed_polygon, has_detection, dem_name, bbox_wsen
			) 
			VALUES (
				%(herd_unit_id)s, %(survey_id)s, %(name)s, %(img_key)s, %(image_length_px)s, 
				%(image_width_px)s, %(area)s, %(viewshed_polygon)s, %(has_detection)s, %(dem_name)s, %(bbox_wsen)s
			) 
			RETURNING *; 
		""")

        cursor.row_factory = class_row(Image)
        cursor.execute(query, parameters)

        image = cursor.fetchone()

        if not image:
            raise FailedToCreate("Image")

        return image

    def create_image(self, parameters: dict) -> Image:
        """ """
        return self._create_image(parameters)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_image(self, cursor: Cursor[Image], image_id: Union[int, UUID]) -> Image:
        """ """
        cursor.row_factory = class_row(Image)
        query = sql.SQL(" SELECT * FROM core.images WHERE {id_field} = %s; ")

        match image_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("image_id")), (image_id,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (image_id,)
                )

        image = cursor.fetchone()
        if not image:
            raise ObjectNotFound("Image", str(image_id))

        return image

    def get_image(self, image_id: UUID, user: User) -> Image:
        """ """
        usr_id = str(user.uuid)
        img_id = str(image_id)

        res = self.check_permission("image", img_id, usr_id, "access")

        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_image(image_id)
        else:
            raise AuthorizationFailure(usr_id, "access", "image", img_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_image_crops(
        self, cursor: Cursor[ReviewedArea], image_id: Union[int, UUID]
    ) -> List[ReviewedArea]:
        """ """
        image = self._get_image(cursor, image_id)
        query = sql.SQL(" SELECT * FROM core.reviewed_area WHERE image_id = %s; ")

        cursor.row_factory = class_row(ReviewedArea)
        cursor.execute(query, (image.image_id,))

        crops = cursor.fetchall()
        if len(crops) == 0:
            raise ObjectNotFound("Crops for image", str(image_id))

        return crops

    def get_image_crops(self, image_id: int | UUID) -> List[ReviewedArea]:
        """ """
        return self._get_image_crops(image_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_image_predictions(
        self, cursor: Cursor[Prediction], image_id: int | UUID
    ) -> List[Prediction]:
        """ """
        image = self._get_image(cursor, image_id)
        query = sql.SQL(" SELECT * FROM core.predictions WHERE image_id = %s; ")

        cursor.row_factory = class_row(Prediction)
        cursor.execute(query, (image.image_id,))

        predictions = cursor.fetchall()
        if len(predictions) == 0:
            raise ObjectNotFound("Predctions for image", str(image_id))

        return predictions

    def get_image_predictions(self, image_id: int | UUID) -> List[Prediction]:
        """ """
        return self._get_image_predictions(image_id=image_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_image_annotations(
        self, cursor: Cursor[Annotation], image_id: UUID
    ) -> List[Annotation]:
        """ """
        query = sql.SQL(" SELECT * FROM core.annotations WHERE image_id = %s; ")

        db_id = self._get_image(cursor, image_id).image_id
        cursor.execute((query), (db_id,))

        return cursor.fetchall()

    def get_image_annotations(self, image_id: UUID, user: User) -> List[Annotation]:
        """ """
        usr_id = str(user.uuid)
        img_id = str(image_id)

        res = self.check_permission("image", img_id, usr_id, "access")

        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_image_annotations(image_id=image_id)
        else:
            raise AuthorizationFailure(usr_id, "access", "image", img_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _update_image(
        self, cursor: Cursor[Image], image_id: Union[int, UUID], req: UpdateImageReq
    ) -> Image:
        """ """
        cursor.row_factory = class_row(Image)
        query = sql.SQL(""" 
			UPDATE core.images AS i SET {augmented_field}, modified = CURRENT_TIMESTAMP
			WHERE i.{id_field} = %s
			RETURNING *; 
		""")
        kw_augmented_field = sql.SQL(",").join(
            [
                sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
                for key, value in req.model_dump().items()
                if key
                in set(
                    [
                        "name",
                        "img_key",
                        "image_length_px",
                        "image_width_px",
                        "herd_unit_id",
                        "survey_id",
                        "opened_by_user_id",
                        "area",
                        "polygon",
                        "has_detection",
                        "dem_name",
                        "bbox_wsen",
                    ]
                )
                and value is not None
            ]
        )
        match image_id:
            case int():
                image = cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("image_id"),
                    ),
                    (image_id,),
                ).fetchone()
            case UUID():
                image = cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("uuid"),
                    ),
                    (image_id,),
                ).fetchone()

        if not image:
            raise ObjectNotFound("Image", str(image_id))

        return image

    def update_image(
        self,
        image_id: Union[int, UUID],
        req: UpdateImageReq,
        user: User,
        bypass: bool = False,
    ) -> Image:
        """ """
        # Allow the api layer to bypass bypass acl checks to prevent redundant checks
        if bypass or isinstance(image_id, int):
            return self._update_image(image_id, req)

        img_id = str(image_id)
        res = self.check_permission("image", img_id, user.id, "access")

        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._update_image(image_id, req)
        else:
            raise AuthorizationFailure(user.id, "access", "image", img_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _delete_image(self, cursor: Cursor, image_id: int | UUID) -> bool:
        """ """
        query = sql.SQL(""" DELETE FROM core.images WHERE {id_field} = %s; """)
        match image_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("image_id")), (image_id,)
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (image_id,)
                )
            case _:
                raise TypeError("image_id must be an integer, or UUID")

        return True if cursor.rowcount > 0 else False

    def delete_image(self, image_id: int | UUID) -> bool:
        """ """
        return self._delete_image(image_id=image_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Core - Predictions

    @connect
    def _create_prediction(
        self, cursor: Cursor[Prediction], req: CreatePredictionReq
    ) -> Prediction:
        """ """
        image = self._get_image(cursor, req.image_id)
        model = self._get_model(cursor, req.model_id)

        query = sql.SQL("""
			INSERT INTO core.predicitons (
				image_id, model_id, label, score, box_tx, box_ty, box_bx, box_by
			)
			VALUES (
				%(image_id)s, %(model_id)s, %(label)s, %(score)s, %(box_tx)s, %(box_ty)s, %(box_bx)s, %(box_by)s
			)
			RETURNING *;

			""")

        prediction = cursor.execute(query, req.model_dump()).fetchone()

        if not prediction:
            raise FailedToCreate("prediction")

        return prediction

    def create_prediction(self, req: CreatePredictionReq, user: User) -> Prediction:
        """ """
        usr_id = str(user.uuid)
        image_id = str(req.image_id)

        res = self.check_permission("image", image_id, usr_id, "access")
        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._create_prediction(req)
        else:
            raise AuthorizationFailure(usr_id, "access", "image", image_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_prediction(
        self, cursor: Cursor[Prediction], prediction_id: UUID
    ) -> Prediction:
        """ """
        cursor.row_factory = class_row(Prediction)
        query = sql.SQL("SELECT * FROM core.predictions WHERE uuid = %s")

        prediction = cursor.execute(query, (prediction_id,)).fetchone()

        if not prediction:
            raise ObjectNotFound("prediction", str(prediction_id))

        return prediction

    def get_prediction(self, prediction_id: UUID, user: User) -> Prediction:
        """ """
        usr_id = str(user.uuid)
        pred_id = str(prediction_id)

        res = self.check_permission("prediction", pred_id, usr_id, "access")

        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_prediction(prediction_id)
        else:
            raise AuthorizationFailure(usr_id, "access", "prediction", pred_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    # TODO: Replace PredictionCropQuery with PredictionQuery
    def _get_predictions(
        self, cursor: Cursor[Prediction], req: PredictionQuery
    ) -> List[Prediction]:
        """ """
        query = sql.SQL("SELECT p.* FROM core.predictions as p")

        p_filters, data = QueryBuilder.filter_by_object_ids(
            "p", "pred_id", req.prediction_id
        )
        cursor.row_factory = class_row(Prediction)
        return cursor.execute(
            sql.SQL("{q} WHERE {p}").format(q=query, p=p_filters), data
        ).fetchall()

    def get_predictions(self, req: PredictionQuery, user: User) -> List[Prediction]:
        """ """
        res = self.bulk_check_permission(
            [
                self.create_bulk_check_request(
                    "prediction", str(pred_uuid), user.id, "access"
                )
                for pred_uuid in req.prediction_id
            ]
        )

        if all(
            pair.item.permissionship
            == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
            for pair in res.pairs
        ):
            return self._get_predictions(req)
        else:
            raise BulkAuthorizationFailure(user.id, "access")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Core - Annotations

    @connect
    def _create_annotation(
        self,
        cursor: Cursor[Annotation],
        req: CreateAnnotationReq,
        user: User,
    ) -> Annotation:
        """ """
        query_1 = sql.SQL(""" 
			INSERT INTO core.annotations (
				label_id, image_id, herd_unit_id, box_tx, box_ty, box_bx, box_by, created_by_user_id, pred_id, uuid
			)
			VALUES (
				%(label_id)s, %(image_id)s, %(herd_unit_id)s, %(box_tx)s, %(box_ty)s, 
				%(box_bx)s, %(box_by)s, %(created_by_user_id)s, %(pred_id)s, %(uuid)s
			) 
			RETURNING *; 
		""")

        query_2 = sql.SQL("""
			INSERT INTO core.annotations_reviewed_area (
				reviewed_area_id, annotation_id
			)
			VALUES (
				%s, %s
			)
		""")

        params = req.model_dump()

        image = self._get_image(cursor, req.image_id)
        params["image_id"] = image.image_id

        label = self._get_label(cursor, req.label_id)
        params["label_id"] = label.label_id

        if req.pred_id:
            prediction = self._get_prediction(cursor, req.pred_id)
            params["pred_id"] = prediction.pred_id
        else:
            params["pred_id"] = 0

        params["created_by_user_id"] = user.user_id

        cursor.row_factory = class_row(Annotation)
        annotation = cursor.execute(query_1, params).fetchone()

        if not annotation:
            raise FailedToCreate("Annotation")

        if req.reviewed_area_id:
            ra_id = self._get_reviewed_area(
                cursor, req.reviewed_area_id
            ).reviewed_area_id
            cursor.execute(query_2, (ra_id, annotation.annotation_id))

        self.write_spice_relationships(
            [
                self.create_spice_update(
                    "annotation",
                    str(annotation.uuid),
                    "image",
                    str(image.uuid),
                    "parent",
                )
            ]
        )

        return annotation

    def create_annotation(
        self,
        req: CreateAnnotationReq,
        user: User,
        bypass: bool = False,
    ) -> Annotation:
        """ """
        if bypass:
            return self._create_annotation(req, user)
        img_id = str(self._get_image(req.image_id).uuid)
        lbl_id = str(self._get_label(req.label_id).uuid)

        res = self.bulk_check_permission(
            [
                self.create_bulk_check_request("image", img_id, user.id, "access"),
                self.create_bulk_check_request("label", lbl_id, user.id, "access"),
            ]
        )

        if all(
            pair.item.permissionship
            == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
            for pair in res.pairs
        ):
            return self._create_annotation(req, user)
        else:
            raise BulkAuthorizationFailure(user.id, "access")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_annotation(
        self, cursor: Cursor[Annotation], annotation_id: Union[int, UUID]
    ) -> Annotation:
        """ """
        cursor.row_factory = class_row(Annotation)
        query = sql.SQL(
            """ SELECT * FROM core.annotations WHERE {id_field} = ANY(%s); """
        )
        match annotation_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("annotation_id")),
                    ([annotation_id],),
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), ([annotation_id],)
                )

        annotation = cursor.fetchone()

        if not annotation:
            raise ObjectNotFound("Annotation", str(annotation_id))

        return annotation

    def get_annotation(
        self, annotation_id: Union[int, UUID], user: User, bypass: bool = False
    ) -> Annotation:
        """ """
        if bypass or isinstance(annotation_id, int):
            return self._get_annotation(annotation_id)

        annot_id = str(annotation_id)

        res = self.check_permission("annotation", annot_id, user.id, "access")

        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_annotation(annotation_id)
        else:
            raise AuthorizationFailure(
                user.id, "access", "annotation", str(annotation_id)
            )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_annotation_exists(self, cursor: Cursor, annotation_id: int | UUID) -> bool:
        """ """
        query = sql.SQL(
            " SELECT EXISTS (SELECT image_id FROM core.annotations where {id_field} = %s); "
        )
        result = False
        match annotation_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("annotation_id")),
                    (annotation_id,),
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (annotation_id,)
                )

        result = cursor.fetchone()

        if result is None:
            return False

        return result[0]

    def get_annotation_exists(self, anntoation_id: int | UUID):
        """ """
        return self._get_annotation_exists(annotation_id=anntoation_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _update_annotation(
        self,
        cursor: Cursor[Annotation],
        annotation_id: Union[int, UUID],
        req: UpdateAnnotationReq,
    ) -> Annotation:
        """ """
        query = sql.SQL(""" 
            UPDATE core.annotations SET {augmented_field}, modified = CURRENT_TIMESTAMP
			WHERE {id_field} = %s
            RETURNING *; 
        """)

        # Generate comma separated string containing kwargs for use in update query
        kw_augmented_field = sql.SQL(",").join(
            [
                sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
                for key, value in req.model_dump().items()
                if key
                in set(
                    [
                        "label_id",
                        "image_id",
                        "pred_id",
                        "herd_unit_id",
                        "box_tx",
                        "box_ty",
                        "box_bx",
                        "box_by",
                    ]
                )
                and value is not None
            ]
        )

        cursor.row_factory = class_row(Annotation)
        match annotation_id:
            case int():
                cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("annotation_id"),
                    ),
                    (annotation_id,),
                )
            case UUID():
                cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("uuid"),
                    ),
                    (annotation_id,),
                )

        annotation = cursor.fetchone()

        if not annotation:
            raise ObjectNotFound("Annotation", str(annotation_id))

        return annotation

    def update_annotation(
        self,
        annotation_id: Union[int, UUID],
        req: UpdateAnnotationReq,
        user: User,
        bypass: bool = False,
    ) -> Annotation:
        """ """
        if bypass or isinstance(annotation_id, int):
            return self._update_annotation(annotation_id, req)

        annot_id = str(annotation_id)

        if req.image_id and isinstance(req.image_id, UUID):
            image_access = self.check_permission(
                "image", str(req.image_id), user.id, "access"
            )
            if (
                image_access.permissionship
                != CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
            ):
                raise AuthorizationFailure(
                    user.id, "access", "image", str(req.image_id)
                )

        if req.label_id and isinstance(req.label_id, UUID):
            label_access = self.check_permission(
                "label", str(req.label_id), user.id, "access"
            )
            if (
                label_access.permissionship
                != CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
            ):
                raise AuthorizationFailure(
                    user.id, "access", "label", str(req.label_id)
                )

        res = self.check_permission("annotation", annot_id, user.id, "access")

        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._update_annotation(annotation_id, req)
        else:
            raise AuthorizationFailure(user.id, "access", "annotation", annot_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _delete_annotation(self, cursor: Cursor, annotation_id: Union[int, UUID]):
        """ """
        query = sql.SQL(" DELETE FROM core.annotations WHERE {id_field} = %s; ")
        match annotation_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("annotation_id")),
                    (annotation_id,),
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (annotation_id,)
                )

        return True if cursor.rowcount > 0 else False

    def delete_annotation(self, annotation_id: Union[int, UUID], user: User):
        """ """
        annot_id = str(annotation_id)

        res = self.check_permission("annotation", annot_id, user.id, "access")

        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._delete_annotation(annotation_id)
        else:
            raise AuthorizationFailure(user.id, "access", "annotation", annot_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Core - reviewed_area

    @connect
    def _create_reviewed_area(
        self, cursor: Cursor[ReviewedArea], req: CreateReviewedAreaReq
    ) -> ReviewedArea:
        """ """
        query = sql.SQL("""
            INSERT INTO core.reviewed_area (
                image_id, name, area_tx, area_ty, area_bx, area_by, reviewed_area_length_px,
                reviewed_area_width_px, reviewed_by_user_id, ra_key
            )
            VALUES (
                %(image_id)s, %(name)s, %(area_tx)s, %(area_ty)s, %(area_bx)s, %(area_by)s, 
                %(reviewed_area_length_px)s, %(reviewed_area_width_px)s, %(reviewed_by_user_id)s,
                %(ra_key)s
            )
            RETURNING *;
        """)

        image = self._get_image(cursor, req.image_id)
        params = req.model_dump()

        params["image_id"] = image.image_id

        cursor.row_factory = class_row(ReviewedArea)
        crop = cursor.execute(query, params).fetchone()

        if not crop:
            raise FailedToCreate("Reviewed Area")

        self.write_spice_relationships(
            [
                self.create_spice_update(
                    "reviewed_area",
                    str(crop.uuid),
                    "image",
                    str(req.image_id),
                    "parent",
                )
            ]
        )

        return crop

    def create_reviewed_area(
        self, req: CreateReviewedAreaReq, user: User, bypass: bool
    ) -> ReviewedArea:
        """ """
        if bypass:
            return self._create_reviewed_area(req)
        img_id = str(req.image_id)

        res = self.check_permission("image", img_id, user.id, "access")
        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._create_reviewed_area(req)
        else:
            raise AuthorizationFailure(user.id, "acesss", "image", img_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_reviewed_area(
        self, cursor: Cursor[ReviewedArea], reviewed_area_id: int | UUID
    ):
        """ """
        cursor.row_factory = class_row(ReviewedArea)
        query = sql.SQL(" SELECT * FROM core.reviewed_area  WHERE {id_field} = %s ")

        match reviewed_area_id:
            case int():
                cursor.execute(
                    query.format(id_field=sql.Identifier("reviewed_area_id")),
                    (reviewed_area_id,),
                )
            case UUID():
                cursor.execute(
                    query.format(id_field=sql.Identifier("uuid")), (reviewed_area_id,)
                )

        reviewed_area = cursor.fetchone()
        if not reviewed_area:
            raise ObjectNotFound("Reviewed Area", str(reviewed_area_id))

        return reviewed_area

    def get_reviewed_area(self, reviewed_area_id: int | UUID) -> ReviewedArea:
        return self._get_reviewed_area(reviewed_area_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_reviewed_areas(
        self, cursor: Cursor[ReviewedArea], req: RAQuery
    ) -> List[ReviewedArea]:
        """ """
        query = sql.SQL(""" 
			SELECT ra.* FROM core.reviewed_area ra
			JOIN core.images i on i.image_id = ra.image_id
			WHERE {parameter_field} 
		""")

        params = []
        placeholders: Dict[str, Union[List[int], date, int]] = {}

        if req.herd_unit_id:
            herd_unit = self._get_herd_unit(cursor, req.herd_unit_id[0])
            params.append(sql.SQL("i.herd_unit_id = ANY(%(herd_unit_ids)s)"))
            placeholders["herd_unit_ids"] = [herd_unit.herd_unit_id]

        if req.survey_id:
            survey = self._get_survey(cursor, req.survey_id[0])
            params.append(sql.SQL("i.survey_id = ANY(%(survey_ids)s)"))
            placeholders["survey_ids"] = [survey.survey_id]

        if not req.include_reviewed:
            params.append(sql.SQL("RA.reviewed_by_user_id = 0"))

        if not req.include_opened:
            params.append(sql.SQL("i.opened_by_user_id = 0"))

        query_params = sql.SQL(" AND ").join(params)

        if req.num:
            query_params += sql.SQL(" LIMIT %(num)s ")  # pyright: ignore
            placeholders["num"] = req.num

        cursor.row_factory = class_row(ReviewedArea)
        cursor.execute(query.format(parameter_field=query_params), placeholders)

        return cursor.fetchall()

    def get_reviewed_areas(self, req: RAQuery) -> List[ReviewedArea]:
        """ """
        return self._get_reviewed_areas(req)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_reviewed_area_annotations(
        self, cursor: Cursor[Annotation], ra_id: UUID
    ) -> list[Annotation]:
        """ """
        cursor.row_factory = class_row(Annotation)
        query = sql.SQL(""" SELECT * FROM core.annotations WHERE annotation_id IN (
								SELECT annotation_id FROM core.annotations_reviewed_area
								WHERE reviewed_area_id = %s ); """)

        ra = self._get_reviewed_area(ra_id)
        cursor.execute(query, (ra.reviewed_area_id,))

        annotations = cursor.fetchall()
        if annotations is None:
            raise Exception("Crop has no annotations")
        return annotations

    def get_reviewed_area_annotations(
        self, reviewed_area_id: UUID, user: User
    ) -> list[Annotation]:
        """ """
        ra_id = str(reviewed_area_id)
        res = self.check_permission("reviewed_area", ra_id, user.id, "access")

        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_reviewed_area_annotations(reviewed_area_id)
        else:
            raise AuthorizationFailure(user.id, "access", "reviewed_area", ra_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _update_reviewed_area(
        self,
        cursor: Cursor[ReviewedArea],
        reviewed_area_id: Union[int, UUID],
        req: UpdateReviewedAreaReq,
        user: User,
    ) -> ReviewedArea:
        """ """
        query = sql.SQL(""" UPDATE core.reviewed_area SET {augmented_field} 
            modified = CURRENT_TIMESTAMP, reviewed_by_user_id = %s
			WHERE {id_field} = %s
            RETURNING *; """)

        kw_augmented_field = sql.SQL(",").join(
            [
                sql.SQL("{} = '%s'" % (value)).format(sql.Identifier(key))
                for key, value in req.model_dump().items()
                if key
                in set(
                    [
                        "image_id",
                        "name",
                        "ra_key",
                        "area_tx",
                        "area_ty",
                        "area_bx",
                        "area_by",
                        "reviewed_area_length_px",
                        "reviewed_area_width_px",
                    ]
                )
                and value is not None
            ]
        )

        cursor.row_factory = class_row(ReviewedArea)
        match reviewed_area_id:
            case int():
                cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("reviewed_area_id"),
                    ),
                    (user.user_id, reviewed_area_id),
                )
            case UUID():
                cursor.execute(
                    query.format(
                        augmented_field=kw_augmented_field,
                        id_field=sql.Identifier("uuid"),
                    ),
                    (user.user_id, reviewed_area_id),
                )
        reviewed_area = cursor.fetchone()

        if not reviewed_area:
            raise ObjectNotFound("Reviewed Area", str(reviewed_area))

        return reviewed_area

    def update_reviewed_area(
        self,
        reviewed_area_id: Union[int, UUID],
        req: UpdateReviewedAreaReq,
        user: User,
        bypass: bool = False,
    ) -> ReviewedArea:
        """ """
        if bypass or isinstance(reviewed_area_id, int):
            return self._update_reviewed_area(reviewed_area_id, req)

        ra_id = str(reviewed_area_id)

        if req.image_id:
            image_access = self.check_permission(
                "image", str(req.image_id), user.id, "access"
            )
            if (
                image_access.permissionship
                != CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
            ):
                raise AuthorizationFailure(
                    user.id, "access", "image", str(req.image_id)
                )

        res = self.check_permission("reviewed_area", ra_id, user.id, "access")

        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._update_reviewed_area(reviewed_area_id, req, user)
        else:
            raise AuthorizationFailure(user.id, "access", "reviewed_area", "access")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_project_users(
        self, cursor: Cursor[User], project_id: Project | int | UUID
    ) -> list[User] | User | None:
        """ """
        cursor.row_factory = class_row(User)
        query = sql.SQL(
            """
			SELECT users.user_id, username, external_auth_id, external_auth_provider, status, created, 
			modified, last_login, locale, uuid FROM usermanagement.users AS users JOIN projectmanagement.projects_users
			as projects_users ON projects_users.user_id = users.user_id WHERE projects_users.project_id = %s; """
        )
        match project_id:
            case Project():
                cursor.execute(query, (project_id.project_id,))
            case int():
                cursor.execute(query, (project_id,))
            case _:
                project = self._get_project(project_id)
                cursor.execute(query, (project.project_id,))
        users = cursor.fetchall()
        return (
            users[0]
            if len(users) == 1 and isinstance(users[0], User)
            else users if all(isinstance(user, User) for user in users) else None
        )

    def get_project_users(
        self, project_id: Project | int | UUID
    ) -> list[User] | User | None:
        """ """
        return self._get_project_users(project_id=project_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_user_projects(
        self, cursor: Cursor[Project], user_id: User | int | UUID
    ) -> list[Project]:
        """ """
        cursor.row_factory = class_row(Project)
        query = sql.SQL(""" 
			SELECT projects.project_id, name, created, modified, uuid FROM projectmanagement.projects as projects JOIN 
			projectmanagement.projects_users AS projects_users ON projects_users.project_id = projects.project_id
			WHERE projects_users.user_id = %s; """)
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
            raise Exception("User has no projects")
        return projects

    def get_user_projects(self, user_id: User | int | UUID) -> list[Project]:
        """ """
        return self._get_user_projects(user_id=user_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_project_schemas(
        self, cursor: Cursor[Schema], project_id: UUID
    ) -> list[Schema]:
        """ """
        cursor.row_factory = class_row(Schema)
        query = sql.SQL("""
			SELECT schemas.schema_id, name, created, modified, uuid FROM projectmanagement.schemas AS schemas 
			JOIN projectmanagement.projects_schemas AS projects_schemas ON projects_schemas.schema_id = schemas.schema_id 
			WHERE projects_schemas.project_id =  %s; """)
        project = self._get_project(project_id)

        cursor.execute(query, (project.project_id,))
        schemas = cursor.fetchall()
        return schemas

    def get_project_schemas(self, project_id: UUID, user: User) -> list[Schema]:
        """ """
        res = self.check_permission("project", str(project_id), str(user.uuid), "view")
        if res.permissionship == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION:
            return self._get_project_schemas(project_id=project_id)
        else:
            raise AuthorizationFailure(
                str(user.uuid), "view", "project", str(project_id)
            )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Relationship Management - projectmanagement <-> projectmanagement: surveys <-> herdunits

    @connect
    def _get_cropping_herd_units(
        self, cursor: Cursor[HerdUnit], survey_id: Survey | int | UUID
    ) -> list[HerdUnit]:
        """ """
        cursor.row_factory = class_row(HerdUnit)
        survey = (
            self._get_survey(survey_id)
            if not isinstance(survey_id, Survey)
            else survey_id
        )
        query = sql.SQL("""
			SELECT herd_units.herd_unit_id, name, created, modified, uuid FROM projectmanagement.herd_units as herd_units JOIN
			projectmanagement.surveys_herd_units AS surveys_herd_units ON surveys_herd_units.herd_unit_id = herd_units.herd_unit_id
			WHERE surveys_herd_units.survey_id = %s; """)
        cursor.execute(query, (survey.survey_id,))
        herd_units = cursor.fetchall()
        if herd_units is None:
            raise Exception("No herd units found")
        return herd_units

    def get_cropping_herd_units(self, survey_id: Survey | int | UUID) -> list[HerdUnit]:
        """ """
        return self._get_cropping_herd_units(survey_id=survey_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Relationship Management - projectmanagement <-> projectmanagement: projects <-> surveys

    @connect
    def _get_project_surveys(
        self, cursor: Cursor[Survey], project_id: Project | int | UUID
    ) -> list[Survey]:
        """ """
        cursor.row_factory = class_row(Survey)
        project = (
            self._get_project(project_id)
            if not isinstance(project_id, Project)
            else project_id
        )
        query = sql.SQL("""
			SELECT surveys.survey_id, survey_date, name, additional_info, created, modified, uuid from projectmanagement.surveys AS surveys
			JOIN projectmanagement.projects_surveys AS projects_surveys ON projects_surveys.survey_id = surveys.survey_id 
			WHERE projects_surveys.project_id = %s; """)
        cursor.execute(query, (project.project_id,))
        surveys = cursor.fetchall()
        if surveys is None:
            raise Exception("Could not find surveys for project")
        return surveys

    def get_project_surveys(self, project_id: Project | int | UUID) -> list[Survey]:
        """ """
        return self._get_project_surveys(project_id=project_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_auto_crop_batch(
        self, cursor: Cursor[Dict], params: AutoCropperBatchQuery, user: User
    ) -> dict[str, Union[str, int, List[int]]]:
        """ """
        q_params = {
            "survey_id": self._get_survey(cursor, params.survey_id).survey_id,
            "herd_unit_id": self._get_herd_unit(
                cursor, params.herd_unit_id
            ).herd_unit_id,
            "model_id": self._get_model(cursor, params.model_id).model_id,
            "labels": params.label,
            "score": params.min_confidence,
            "batch_size": params.batch_size,
        }

        cursor.row_factory = dict_row
        query = sql.SQL(""" 
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
							'dimensions', json_build_object(
								'top_left', json_build_array(P.box_tx, P.box_ty), 
								'bottom_right', json_build_array(P.box_bx, P.box_by)),
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
		""")

        cursor.execute(query, q_params)

        results = cursor.fetchone()

        if results is None:
            raise Exception("Failed to fetch batch")

        ids = []
        for row in cast(dict, results)["json_agg"]:
            ids.append((user.user_id, row["image_id"]))

        cursor.executemany(
            sql.SQL(
                "UPDATE core.images SET opened_by_user_id = %s WHERE image_id = %s"
            ),
            ids,
        )
        return cast(dict, results)["json_agg"]

    def get_auto_crop_batch(
        self, req: AutoCropperBatchQuery, user: User
    ) -> dict[str, Union[str, int, List[int]]]:
        """ """
        usr_id = str(user.uuid)
        perm = "access"

        res = self.bulk_check_permission(
            [
                self.create_bulk_check_request(
                    "survey", str(req.survey_id), usr_id, perm
                ),
                self.create_bulk_check_request(
                    "herd_unit", str(req.herd_unit_id), usr_id, perm
                ),
                self.create_bulk_check_request(
                    "model", str(req.model_id), usr_id, perm
                ),
            ]
        )

        if all(
            pair.item.permissionship
            == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
            for pair in res.pairs
        ):
            return self._get_auto_crop_batch(req, user)
        else:
            raise BulkAuthorizationFailure(usr_id, "access")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Functionality - Set predictions as reviewed

    @connect
    def _set_predictions_reviewed(
        self,
        cursor: Cursor,
        prediction_ids: List[UUID],
        user: User,
    ) -> bool:
        """ """
        print([(user.user_id, uuid) for uuid in prediction_ids])
        query = sql.SQL(
            " UPDATE core.predictions AS p SET reviewed_by_user_id = %s WHERE p.uuid = %s "
        )
        cursor.executemany(
            query,
            [(user.user_id, uuid) for uuid in prediction_ids],
        )
        return True

    def set_predictions_reviewed(self, prediction_ids: List[UUID], user: User) -> bool:
        """ """
        return self._set_predictions_reviewed(prediction_ids, user)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Functionality - Close previously opened images

    @connect
    def _close_user_images(self, cursor: Cursor, user_id: int | UUID) -> bool:
        """ """
        query = sql.SQL(
            " UPDATE core.images SET opened_by_user_id = 0 WHERE opened_by_user_id = %s; "
        )
        match user_id:
            case int():
                cursor.execute(query, (user_id,))
            case UUID():
                user = self._get_user(user_id)
                cursor.execute(query, (user.user_id,))

        return True if cursor.rowcount > 0 else False

    def close_user_images(self, user_id: int | UUID) -> bool:
        """ """
        return self._close_user_images(user_id=user_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Functionality - Get Images by survey

    @connect
    def _get_survey_images(
        self, cursor: Cursor[Image], survey_id: Survey | int | UUID
    ) -> list[Image] | Image:
        """ """
        cursor.row_factory = class_row(Image)
        query = sql.SQL(" SELECT * FROM core.images WHERE survey_id = %s; ")
        match survey_id:
            case Survey():
                cursor.execute(query, (survey_id.survey_id,))
            case int():
                cursor.execute(query, (survey_id,))
            case UUID():
                survey = self._get_survey(survey_id)
                cursor.execute(query, (survey.survey_id,))

        return cursor.fetchall()

    def get_survey_images(self, survey_id: Survey | int | UUID) -> list[Image]:
        """ """
        return self._get_survey_images(survey_id=survey_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Functionality - Get crops to review

    @connect
    def _get_crop_to_review(
        self, cursor: Cursor[ReviewedArea], req: RAQuery, user: User
    ) -> Union[ReviewedArea, None]:
        """Fetch a batch of reviewed areas that have yet to be reviewed."""
        reviewed_areas = self._get_reviewed_areas(cursor, req)

        if len(reviewed_areas) > 0:
            image = self._get_image(reviewed_areas[0].image_id)
            self._update_image(
                cursor,
                image.uuid,
                UpdateImageReq(opened_by_user_id=user.user_id),
            )

            return reviewed_areas[0]
        else:
            return None

    def get_crop_to_review(self, req: RAQuery, user: User) -> Union[ReviewedArea, None]:
        """ """
        return self._get_crop_to_review(req, user)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_crop_to_review_selection_count(self, cursor, req: RAQuery) -> int:
        """ """
        return len(self._get_reviewed_areas(cursor, req))

    def get_crop_to_review_selection_count(self, req: RAQuery) -> int:
        """ """
        return self._get_crop_to_review_selection_count(req)
