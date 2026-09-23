# Class definition for Project objects in the database
# Author: Michael B. Lance
# ---------------------------------------------------------------------------------------------------------------------------
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Self, Union
from uuid import UUID

from authzed.api.v1 import RelationshipUpdate
import psycopg.sql as sql
from psycopg import Cursor
from psycopg.rows import class_row
from pydantic import BaseModel, ConfigDict, field_validator

from database.object_models.user_management.roles import Role
from database.object_models.user_management.users import User

from ..base import DBbase, Keyring, create_spice_update

# ---------------------------------------------------------------------------------------------------------------------------


class ProjectQuery(BaseModel):
    project_id: Optional[List[Union[int, UUID]]] = None

    @field_validator("project_id", mode="before")
    @classmethod
    def ensure_list(cls, value):
        if isinstance(value, list):
            return value
        return [value]


# ---------------------------------------------------------------------------------------------------------------------------


class createProjectReq(BaseModel):
    name: str
    organization_ids: Keyring


# ---------------------------------------------------------------------------------------------------------------------------


@dataclass
class Project(DBbase):
    """Dataclass for representing projects from the databse"""

    project_id: int
    name: str
    created: datetime
    modified: datetime
    uuid: UUID

    __tablename__: str = "projects"
    __schema__: str = "projectmanagement"
    __pk_name__: str = "project_id"

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    class Response(BaseModel):
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
    ) -> Optional[tuple[Self, list[RelationshipUpdate]]]:
        cursor.row_factory = class_row(cls)
        query = sql.SQL("""
            WITH new_project AS (
                INSERT INTO projectmanagement.projects (name)
                VALUES (%(name)s)
                RETURNING *
            )
            INSERT INTO usermanagement.organizations_projects (project_id, organization_id)
            VALUES ((SELECT project_id FROM new_project), %(organization_id)s);

            INSERT INTO projectmanagement.projects_users (project_id, user_id, role_id)
            VALUES ((SELECT project_id FROM new_project), %(user_id)s, %(role_id)s);

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
            create_spice_update(
                "project", project.uuid, "user", user.uuid, "annotator"
            ),
        ]

        return project, spice_updates

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def serialize(self):
        return Project.Response.model_validate(self).model_dump(mode="json")
