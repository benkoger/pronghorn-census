# Psycopg3 sql based helpers
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from collections import deque
from typing import Tuple, Any, Optional
from uuid import UUID
from database.object_models.base import PrimaryKey, DBbase

import psycopg.sql as sql

# ---------------------------------------------------------------------------------------------------------------------------

SCHEMA_GRAPH: dict[tuple[str, str], list[tuple[tuple[str, str], str]]] = {
    ("core", "predictions"): [(("core", "images"), "image_id")],
    ("core", "reviewed_area"): [(("core", "images"), "image_id")],
    ("core", "annotations"): [(("core", "images"), "image_id")],
    ("core", "image_metadata"): [(("core", "images"), "image_id")],
    ("core", "image_footprints"): [(("core", "images"), "image_id")],
    ("core", "images"): [
        (("projectmanagement", "surveys"), "survey_id"),
        (("projectmanagement", "herd_units"), "herd_unit_id"),
    ],
    ("projectmanagement", "labels"): [(("projectmanagement", "schemas"), "schema_id")],
    ("projectmanagement", "models"): [(("projectmanagement", "schemas"), "schema_id")],
    ("core", "am_units"): [
        (("projectmanagement", "active_measurements"), "active_measurement_id")
    ],
    ("projectmanagement", "surveys"): [(("projectmanagement", "projects"), "project_id")],
    ("projectmanagement", "herd_units"): [(("projectmanagement", "projects"), "project_id")],
}


def find_relationship_path(
    start_table: tuple[str, ...],
    end_table: tuple[str, ...],
) -> Optional[list[tuple[tuple[str, ...], tuple[str, ...], str]]]:
    """Finds the shortest path of (from_table, to_table, fk_col) from start to end."""
    if start_table == end_table:
        return []

    queue: deque[list[tuple[tuple[str, ...], Optional[tuple[str, ...]], Optional[str]]]] = deque(
        [[(start_table, None, None)]]
    )
    visited = {start_table}

    while queue:
        path = queue.popleft()
        current_table = path[-1][0]

        if current_table == end_table:
            edges = []
            for i in range(len(path) - 1):
                edges.append((path[i][0], path[i + 1][0], path[i + 1][2]))  # type: ignore[arg-type]
            return edges

        for next_table, fk in SCHEMA_GRAPH.get(current_table, []):  # type: ignore[arg-type]
            if next_table not in visited:
                visited.add(next_table)
                queue.append(path + [(next_table, current_table, fk)])

    return None

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

    Traverses the schema relationship graph to construct the exact sequence of joins
    from child to parent without redundant or duplicate joins.
    """
    start_key = tuple(cls.__table__._obj)
    end_key = tuple(parent_cls.__table__._obj)

    edges = find_relationship_path(start_key, end_key)
    if edges is None:
        pk_name = parent_cls.__pk__._obj[-1]
        if hasattr(cls, pk_name):
            edges = [(start_key, end_key, pk_name)]
        else:
            raise ValueError(
                f"No relationship path found between {cls.__name__} and {parent_cls.__name__}"
            )

    joins: list[sql.Composable] = []

    if len(edges) == 1:
        # Direct relationship (e.g. Prediction -> Image)
        _, _, fk_col = edges[0]
        fk_ident = sql.Identifier(fk_col)

        if isinstance(parent_pk, UUID):
            joins.append(
                sql.SQL("JOIN {parent_table} ON {parent_table}.{fk} = {child_table}.{fk}").format(
                    parent_table=parent_cls.__table__,
                    child_table=cls.__table__,
                    fk=fk_ident,
                )
            )
            condition = sql.SQL("{parent_table}.uuid").format(parent_table=parent_cls.__table__)
        else:
            condition = sql.SQL("{child_table}.{fk}").format(
                child_table=cls.__table__,
                fk=fk_ident,
            )
    else:
        # Multi-hop relationship (e.g. Annotation -> Image -> Survey)
        for i in range(len(edges) - 1):
            from_t, to_t, fk_col = edges[i]
            joins.append(
                sql.SQL("JOIN {to_table} ON {to_table}.{fk} = {from_table}.{fk}").format(
                    to_table=sql.Identifier(*to_t),
                    from_table=sql.Identifier(*from_t),
                    fk=sql.Identifier(fk_col),
                )
            )

        last_inter_table = sql.Identifier(*edges[-1][0])
        final_fk = sql.Identifier(edges[-1][2])

        if isinstance(parent_pk, UUID):
            joins.append(
                sql.SQL("JOIN {parent_table} ON {parent_table}.{fk} = {inter_table}.{fk}").format(
                    parent_table=parent_cls.__table__,
                    inter_table=last_inter_table,
                    fk=final_fk,
                )
            )
            condition = sql.SQL("{parent_table}.uuid").format(parent_table=parent_cls.__table__)
        else:
            condition = sql.SQL("{inter_table}.{fk}").format(
                inter_table=last_inter_table,
                fk=final_fk,
            )

    return condition, joins
