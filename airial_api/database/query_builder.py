# Psycopg3 sql based helpers
# Author: Michael B. Lance

# ---------------------------------------------------------------------------------------------------------------------------

from typing import Any
from uuid import UUID
from database.object_models.base import PrimaryKey

import psycopg.sql as sql

# ---------------------------------------------------------------------------------------------------------------------------


def filter_by_object_ids(
    pfx: str, id_field: str, ids: list[PrimaryKey]
) -> tuple[sql.Composable, dict]:
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


# ---------------------------------------------------------------------------------------------------------------------------
# Composable Join & Traversal Helpers
# ---------------------------------------------------------------------------------------------------------------------------


def get_column_names(cls: type) -> set[str]:
    """Return set of column/field names for a model class."""
    if hasattr(cls, "__dataclass_fields__"):
        return set(cls.__dataclass_fields__.keys())
    if hasattr(cls, "__annotations__"):
        return set(cls.__annotations__.keys())
    return set()


def has_column(cls: type, col_name: str) -> bool:
    """Check if model class has a specific column/field."""
    return col_name in get_column_names(cls)


def resolve_join_columns(
    model_left: type,
    model_right: type,
    explicit_col: str | None = None,
) -> tuple[str, str]:
    """Resolve the join column names for two adjacent models (left_col, right_col)."""
    if explicit_col:
        if has_column(model_left, explicit_col) and has_column(model_right, explicit_col):
            return (explicit_col, explicit_col)
        if has_column(model_left, explicit_col):
            pk_r = getattr(model_right, "__pk_name__", None)
            if pk_r and has_column(model_right, pk_r):
                return (explicit_col, pk_r)
        if has_column(model_right, explicit_col):
            pk_l = getattr(model_left, "__pk_name__", None)
            if pk_l and has_column(model_left, pk_l):
                return (pk_l, explicit_col)
        raise ValueError(
            f"Cannot resolve explicit join column '{explicit_col}' between {model_left} and {model_right}"
        )

    pk_left = getattr(model_left, "__pk_name__", None)
    pk_right = getattr(model_right, "__pk_name__", None)

    # 1. Left model has right model's primary key (e.g. Annotation has image_id)
    if pk_right and has_column(model_left, pk_right):
        return (pk_right, pk_right)

    # 2. Right model has left model's primary key (e.g. SurveysHerdUnits has herd_unit_id)
    if pk_left and has_column(model_right, pk_left):
        return (pk_left, pk_left)

    # 3. Junction table __key__ match
    keys_left = getattr(model_left, "__key__", ())
    for k in keys_left:
        if has_column(model_right, k):
            return (k, k)

    keys_right = getattr(model_right, "__key__", ())
    for k in keys_right:
        if has_column(model_left, k):
            return (k, k)

    # 4. Common _id columns
    common_ids = [
        c
        for c in (get_column_names(model_left) & get_column_names(model_right))
        if c.endswith("_id")
    ]
    if len(common_ids) == 1:
        return (common_ids[0], common_ids[0])

    # 5. Any common columns excluding generic metadata
    exclude = {"uuid", "created", "modified", "name", "description"}
    common = (get_column_names(model_left) & get_column_names(model_right)) - exclude
    if len(common) == 1:
        c = common.pop()
        return (c, c)

    raise ValueError(
        f"Cannot automatically determine join columns between {model_left} and {model_right}. "
        "Specify an explicit join column via a tuple: (Model, 'column_name')."
    )


def can_join(model_a: type, model_b: type) -> bool:
    """Check whether two models can be automatically joined."""
    try:
        resolve_join_columns(model_a, model_b)
        return True
    except ValueError:
        return False


def build_traversal_query(
    child_cls: type,
    parent_cls: type,
    via: list[type | tuple[type, str]],
) -> sql.Composed:
    """Build a composable multi-hop SQL query from child_cls to parent_cls via intermediate models.

    Produces a query of the form:
        SELECT DISTINCT t0.*
        FROM child_table t0
        JOIN via_1 t1 ON t0.col = t1.col
        ...
        WHERE tn.parent_pk_col = %s;
    """
    if not via:
        raise ValueError("via list cannot be empty for build_traversal_query")

    # Normalize hops into list of (model_cls, explicit_col)
    hops: list[tuple[type, str | None]] = []
    for item in via:
        if isinstance(item, tuple):
            hops.append((item[0], item[1]))
        else:
            hops.append((item, None))

    # Auto-detect hop ordering:
    # If child connects to the last hop but not the first, user passed parent-to-child order.
    # Reverse so hops[0] is adjacent to child_cls.
    if len(hops) > 1:
        first_cls = hops[0][0]
        last_cls = hops[-1][0]
        if not can_join(child_cls, first_cls) and can_join(child_cls, last_cls):
            hops.reverse()

    # Build sequence of tables starting with child_cls at index 0 (aliases: t0, t1, t2, ...)
    join_clauses: list[sql.Composed] = []
    current_cls = child_cls
    current_alias = sql.Identifier("t0")

    for i, (hop_cls, explicit_col) in enumerate(hops, start=1):
        hop_alias = sql.Identifier(f"t{i}")
        col_left, col_right = resolve_join_columns(current_cls, hop_cls, explicit_col)

        join_clauses.append(
            sql.SQL(
                "JOIN {table} {alias} ON {left_alias}.{col_left} = {alias}.{col_right}"
            ).format(
                table=hop_cls.get_table_identifier(),
                alias=hop_alias,
                left_alias=current_alias,
                col_left=sql.Identifier(col_left),
                col_right=sql.Identifier(col_right),
            )
        )
        current_cls = hop_cls
        current_alias = hop_alias

    # Determine filter condition against parent_cls
    parent_pk_name = getattr(parent_cls, "__pk_name__", None)
    if not parent_pk_name:
        raise ValueError(f"Parent class {parent_cls} must have __pk_name__")

    if has_column(current_cls, parent_pk_name):
        where_clause = sql.SQL("WHERE {last_alias}.{fk_col} = %s").format(
            last_alias=current_alias,
            fk_col=sql.Identifier(parent_pk_name),
        )
    else:
        # Join parent_cls as final hop
        parent_alias = sql.Identifier(f"t{len(hops) + 1}")
        col_left, col_right = resolve_join_columns(current_cls, parent_cls)
        join_clauses.append(
            sql.SQL(
                "JOIN {table} {alias} ON {left_alias}.{col_left} = {alias}.{col_right}"
            ).format(
                table=parent_cls.get_table_identifier(),
                alias=parent_alias,
                left_alias=current_alias,
                col_left=sql.Identifier(col_left),
                col_right=sql.Identifier(col_right),
            )
        )
        where_clause = sql.SQL("WHERE {parent_alias}.{pk_col} = %s").format(
            parent_alias=parent_alias,
            pk_col=sql.Identifier(parent_pk_name),
        )

    all_joins = sql.SQL(" ").join(join_clauses)

    query = sql.SQL(
        "SELECT DISTINCT t0.* FROM {child_table} t0 {joins} {where};"
    ).format(
        child_table=child_cls.get_table_identifier(),
        joins=all_joins,
        where=where_clause,
    )

    return query
