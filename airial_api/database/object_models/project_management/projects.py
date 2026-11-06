"""Project database models and schemas."""

# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Self
from uuid import UUID

import psycopg.sql as sql
from authzed.api.v1 import RelationshipUpdate
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict, field_validator

from database.object_models.user_management.roles import Role
from database.object_models.user_management.users import User

from ..base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class ProjectQuery(BaseModel):
    """Query parameters for projects."""

    project_id: list[int | UUID] | None = None

    @field_validator("project_id", mode="before")
    @classmethod
    def ensure_list(cls, value: int | UUID | list[int | UUID] | None) -> list[int | UUID] | None:
        """Ensure project ID is a list.

        Args:
            value: Single project ID, list of project IDs, or None.

        Returns:
            List of project IDs or None.
        """
        if isinstance(value, list):
            return value
        return [value]


# ---------------------------------------------------------------------------------------------------------------------------


class createProjectReq(BaseModel):
    """Request schema for creating a project."""

    name: str
    organization_ids: Keyring


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Project(DBbase):
    """Dataclass for representing projects from the database."""

    project_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID

    __table__: ClassVar[sql.Identifier] = sql.Identifier("projectmanagement", "projects")
    __pk__: ClassVar[sql.Identifier] = sql.Identifier("project_id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
        """Response schema for a project."""

        model_config = ConfigDict(from_attributes=True)

        project_id: int
        name: str
        created: datetime
        modified: datetime
        uuid: UUID

    Response: ClassVar[type[BaseModel]] = Response

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: createProjectReq, user: User, role: Role
    ) -> tuple[Self, list[RelationshipUpdate]] | None:
        """Create a new project record and associated organization and user links.

        Args:
            cursor: Active database cursor.
            req: Project creation request with name and organization IDs.
            user: Creating user who will be assigned to the project.
            role: Role to assign to the user on the project.

        Returns:
            Optional tuple containing created Project and SpiceDB relationship updates, or None.
        """
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            WITH new_project AS (
                INSERT INTO projectmanagement.projects (name)
                VALUES (%(name)s)
                RETURNING *
            ),
            org_link AS (
                INSERT INTO usermanagement.organizations_projects (
                    project_id, organization_id
                )
                SELECT project_id, %(organization_id)s FROM new_project
            ),
            user_link AS (
                INSERT INTO projectmanagement.projects_users (
                    project_id, user_id, role_id
                )
                SELECT project_id, %(user_id)s, %(role_id)s FROM new_project
            )
            SELECT * FROM new_project;
        """)

        cursor.execute(
            query,
            {
                **req.model_dump(),
                "organization_id": req.organization_ids.pkey,
                "user_id": user.user_id,
                "role_id": role.role_id,
            },
        )

        if not (project := cursor.fetchone()):
            return None

        spice_updates = [
            create_spice_update(
                "project",
                project.uuid,
                "organization",
                req.organization_ids.uuid,
                "parent",
            ),
            create_spice_update("project", project.uuid, "user", user.uuid, "annotator"),
        ]

        return project, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self) -> dict:
        """Serialize project model to a dictionary.

        Returns:
            dict: Serialized project representation.
        """
        return Project.Response.model_validate(self).model_dump(mode="json")
