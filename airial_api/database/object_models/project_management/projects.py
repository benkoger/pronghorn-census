# Class definition for Project objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
"""Project database models and schemas."""

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
    def ensure_list(cls, value):
        """Ensure project ID is a list."""
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

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def _create(
        cls, cursor: Cursor[Self], req: createProjectReq, user: User, role: Role
    ) -> tuple[Self, list[RelationshipUpdate]] | None:
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

    def serialize(self):
        """Serialize project model to a dictionary."""
        return Project.Response.model_validate(self).model_dump(mode="json")
