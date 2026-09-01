# Psycopg3 database abstraction layer for airial_apidatabase.py
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------#


import atexit
import uuid
from functools import wraps
from typing import (
    Any,
    Callable,
    cast,
    Type,
)

from collections.abc import Iterable
from pydantic import BaseModel
from uuid import UUID

from authzed.api.v1 import (
    BulkCheckPermissionRequest,
    BulkCheckPermissionRequestItem,
    BulkCheckPermissionResponse,
    CheckPermissionRequest,
    Client,
    Consistency,
    InsecureClient,
    LookupResourcesRequest,
    ObjectReference,
    RelationshipUpdate,
    SubjectReference,
    WriteRelationshipsRequest,
)
from grpc import (
    access_token_call_credentials,
    composite_channel_credentials,
    ssl_channel_credentials,
)
import psycopg.sql as sql
from psycopg import Cursor
from psycopg.errors import DatabaseError
from psycopg.rows import class_row
from psycopg_pool import ConnectionPool
from werkzeug.security import generate_password_hash

from database.object_models.base import DBbase, T, Relationbase

from .errors import (
    FailedToCreate,
    ObjectNotFound,
)

# ---------------------------------------------------------------------------------------------------------------------------

EXT_KEY = "base"
PrimaryKey = int | UUID

# ---------------------------------------------------------------------------------------------------------------------------


def _clause_generator(
    clauses: dict[str, Any],
    sep: sql.SQL = sql.SQL(", "),
    prefix: str = "",
) -> sql.Composed:
    """Generate SQL statements from a dictionary."""
    return sep.join(
        sql.SQL("{} = {}").format(
            sql.Identifier(col),
            sql.Placeholder(f"{prefix}{col}"),
        )
        for col in clauses.keys()
    )


def _resolve_identifier(cls, key: PrimaryKey) -> sql.Identifier:
    """Determine which key type a PrimaryKey object is"""
    match key:
        case int():
            pk_col = cls.get_pk_identifier()
        case UUID():
            pk_col = sql.Identifier("uuid")

    return pk_col


# ---------------------------------------------------------------------------------------------------------------------------


