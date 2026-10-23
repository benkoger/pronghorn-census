# Psycopg3 database abstraction layer for airial_apidatabase.py
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------#


import atexit
from datetime import date
import uuid
from functools import wraps
from typing import (
    Any,
    Callable,
    Optional,
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
from psycopg import Connection, Cursor
from psycopg.errors import DatabaseError
from psycopg.rows import class_row, dict_row, tuple_row
from psycopg.types.enum import EnumInfo, register_enum
from psycopg_pool import ConnectionPool

from database.object_models.autocropper import AutoCropperBatchQuery
from database.object_models.base import DBbase, T, Relationbase, PrimaryKey, BulkRequest

from database.object_models.core.activity import ActivityType
from database.object_models.core.images import (
    Image,
    RAQuery,
    ReviewedArea,
    UpdateImageReq,
)
from database.object_models.project_management.herd_units import HerdUnit
from database.object_models.project_management.models import Model, ModelType
from database.object_models.project_management.surveys import Survey
from database.object_models.user_management.users import User
from database.query_builder import (
    filter_by_object_ids,
    resolve_identifier,
    clause_generator,
)

from .errors import (
    FailedToCreate,
    ObjectNotFound,
)

# ---------------------------------------------------------------------------------------------------------------------------

EXT_KEY = "base"


def configure_connection(conn: Connection):
    for enum_name, enum_cls in [
        ("projectmanagement.model_type", ModelType),
        ("core.activity_type", ActivityType),
    ]:
        try:
            info = EnumInfo.fetch(conn, enum_name)
            if not info:
                info = EnumInfo.fetch(conn, enum_name.split(".")[-1])
            if info:
                mapping = [(member, member.value) for member in enum_cls]
                register_enum(info, context=conn, enum=enum_cls, mapping=mapping)
        except Exception:
            continue


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
            configure=configure_connection,
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
    # INSERT
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _insert(self, cursor: Cursor[T], cls: type[T], req: BaseModel, *args) -> T:
        """Internal insert method."""
        if not (result := cls._create(cursor, req, *args)):
            raise FailedToCreate(cls.__name__)

        obj, relations = result

        if len(relations) > 0:
            self.write_spice_relationships(relations)

        return obj

    def insert(self, cls: type[T], req: BaseModel, *args) -> T:
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
        return self._insert(cls, req, *args)

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
            SET {set_clause}{modified_statement}
            WHERE {id_col} = %(_pk_val)s
            RETURNING *;
        """)

        if hasattr(cls, "modified"):
            modified_statement = sql.SQL(", modified = CURRENT_TIMESTAMP ")
        else:
            modified_statement = sql.SQL("")

        data = req.model_dump(exclude_unset=True, exclude_none=True)

        if not data:
            return self._get(cursor, cls, pk)

        set_clause = clause_generator(data)

        pk_col = resolve_identifier(cls, pk)

        cursor.execute(
            query.format(
                table=cls.get_table_identifier(),
                id_col=pk_col,
                set_clause=set_clause,
                modified_statement=modified_statement,
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

        set_clause = clause_generator(data)
        where_clause = clause_generator(scope, sep=sql.SQL(" AND "), prefix="_scope_")

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

        pk_col = resolve_identifier(cls, pk)

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

        query = sql.SQL("SELECT * FROM {table} WHERE {fk_col} = %s;").format(
            table=child_cls.get_table_identifier(),
            fk_col=parent_cls.get_pk_identifier(),
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

    @connect
    def _get_related(
        self,
        cursor: Cursor[T],
        relation_cls: Type[Relationbase],
        target_cls: Type[T],
        scope: dict[str, Any],
    ) -> list[T]:
        """Internal method to fetch target models via a relation join table."""
        if not scope:
            raise ValueError("At least one filter condition must be provided.")

        # Build parameterized WHERE clause targeting relation scope fields
        where_clause = clause_generator(scope, sep=sql.SQL(" AND "), prefix="_scope_")
        scope_params = {f"_scope_{k}": v for k, v in scope.items()}

        query = sql.SQL(
            "SELECT t.* FROM {target_table} t "
            "JOIN {relation_table} r ON t.{target_pk} = r.{fk_field} "
            "WHERE r.{where_clause};"
        ).format(
            target_table=target_cls.get_table_identifier(),
            relation_table=relation_cls.get_table_identifier(),
            target_pk=sql.Identifier(target_cls.__pk_name__),
            fk_field=sql.Identifier(target_cls.__pk_name__),
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
        return self._get_related(relation_cls, target_cls, scope)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _bulk_get(self, cursor: Cursor[T], cls: type[T], req: BulkRequest) -> list[T]:
        """Internal bulk_get method."""
        cursor.row_factory = class_row(cls)
        query = sql.SQL("SELECT * FROM {table} as bobj")

        p_filters, data = filter_by_object_ids("bobj", cls.__pk_name__, req.object_ids)

        return cursor.execute(
            sql.SQL("{q} WHERE {p}").format(
                q=query.format(table=cls.get_table_identifier()), p=p_filters
            ),
            data,
        ).fetchall()

    def bulk_get(self, cls: type[T], req: BulkRequest) -> list[T]:
        """
        Fetch a collection of entities efficiently using a collection of primary keys

        Args:
            cls: The DBbase entity model class to fetch.
            req: A pydantic request model including PrimaryKey identifiers

        Returns:
            A list of entities according to the provided identifiers

        Raises:
            ObjectNotFound: If one or more provided identifiers do not have a corresponding entity.

        """
        return self._bulk_get(cls, req)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # WHERE
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _where(self, cursor: Cursor[T], cls: Type[T], scope: dict[str, Any]) -> list[T]:
        """Internal where method."""
        if not scope:
            raise ValueError("At least one filter condition must be provided.")

        # Build parameterized WHERE clause (e.g., image_uuid = %s)
        where_clause = clause_generator(scope, sep=sql.SQL(" AND "), prefix="_scope_")
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

        pk_col = resolve_identifier(cls, pk)

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

        pk_col = resolve_identifier(cls, pk)

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

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Batching -- Complex Relations
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_auto_crop_batch(
        self, cursor: Cursor[dict], params: AutoCropperBatchQuery, user: User
    ) -> dict[str, str | int | list[int]]:
        """ """
        q_params = {
            "survey_id": self._get(cursor, Survey, params.survey_id).survey_id,
            "herd_unit_id": self._get(
                cursor, HerdUnit, params.herd_unit_id
            ).herd_unit_id,
            "model_id": self._get(cursor, Model, params.model_id).model_id,
            "labels": params.label,
            "score": params.min_confidence,
            "batch_size": params.batch_size,
        }

        cursor.row_factory = dict_row
        query = sql.SQL(""" 
		    WITH SelectedImages AS (
    SELECT I.image_id
    FROM core.images I
    INNER JOIN core.predictions P ON I.image_id = P.image_id
    WHERE I.herd_unit_id = %(herd_unit_id)s
      AND I.survey_id = %(survey_id)s
      AND I.opened_by_user_id = 0
      AND P.model_id = %(model_id)s
      AND P.reviewed_by_user_id = 0  
      AND P.label = ANY(%(labels)s)
      AND P.score > %(score)s
    GROUP BY I.image_id
    ORDER BY MAX(P.score) DESC  
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
            ORDER BY P.score DESC -- Internal array stays perfectly ordered
        ) AS predictions,
        MAX(P.score) AS max_score -- Kept for outer sorting parity
    FROM core.images I
    INNER JOIN core.predictions P ON I.image_id = P.image_id
    WHERE I.image_id IN (SELECT image_id FROM SelectedImages)
      AND P.label = ANY(%(labels)s)
      AND P.score > %(score)s
      AND P.model_id = %(model_id)s
    GROUP BY I.image_id
    ORDER BY max_score DESC) AS img_preds;
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
    ) -> dict[str, str | int | list[int]]:
        """ """
        return self._get_auto_crop_batch(req, user)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Legacy Holdovers -- Not enough time to rewrite
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # TODO: These methods need to be folded into the greater generics pattern !techdebt!

    @connect
    def _get_survey_images(
        self, cursor: Cursor[Any], survey_id: UUID, limit: int, offset: int
    ) -> tuple[list[Image], int]:
        """ """

        query_1 = sql.SQL("SELECT COUNT(*) FROM core.images WHERE survey_id = %s")
        query_2 = sql.SQL(""" 
            SELECT * FROM core.images 
            WHERE survey_id = %s
            ORDER BY image_id ASC 
            LIMIT %s OFFSET %s; 
        """)

        survey = self._get(cursor, Survey, survey_id)

        cursor.row_factory = tuple_row
        res = cursor.execute(query_1, (survey.survey_id,)).fetchone()

        if not res:
            return [], 0

        total_images = int(res[0])

        cursor.row_factory = class_row(Image)

        images = cursor.execute(query_2, (survey.survey_id, limit, offset)).fetchall()

        return images, total_images

    def get_survey_images(
        self, survey_id: UUID, limit: int, offset: int
    ) -> tuple[list[Image], int]:
        """ """
        return self._get_survey_images(survey_id, limit, offset)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_survey_annotated_images(
        self,
        cursor: Cursor[dict],
        label_ids: list[int],
        date_range: tuple[date, date] | None,
        survey_ids: list[int] | None,
        herd_unit_ids: list[int] | None,
    ):
        """ """
        cursor.row_factory = dict_row

        params_1 = []
        placeholders: dict[str, list[int] | date] = {"label_ids": label_ids}

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
        label_ids: list[int],
        date_range: tuple[date, date] | None,
        survey_ids: list[int] | None,
        herd_unit_ids: list[int] | None,
    ):
        """ """
        return self._get_survey_annotated_images(
            label_ids, date_range, survey_ids, herd_unit_ids
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_reviewed_areas(
        self, cursor: Cursor[ReviewedArea], req: RAQuery
    ) -> list[ReviewedArea]:
        """ """
        query = sql.SQL(""" 
			SELECT ra.* FROM core.reviewed_area ra
			JOIN core.images i on i.image_id = ra.image_id
			WHERE {parameter_field} 
		""")

        params = []
        placeholders: dict[str, list[int] | date | int] = {}

        if req.herd_unit_id:
            herd_unit = self._get(cursor, HerdUnit, req.herd_unit_id[0])
            params.append(sql.SQL("i.herd_unit_id = ANY(%(herd_unit_ids)s)"))
            placeholders["herd_unit_ids"] = [herd_unit.herd_unit_id]

        if req.survey_id:
            survey = self._get(cursor, Survey, req.survey_id[0])
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

    def get_reviewed_areas(self, req: RAQuery) -> list[ReviewedArea]:
        """ """
        return self._get_reviewed_areas(req)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @connect
    def _get_crop_to_review(
        self, cursor: Cursor[ReviewedArea], req: RAQuery, user: User
    ) -> Optional[ReviewedArea]:
        """Fetch a batch of reviewed areas that have yet to be reviewed."""
        reviewed_areas = self._get_reviewed_areas(cursor, req)

        if len(reviewed_areas) > 0:
            image = self._get(cursor, Image, reviewed_areas[0].image_id)
            self._update(
                cursor,
                Image,
                image.image_id,
                UpdateImageReq(opened_by_user_id=user.user_id),
            )

            return reviewed_areas[0]
        else:
            return None

    def get_crop_to_review(self, req: RAQuery, user: User) -> Optional[ReviewedArea]:
        """ """
        return self._get_crop_to_review(req, user)
