"""Integration and unit tests for the Schemas API endpoints."""

from typing import Any
from uuid import uuid4

from flask.testing import FlaskClient
from testing_core import APITester

from app.extensions import base
from database.object_models.project_management.labels import Label
from database.object_models.project_management.models import Model
from database.object_models.project_management.schemas import Schema

SCHEMAS_URL = "/api/v1/schemas"
SCHEMA_ID = 1
SCHEMA_UUID = "1b9930d5-386d-4132-9afb-e5dbdf43ea23"
PROJECT_KEYRING = {"pkey": 1, "uuid": "58bb015b-cc74-45a2-b986-def9173cdf86"}
MODEL_KEYRING = {"pkey": 2, "uuid": "f5f4caad-1fd4-46a7-982e-21d396a36d48"}


def _build_schema_payload() -> dict[str, Any]:
    """Build a valid schema creation payload.

    Returns:
        dict[str, Any]: Valid createSchemaReq payload dictionary.
    """
    return {
        "name": f"TestSchema_{uuid4().hex[:8]}",
        "project_ids": PROJECT_KEYRING,
        "model_ids": MODEL_KEYRING,
    }


def _unlink_schema_from_projects(schema_id: int) -> None:
    """Remove projects_schemas link rows before deleting a schema.

    The projects_schemas FK on schema_id uses ON DELETE SET NULL against a
    NOT NULL primary key column, so link rows must be cleared before deletion.

    Args:
        schema_id (int): Integer primary key of the schema to unlink.
    """

    def _run(cursor, _db) -> None:
        cursor.execute(
            "DELETE FROM projectmanagement.projects_schemas WHERE schema_id = %(sid)s;",
            {"sid": schema_id},
        )

    base.execute(_run)


class TestSchemas(APITester):
    """Test suite covering the `/api/v1/schemas` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients and
    automatic database transaction rollbacks for isolation.
    """

    # -------------------------------------------------------------------------
    # 1. GET Schema Labels
    # -------------------------------------------------------------------------

    def test_get_schema_labels_by_uuid(self, auth_client: FlaskClient) -> None:
        """Verify retrieving labels belonging to a schema by UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{SCHEMAS_URL}/{SCHEMA_UUID}/labels")
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            Label.Response.model_validate(item)

    def test_get_schema_labels_by_int_id(self, auth_client: FlaskClient) -> None:
        """Verify retrieving labels belonging to a schema by integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{SCHEMAS_URL}/{SCHEMA_ID}/labels")
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            Label.Response.model_validate(item)

    def test_get_schema_labels_not_found(self, auth_client: FlaskClient) -> None:
        """Verify empty list responses for labels under non-existent schemas.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        res_uuid = auth_client.get(f"{SCHEMAS_URL}/{uuid4()}/labels")
        assert res_uuid.status_code == 200
        assert res_uuid.get_json() == []

        res_int = auth_client.get(f"{SCHEMAS_URL}/999999999/labels")
        assert res_int.status_code == 200
        assert res_int.get_json() == []

    # -------------------------------------------------------------------------
    # 2. GET Schema Models
    # -------------------------------------------------------------------------

    def test_get_schema_models_by_uuid(self, auth_client: FlaskClient) -> None:
        """Verify retrieving models belonging to a schema by UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{SCHEMAS_URL}/{SCHEMA_UUID}/models")
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            Model.Response.model_validate(item)

    def test_get_schema_models_by_int_id(self, auth_client: FlaskClient) -> None:
        """Verify retrieving models belonging to a schema by integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{SCHEMAS_URL}/{SCHEMA_ID}/models")
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            Model.Response.model_validate(item)

    def test_get_schema_models_not_found(self, auth_client: FlaskClient) -> None:
        """Verify empty list responses for models under non-existent schemas.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        res_uuid = auth_client.get(f"{SCHEMAS_URL}/{uuid4()}/models")
        assert res_uuid.status_code == 200
        assert res_uuid.get_json() == []

        res_int = auth_client.get(f"{SCHEMAS_URL}/999999999/models")
        assert res_int.status_code == 200
        assert res_int.get_json() == []

    # -------------------------------------------------------------------------
    # 3. POST Create Schema
    # -------------------------------------------------------------------------

    def test_create_schema_success(self, auth_client: FlaskClient) -> None:
        """Verify creating a new schema record.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        payload = _build_schema_payload()
        response = auth_client.post(SCHEMAS_URL, json=payload)
        assert response.status_code == 201

        data = response.get_json()
        validated = Schema.Response.model_validate(data)
        assert validated.name == payload["name"]

    def test_create_schema_invalid_payload(self, auth_client: FlaskClient) -> None:
        """Verify 400 validation errors when posting invalid schema payloads.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.post(SCHEMAS_URL, json={}).status_code == 400
        assert (
            auth_client.post(SCHEMAS_URL, json={"name": "MissingKeys"}).status_code
            == 400
        )

    # -------------------------------------------------------------------------
    # 4. DELETE Schema (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_delete_schema_by_uuid(self, auth_client: FlaskClient) -> None:
        """Verify deleting a schema by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        create_res = auth_client.post(SCHEMAS_URL, json=_build_schema_payload())
        assert create_res.status_code == 201
        created = create_res.get_json()
        _unlink_schema_from_projects(created["schema_id"])

        del_res = auth_client.delete(f"{SCHEMAS_URL}/{created['uuid']}")
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert (
            auth_client.get(f"{SCHEMAS_URL}/{created['uuid']}/labels").get_json() == []
        )

    def test_delete_schema_by_int_id(self, auth_client: FlaskClient) -> None:
        """Verify deleting a schema by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        create_res = auth_client.post(SCHEMAS_URL, json=_build_schema_payload())
        assert create_res.status_code == 201
        created = create_res.get_json()
        _unlink_schema_from_projects(created["schema_id"])

        del_res = auth_client.delete(f"{SCHEMAS_URL}/{created['schema_id']}")
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert (
            auth_client.get(
                f"{SCHEMAS_URL}/{created['schema_id']}/labels"
            ).get_json()
            == []
        )

