# Psycopg3 sql based helpers
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from typing import Tuple, Any
from uuid import UUID
from database.object_models.base import PrimaryKey, DBbase

import psycopg.sql as sql

# ---------------------------------------------------------------------------------------------------------------------------


def filter_by_object_ids(
    table: sql.Identifier, pk_col: sql.Identifier, ids: list[PrimaryKey]
) -> Tuple[sql.Composable, dict]:
    """Builds SQL to filter by integer primary keys or UUIDs."""
    data = {"_filter_ints": [], "_filter_uuids": []}

    for id_val in ids:
        if isinstance(id_val, int):
            data["_filter_ints"].append(id_val)
        elif isinstance(id_val, UUID):
            data["_filter_uuids"].append(id_val)

    return (
        sql.SQL(
            "{table}.{pk_col} = ANY({i_placeholder}::int[]) OR {table}.uuid = ANY({u_placeholder}::uuid[])"
        ).format(
            table=table,
            pk_col=pk_col,
            i_placeholder=sql.Placeholder("_filter_ints"),
            u_placeholder=sql.Placeholder("_filter_uuids"),
        ),
        data,
    )


def clause_generator(
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


def resolve_identifier(cls: type[DBbase], key: PrimaryKey) -> sql.Identifier:
    """Determine which key type a PrimaryKey object is"""
    match key:
        case int():
            pk_col = cls.__pk__
        case UUID():
            pk_col = sql.Identifier("uuid")
        case _:
            raise Exception(f"type {type(key)}")

    return pk_col


def resolve_parent_filter(
    cls: type[DBbase],
    parent_cls: type[DBbase],
    parent_pk: PrimaryKey,
) -> tuple[sql.Composable, list[sql.Composable]]:
    """Resolves foreign key filter condition and required joins for a parent class.

    Supports direct parent-child relationships and indirect relationships
    defined via __parent_table__ and __parent_fk__.
    Uses sql.Identifier directly without deconstruction.
    """
    joins: list[sql.Composable] = []

    # 1. Determine which table holds parent_cls.__pk__
    if cls.__parent_table__ and cls.__parent_fk__:
        inter_table = cls.__parent_table__
        inter_fk = cls.__parent_fk__
        joins.append(
            sql.SQL("JOIN {inter_table} ON {inter_table}.{inter_fk} = {child_table}.{inter_fk}").format(
                inter_table=inter_table,
                inter_fk=inter_fk,
                child_table=cls.__table__,
            )
        )
        target_table = inter_table
    else:
        target_table = cls.__table__

    # 2. Condition depends on whether parent_pk is UUID or int
    if isinstance(parent_pk, UUID):
        # The parent is already joined when it is the table the child reaches its parents through
        if target_table != parent_cls.__table__:
            joins.append(
                sql.SQL("JOIN {parent_table} ON {parent_table}.{pk} = {target_table}.{pk}").format(
                    parent_table=parent_cls.__table__,
                    pk=parent_cls.__pk__,
                    target_table=target_table,
                )
            )
        condition = sql.SQL("{parent_table}.uuid").format(parent_table=parent_cls.__table__)
    else:
        condition = sql.SQL("{target_table}.{pk}").format(
            target_table=target_table,
            pk=parent_cls.__pk__,
        )

    return condition, joins