class Database:
    """A psycopg3 based database abstraction layer for the airial_api package"""

    def __init__(
        self,
        db_config: dict[str, str],
        spice_config: dict[str, str | bool],
    ):
        self._config = db_config
        self._pool = None

        if spice_config["use_tls"]:

            with open(cast(str, spice_config["SPICEDB_CERT_PATH"]), "rb") as f:
                tls_creds = ssl_channel_credentials(f.read())

            token_creds = access_token_call_credentials(
                cast(str, spice_config["bearer_token"])
            )

            combined_creds = composite_channel_credentials(tls_creds, token_creds)

            self._spice_client = Client(
                cast(str, spice_config["spice_url"]),
                combined_creds,
            )
        else:

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

        atexit.register(self.close_pool)

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

    def write_spice_relationships(self, updates: list[RelationshipUpdate]):
        """ """
        return self._spice_client.WriteRelationships(
            WriteRelationshipsRequest(updates=updates)
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
        self,
        items: Iterable[BulkCheckPermissionRequestItem],
        consistency: Consistency | None = None,
    ) -> BulkCheckPermissionResponse:
        if consistency is None:
            consistency = Consistency(fully_consistent=True)

        request = BulkCheckPermissionRequest(items=items, consistency=consistency)
        return self._spice_client.BulkCheckPermission(request)

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
    def _check_bootstrapped(self, cursor: Cursor) -> bool:
        """ """
        query = sql.SQL("SELECT first_run FROM usermanagement.initialization;")
        res = cursor.execute(query).fetchone()

        if res is None:
            # first_run is set up during database bootstrapping
            raise DatabaseError()

        return False if res[0] else True

    def check_bootstrapped(self) -> bool:
        return self._check_bootstrapped()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _set_bootstrapped(self, cursor: Cursor) -> bool:
        """ """
        query = sql.SQL("UPDATE usermanagement.initialization SET first_run = false;")

        cursor.execute(query)

        return True

    def set_bootstrapped(self) -> bool:
        """ """
        return self._set_bootstrapped()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # INSERT
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _insert(self, cursor: Cursor[T], cls: type[T], req: BaseModel) -> T:
        """Internal insert method."""
        if not (result := cls._create(cursor, req)):
            raise FailedToCreate(cls.__name__)

        obj, relations = result

        if len(relations) > 0:
            self.write_spice_relationships(relations)

        return obj

    def insert(self, cls: type[T], req: BaseModel) -> T:
        """Inserts a new record into the database and returns the created instance.

        Args:
            cls: The model class to insert into.
            **req: Pydantic request model.

        Returns:
            T: The newly created entity.

        Raises:
            ForeignKeyViolation: If a foreign key references a non-existent record.
            UniqueViolation: If a unique constraint is violated.
        """
        return self._insert(cls, req)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # UPDATE
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _update(
        self, cursor: Cursor[T], cls: type[T], pk: PrimaryKey, req: BaseModel
    ) -> T:
        """Internal update method."""
        query = sql.SQL("""
            UPDATE {table}
            SET {set_clause}, modified = CURRENT_TIMESTAMP
            WHERE {id_col} = %(_pk_val)s
            RETURNING *;
        """)

        data = req.model_dump(exclude_unset=True, exclude_none=True)

        if not data:
            return self._get(cursor, cls, pk)

        set_clause = _clause_generator(data)

        pk_col = _resolve_identifier(cls, pk)

        cursor.execute(
            query.format(
                table=cls.get_table_identifier(), id_col=pk_col, set_clause=set_clause
            ),
            {**data, "_pk_val": pk},
        )

        cursor.row_factory = class_row(cls)
        if not (obj := cursor.fetchone()):
            raise ObjectNotFound(cls.__name__, str(pk))

        return obj

    def update(
        self,
        cls: type[T],
        pk: PrimaryKey,
        req: BaseModel,
    ) -> T:
        """Update an existing record's metadata using its primary key and update payload.

        Partial updates are supported; unset or None fields in the request model
        are excluded from the SQL update clause.

        Args:
            cls: The DBbase entity model class to update.
            pk: The primary key (int or UUID) of the target record.
            req: A Pydantic request model containing fields to set.

        Returns:
            The updated entity instance re-hydrated from the database.

        Raises:
            ObjectNotFound: If no database record matches the provided primary key.
        """
        return self._update(cls, pk, req)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _bulk_update(
        self,
        cursor: Cursor[T],
        cls: type[T],
        req: BaseModel,
        scope: dict[str, Any],
    ) -> int:
        """ """
        query = sql.SQL("""
            UPDATE {table}
            SET {set_clause}, modified = CURRENT_TIMESTAMP
            WHERE {where_clause}
        """)

        data = req.model_dump(exclude_unset=True, exclude_none=True)

        # if there is nothing to change, technically the operation was sucecssful :D
        if not data:
            return 0

        set_clause = _clause_generator(data)
        where_clause = _clause_generator(scope, sep=sql.SQL(" AND "), prefix="_scope_")

        scope_params = {f"_scope_{k}": v for k, v in scope.items()}

        cursor.execute(
            query.format(
                table=cls.get_table_identifier(),
                set_clause=set_clause,
                where_clause=where_clause,
            ),
            {**data, **scope_params},
        )

        return cursor.rowcount

    def bulk_update(
        self,
        cls: type[T],
        req: BaseModel,
        scope: dict[str, Any],
    ) -> int:
        """Perform a multi-row scoped update across entities matching filter criteria.

        Executes a bulk SQL UPDATE statement on records that match all key-value pairs
        specified in the scope dictionary. Unset or None fields in the request model
        are excluded from the update.

        Args:
            cls: The DBbase entity model class to update.
            req: A Pydantic request model containing fields and values to update.
            scope: A dictionary of column-value condition pairs defining the WHERE
                filter scope (e.g., {"user_id": 123, "status": "active"}).

        Returns:
            The total number of rows modified in the database.

        Raises:
            ValueError: If the `scope` dictionary is empty.
        """
        return self._bulk_update(cls=cls, req=req, scope=scope)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # GET
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get(self, cursor: Cursor[T], cls: Type[T], pk: PrimaryKey) -> T:
        """Internal get method."""
        cursor.row_factory = class_row(cls)
        query = sql.SQL(" SELECT * FROM {table} WHERE {id_col} = %s ")

        pk_col = _resolve_identifier(cls, pk)

        cursor.execute(
            query.format(table=cls.get_table_identifier(), id_col=pk_col),
            (pk,),
        )
        obj = cursor.fetchone()

        if not obj:
            raise ObjectNotFound(cls.__name__, str(pk))

        return obj

    def get(self, cls: Type[T], pk: PrimaryKey) -> T:
        """Selects a single record by primary key and returns an instantiated object."""
        return self._get(cls, pk)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_children(
        self,
        cursor: Cursor[T],
        child_cls: type[T],
        parent_cls: type[DBbase],
        parent_pk: PrimaryKey,
    ) -> list[T]:
        """Internal get_children method."""
        if isinstance(parent_pk, UUID):
            parent_obj = self._get(cursor, parent_cls, parent_pk)

            parent_pk = getattr(parent_obj, parent_cls.__pk_name__)

        foreign_key = f"{parent_cls.__name__.lower()}_id"

        query = sql.SQL("SELECT * FROM {table} WHERE {fk_col} = %s;").format(
            table=child_cls.get_table_identifier(),
            fk_col=sql.Identifier(foreign_key),
        )

        cursor.row_factory = class_row(child_cls)
        cursor.execute(query, (parent_pk,))
        return cursor.fetchall()

    def get_children(
        self,
        child_cls: type[T],
        parent_cls: type[DBbase],
        parent_pk: PrimaryKey,
    ) -> list[T]:
        """Fetches child records owned by a parent record.

        Args:
            child_cls: The child model class to return.
            parent_cls: The parent model class.
            parent_pk: The primary key of the parent record.
            foreign_key: Foreign key column name on the child. Inferred if omitted.

        Returns:
            list[T]: The child records, or an empty list if none exist.

        Raises:
            ObjectNotFound: If the parent record does not exist.
        """
        return self._get_children(child_cls, parent_cls, parent_pk)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # WHERE
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _where(self, cursor: Cursor[T], cls: Type[T], scope: dict[str, Any]) -> list[T]:
        """Internal where method."""
        if not scope:
            raise ValueError("At least one filter condition must be provided.")

        # Build parameterized WHERE clause (e.g., image_uuid = %s)
        where_clause = _clause_generator(scope, sep=sql.SQL(" AND "), prefix="_scope_")
        scope_params = {f"_scope_{k}": v for k, v in scope.items()}

        query = sql.SQL("SELECT * FROM {table} WHERE {where_clause};").format(
            table=cls.get_table_identifier(),
            where_clause=where_clause,
        )

        cursor.row_factory = class_row(cls)
        cursor.execute(query, scope_params)
        return cursor.fetchall()

    def where(self, cls: Type[T], scope: dict[str, Any]) -> list[T]:
        """
        Fetches records matching column filter criteria.

            Args:
                cls: The target model class to return.
                **filters: Key-value pairs to filter by (e.g., status="active").

            Returns:
                list[T]: Records matching all criteria.

            Raises:
                ValueError: If no filter parameters are passed.
                ObjectNotFound: If no matching records are found.
        """
        return self._where(cls, scope)

    @connect
    def _get_related(
        self,
        cursor: Cursor[T],
        relation_cls: Type[Relationbase],
        target_cls: Type[T],
        scope: dict[str, Any],
        fk_field: str,
    ) -> list[T]:
        """Internal method to fetch target models via a relation join table."""
        if not scope:
            raise ValueError("At least one filter condition must be provided.")

        # Build parameterized WHERE clause targeting relation scope fields
        where_clause = _clause_generator(scope, sep=sql.SQL(" AND "), prefix="_scope_")
        scope_params = {f"_scope_{k}": v for k, v in scope.items()}

        query = sql.SQL(
            "SELECT t.* FROM {target_table} t "
            "JOIN {relation_table} r ON t.{target_pk} = r.{fk_field} "
            "WHERE {where_clause};"
        ).format(
            target_table=target_cls.get_table_identifier(),
            relation_table=relation_cls.get_table_identifier(),
            target_pk=sql.Identifier(target_cls.__pk_name__),
            fk_field=sql.Identifier(fk_field),
            where_clause=where_clause,
        )

        cursor.row_factory = class_row(target_cls)
        cursor.execute(query, scope_params)
        return cursor.fetchall()

    def get_related(
        self,
        relation_cls: Type[Relationbase],
        target_cls: Type[T],
        scope: dict[str, Any],
        fk_field: str,
    ) -> list[T]:
        """
        Fetches target entity models joined through a BaseRelation junction table.

            Args:
                relation_cls: The BaseRelation junction model class.
                target_cls: The concrete entity model class to hydrate and return.
                scope: Key-value filter pairs applied to the junction table.
                fk_field: The foreign key column name on the junction table linking to target_cls.

            Returns:
                list[T]: Concrete entity records matching the criteria.

            Raises:
                ValueError: If scope is empty.
        """
        return self._get_related(relation_cls, target_cls, scope, fk_field)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # EXISTS
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @connect
    def _exists(
        self,
        cursor: Cursor[Any],
        cls: type[DBbase],
        pk: PrimaryKey,
    ) -> bool:
        """Internal exists method"""
        query = sql.SQL("SELECT EXISTS(SELECT 1 FROM {table} WHERE {id_col} = %s);")

        pk_col = _resolve_identifier(cls, pk)

        cursor.execute(
            query.format(
                table=cls.get_table_identifier(),
                id_col=pk_col,
            ),
            (pk,),
        )
        res = cursor.fetchone()

        if not res or res[0] is False:
            raise ObjectNotFound(cls.__name__, str(pk))

        return True

    def exists(self, cls: type[DBbase], pk: PrimaryKey) -> bool:
        """Asserts that a record exists in the database.

        Args:
            cls: The model class to check.
            pk: The primary key of the record.

        Returns:
            bool: True if the record exists.

        Raises:
            ObjectNotFound: If no record matches the given primary key.
        """
        return self._exists(cls, pk)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # DELETE
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _delete(self, cursor: Cursor[T], cls: type[T], pk: PrimaryKey) -> bool:
        """internal delete method"""
        query = sql.SQL("""
        DELETE FROM {table}
        WHERE {id_col} = %(_pk_val)s
        """)

        pk_col = _resolve_identifier(cls, pk)

        cursor.row_factory = class_row(cls)
        cursor.execute(
            query.format(
                table=cls.get_table_identifier(),
                id_col=pk_col,
            ),
            {"_pk_val": pk},
        )

        return True

    def delete(self, cls: type[T], pk: PrimaryKey) -> bool:
        """Delete an object from the database

        Args:
        cls: the model class to delete.
        pk: The primary key of the record.

        Returns:
            bool: True if the operation was successful.
        """
        return self._delete(cls, pk)
