"""Integration and unit tests for the Projects API endpoints."""

from typing import Any
from uuid import UUID, uuid4

import pytest
from flask import Flask
from flask.testing import FlaskClient
from testing_core import APITester

from app.extensions import base
from database.object_models.project_management.herd_units import HerdUnit
from database.object_models.project_management.models import Model
from database.object_models.project_management.projects import Project
from database.object_models.project_management.schemas import Schema
from database.object_models.project_management.surveys import Survey
from database.object_models.user_management.organizations import Organization

PROJECTS_URL = "/api/v1/projects"


class TestProjects(APITester):
    """Test suite covering the `/api/v1/projects` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients,
    mocked S3 storage, and automatic database transaction rollbacks for isolation.
    """

    @pytest.fixture
    def default_organization(
        self, app: Flask, auth_client: FlaskClient
    ) -> dict[str, Any]:
        """Fetch the active organization keyring for project creation.

        Args:
            app (Flask): Flask application fixture.
            auth_client (FlaskClient): Authenticated test client fixture.

        Returns:
            dict[str, Any]: Organization keyring with integer pkey and string uuid.
        """
        with auth_client.session_transaction() as sess:
            org_uuid_str = sess.get("active_org_uuid")

        with app.app_context():
            if org_uuid_str:
                org = base.get(Organization, UUID(org_uuid_str))
            else:
                org = base.where(Organization, {})[0]
            return {"pkey": org.organization_id, "uuid": str(org.uuid)}

    @pytest.fixture
    def sample_project(self, auth_client: FlaskClient) -> dict[str, Any]:
        """Fetch an existing project belonging to the active organization.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.

        Returns:
            dict[str, Any]: Serialized project dictionary.
        """
        res = auth_client.get(PROJECTS_URL)
        assert res.status_code == 200
        projects = res.get_json()
        assert projects, "Active organization should contain at least one project."
        return projects[0]

    # -------------------------------------------------------------------------
    # 1. GET All Projects (Scoped to Active Organization Session)
    # -------------------------------------------------------------------------

    def test_get_all_projects_success(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify retrieving all projects belonging to the active organization.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(PROJECTS_URL)
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            Project.Response.model_validate(item)
            assert "project_id" in item
            assert "uuid" in item
            assert "name" in item

    # -------------------------------------------------------------------------
    # 2. GET Single Project by ID (UUID and Integer ID)
    # -------------------------------------------------------------------------

    def test_get_project_by_uuid(
        self, auth_client: FlaskClient, sample_project: dict[str, Any]
    ) -> None:
        """Verify retrieving a project by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_project (dict[str, Any]): Sample project fixture.
        """
        proj_uuid = sample_project["uuid"]
        response = auth_client.get(f"{PROJECTS_URL}/{proj_uuid}")
        assert response.status_code == 200

        data = response.get_json()
        Project.Response.model_validate(data)
        assert data["uuid"] == proj_uuid
        assert data["project_id"] == sample_project["project_id"]
        assert data["name"] == sample_project["name"]

    def test_get_project_by_int_id(
        self, auth_client: FlaskClient, sample_project: dict[str, Any]
    ) -> None:
        """Verify retrieving a project by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_project (dict[str, Any]): Sample project fixture.
        """
        proj_id = sample_project["project_id"]
        response = auth_client.get(f"{PROJECTS_URL}/{proj_id}")
        assert response.status_code == 200

        data = response.get_json()
        Project.Response.model_validate(data)
        assert data["project_id"] == proj_id
        assert data["uuid"] == sample_project["uuid"]

    def test_get_project_by_uuid_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when querying a non-existent project UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{PROJECTS_URL}/{uuid4()}")
        assert response.status_code == 404

    def test_get_project_by_int_id_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when querying a non-existent project integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{PROJECTS_URL}/999999999")
        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # 3. GET Associated Relational Entities (Models, Herd Units, Surveys, Schemas)
    # -------------------------------------------------------------------------

    def test_get_project_models(
        self, auth_client: FlaskClient, sample_project: dict[str, Any]
    ) -> None:
        """Verify retrieving models associated with a project by UUID and integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_project (dict[str, Any]): Sample project fixture.
        """
        # Query by UUID
        res_uuid = auth_client.get(f"{PROJECTS_URL}/{sample_project['uuid']}/models")
        assert res_uuid.status_code == 200
        models_uuid = res_uuid.get_json()
        assert isinstance(models_uuid, list)
        for item in models_uuid:
            Model.Response.model_validate(item)

        # Query by integer primary key
        res_id = auth_client.get(f"{PROJECTS_URL}/{sample_project['project_id']}/models")
        assert res_id.status_code == 200
        models_id = res_id.get_json()
        assert isinstance(models_id, list)
        assert len(models_uuid) == len(models_id)

    def test_get_project_herd_units(
        self, auth_client: FlaskClient, sample_project: dict[str, Any]
    ) -> None:
        """Verify retrieving herd units associated with a project.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_project (dict[str, Any]): Sample project fixture.
        """
        # Query by UUID
        res_uuid = auth_client.get(f"{PROJECTS_URL}/{sample_project['uuid']}/herd-units")
        assert res_uuid.status_code == 200
        units_uuid = res_uuid.get_json()
        assert isinstance(units_uuid, list)
        for item in units_uuid:
            HerdUnit.Response.model_validate(item)

        # Query by integer primary key
        res_id = auth_client.get(f"{PROJECTS_URL}/{sample_project['project_id']}/herd-units")
        assert res_id.status_code == 200
        units_id = res_id.get_json()
        assert isinstance(units_id, list)
        assert len(units_uuid) == len(units_id)

    def test_get_project_surveys(
        self, auth_client: FlaskClient, sample_project: dict[str, Any]
    ) -> None:
        """Verify retrieving surveys associated with a project.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_project (dict[str, Any]): Sample project fixture.
        """
        # Query by UUID
        res_uuid = auth_client.get(f"{PROJECTS_URL}/{sample_project['uuid']}/surveys")
        assert res_uuid.status_code == 200
        surveys_uuid = res_uuid.get_json()
        assert isinstance(surveys_uuid, list)
        for item in surveys_uuid:
            Survey.Response.model_validate(item)

        # Query by integer primary key
        res_id = auth_client.get(f"{PROJECTS_URL}/{sample_project['project_id']}/surveys")
        assert res_id.status_code == 200
        surveys_id = res_id.get_json()
        assert isinstance(surveys_id, list)
        assert len(surveys_uuid) == len(surveys_id)

    def test_get_project_schemas(
        self, auth_client: FlaskClient, sample_project: dict[str, Any]
    ) -> None:
        """Verify retrieving schemas associated with a project.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_project (dict[str, Any]): Sample project fixture.
        """
        # Query by UUID
        res_uuid = auth_client.get(f"{PROJECTS_URL}/{sample_project['uuid']}/schemas")
        assert res_uuid.status_code == 200
        schemas_uuid = res_uuid.get_json()
        assert isinstance(schemas_uuid, list)
        for item in schemas_uuid:
            Schema.Response.model_validate(item)

        # Query by integer primary key
        res_id = auth_client.get(f"{PROJECTS_URL}/{sample_project['project_id']}/schemas")
        assert res_id.status_code == 200
        schemas_id = res_id.get_json()
        assert isinstance(schemas_id, list)
        assert len(schemas_uuid) == len(schemas_id)

    def test_get_project_relations_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when querying relations for non-existent project UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        non_existent_uuid = uuid4()
        assert auth_client.get(f"{PROJECTS_URL}/{non_existent_uuid}/models").status_code == 404
        assert auth_client.get(f"{PROJECTS_URL}/{non_existent_uuid}/herd-units").status_code == 404
        assert auth_client.get(f"{PROJECTS_URL}/{non_existent_uuid}/surveys").status_code == 404
        assert auth_client.get(f"{PROJECTS_URL}/{non_existent_uuid}/schemas").status_code == 404

    # -------------------------------------------------------------------------
    # 4. POST Create Project
    # -------------------------------------------------------------------------

    def test_create_project_success(
        self, auth_client: FlaskClient, default_organization: dict[str, Any]
    ) -> None:
        """Verify successfully creating a new project with organization association.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            default_organization (dict[str, Any]): Organization keyring fixture.
        """
        new_name = f"Test_Project_{uuid4().hex[:8]}"
        payload = {
            "name": new_name,
            "organization_ids": default_organization,
        }

        response = auth_client.post(PROJECTS_URL, json=payload)
        assert response.status_code == 201

        data = response.get_json()
        Project.Response.model_validate(data)
        assert data["name"] == new_name
        assert isinstance(data["project_id"], int)
        assert isinstance(data["uuid"], str)

        # Verify new project can be retrieved by UUID and int ID
        created_uuid = data["uuid"]
        created_id = data["project_id"]

        get_uuid = auth_client.get(f"{PROJECTS_URL}/{created_uuid}")
        assert get_uuid.status_code == 200
        assert get_uuid.get_json()["name"] == new_name

        get_id = auth_client.get(f"{PROJECTS_URL}/{created_id}")
        assert get_id.status_code == 200
        assert get_id.get_json()["name"] == new_name

    def test_create_project_invalid_empty_body(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 400 validation error when posting an empty payload.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.post(PROJECTS_URL, json={})
        assert response.status_code == 400

    def test_create_project_missing_organization_ids(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 400 validation error when organization_ids is omitted.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.post(PROJECTS_URL, json={"name": "Orphan_Project"})
        assert response.status_code == 400

    # -------------------------------------------------------------------------
    # 5. DELETE Project (UUID and Integer ID)
    # -------------------------------------------------------------------------

    def test_delete_project_by_uuid(
        self, auth_client: FlaskClient, default_organization: dict[str, Any]
    ) -> None:
        """Verify deleting a project by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            default_organization (dict[str, Any]): Organization keyring fixture.
        """
        # Create a disposable project to delete
        create_res = auth_client.post(
            PROJECTS_URL,
            json={
                "name": f"Del_UUID_Proj_{uuid4().hex[:6]}",
                "organization_ids": default_organization,
            },
        )
        assert create_res.status_code == 201
        created = create_res.get_json()

        # Delete by UUID
        del_res = auth_client.delete(f"{PROJECTS_URL}/{created['uuid']}")
        assert del_res.status_code == 204

        # Confirm 404 on subsequent get
        assert auth_client.get(f"{PROJECTS_URL}/{created['uuid']}").status_code == 404

    def test_delete_project_by_int_id(
        self, auth_client: FlaskClient, default_organization: dict[str, Any]
    ) -> None:
        """Verify deleting a project by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            default_organization (dict[str, Any]): Organization keyring fixture.
        """
        # Create a disposable project to delete
        create_res = auth_client.post(
            PROJECTS_URL,
            json={
                "name": f"Del_Int_Proj_{uuid4().hex[:6]}",
                "organization_ids": default_organization,
            },
        )
        assert create_res.status_code == 201
        created = create_res.get_json()

        # Delete by integer ID
        del_res = auth_client.delete(f"{PROJECTS_URL}/{created['project_id']}")
        assert del_res.status_code == 204

        # Confirm 404 on subsequent get
        assert auth_client.get(f"{PROJECTS_URL}/{created['project_id']}").status_code == 404

    def test_delete_project_non_existent_idempotent(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify deleting a non-existent project succeeds idempotently with 204.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.delete(f"{PROJECTS_URL}/{uuid4()}")
        assert response.status_code == 204

