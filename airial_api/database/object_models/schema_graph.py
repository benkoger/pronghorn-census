"""Schema relationship graph and path traversal utilities."""

# Authors: Michael B. Lance, Antigravity
# ---------------------------------------------------------------------------------------------------------------------------

from collections import deque
from typing import Optional

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
    ("core", "am_units"): [(("projectmanagement", "active_measurements"), "active_measurement_id")],
    ("projectmanagement", "surveys"): [(("projectmanagement", "projects"), "project_id")],
    ("projectmanagement", "herd_units"): [(("projectmanagement", "projects"), "project_id")],
}


def find_relationship_path(
    start_table: tuple[str, ...],
    end_table: tuple[str, ...],
) -> Optional[list[tuple[tuple[str, ...], tuple[str, ...], str]]]:
    """Find the shortest foreign key relationship path between two database tables.

    Performs a breadth-first search across the schema relationship graph to determine
    the sequence of join edges from `start_table` to `end_table`.

    Args:
        start_table: Schema and table tuple of the origin entity (e.g. ("core", "predictions")).
        end_table: Schema and table tuple of the target entity (e.g. ("projectmanagement", "surveys")).

    Returns:
        List of tuples representing join edges `(from_table, to_table, fk_col)`, an empty list
        if start and end tables are identical, or None if no relationship path exists.
    """
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
