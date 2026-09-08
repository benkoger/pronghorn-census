# Psycopg3 sql based helpers
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from typing import Tuple, Any
from uuid import UUID
from database.object_models.base import PrimaryKey

import psycopg.sql as sql

# ---------------------------------------------------------------------------------------------------------------------------


def filter_by_object_ids(
    pfx: str, id_field: str, ids: list[PrimaryKey]
) -> Tuple[sql.Composable, dict]:
    """ """
    data = {f"{pfx}_ints": [], f"{pfx}_uuids": []}

    for id_val in ids:
        if isinstance(id_val, int):
            data[f"{pfx}_ints"].append(id_val)
        elif isinstance(id_val, UUID):
            data[f"{pfx}_uuids"].append(id_val)

    return (
        sql.SQL(
            "{prefix}.{ident} = ANY({i_placehodler}::int[]) OR {prefix}.uuid = ANY({u_placeholder}::uuid[])"
        ).format(
            prefix=sql.Identifier(pfx),
            ident=sql.Identifier(id_field),
            i_placehodler=sql.Placeholder(f"{pfx}_ints"),
            u_placeholder=sql.Placeholder(f"{pfx}_uuids"),
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


def resolve_identifier(cls, key: PrimaryKey) -> sql.Identifier:
    """Determine which key type a PrimaryKey object is"""
    match key:
        case int():
            pk_col = cls.get_pk_identifier()
        case UUID():
            pk_col = sql.Identifier("uuid")
        case _:
            raise Exception(f"type {type(key)}")

    return pk_col
