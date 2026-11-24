"""Integration and unit tests for the Roles API endpoints."""

from uuid import uuid4

from flask.testing import FlaskClient
from testing_core import APITester

from database.object_models.user_management.roles import Role

ROLES_URL = "/api/v1/roles"
ADMIN_ROLE_ID = 1
ADMIN_ROLE_UUID = "c147d407-0254-4b2d-ad74-c780e31cdfb7"
ANNOTATOR_ROLE_ID = 2
ANNOTATOR_ROLE_UUID = "a443310d-f431-4f60-b6af-1454c39f94a2"


class TestRoles(APITester):
    """Test suite covering the `/api/v1/roles` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients and
    automatic database transaction rollbacks for isolation.
    """

    # -------------------------------------------------------------------------
    # 1. GET Bulk Roles by Query IDs
    # -------------------------------------------------------------------------

    def test_get_roles_bulk_by_int_ids(self, auth_client: FlaskClient) -> None:
        """Verify bulk retrieving roles using integer primary key query parameters.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            ROLES_URL, query_string={"object_ids": [ADMIN_ROLE_ID, ANNOTATOR_ROLE_ID]}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 2
        for item in data:
            Role.Response.model_validate(item)

        names = {item["name"] for item in data}
        assert names == {"admin", "annotator"}

    def test_get_roles_bulk_by_uuids(self, auth_client: FlaskClient) -> None:
        """Verify bulk retrieving roles using UUID query parameters.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            ROLES_URL,
            query_string={"object_ids": [ADMIN_ROLE_UUID, ANNOTATOR_ROLE_UUID]},
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 2
        for item in data:
            Role.Response.model_validate(item)

    def test_get_roles_bulk_single_id(self, auth_client: FlaskClient) -> None:
        """Verify bulk endpoint handles a single scalar object_ids query parameter.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            ROLES_URL, query_string={"object_ids": ADMIN_ROLE_UUID}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        Role.Response.model_validate(data[0])
        assert data[0]["uuid"] == ADMIN_ROLE_UUID

    def test_get_roles_bulk_missing_query(self, auth_client: FlaskClient) -> None:
        """Verify 400 validation error when object_ids query parameter is omitted.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(ROLES_URL)
        assert response.status_code == 400

    def test_get_roles_bulk_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when bulk querying roles unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.get(
            ROLES_URL, query_string={"object_ids": [ADMIN_ROLE_ID]}
        )
        assert response.status_code == 401

    # -------------------------------------------------------------------------
    # 2. GET Single Role by ID (UUID and Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_get_role_by_uuid(self, auth_client: FlaskClient) -> None:
        """Verify retrieving a single role by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{ROLES_URL}/{ADMIN_ROLE_UUID}")
        assert response.status_code == 200

        data = response.get_json()
        validated = Role.Response.model_validate(data)
        assert validated.role_id == ADMIN_ROLE_ID
        assert str(validated.uuid) == ADMIN_ROLE_UUID
        assert validated.name == "admin"

    def test_get_role_by_int_id(self, auth_client: FlaskClient) -> None:
        """Verify retrieving a single role by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{ROLES_URL}/{ANNOTATOR_ROLE_ID}")
        assert response.status_code == 200

        data = response.get_json()
        validated = Role.Response.model_validate(data)
        assert validated.role_id == ANNOTATOR_ROLE_ID
        assert str(validated.uuid) == ANNOTATOR_ROLE_UUID
        assert validated.name == "annotator"

    def test_get_role_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 responses for non-existent role UUID and integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.get(f"{ROLES_URL}/{uuid4()}").status_code == 404
        assert auth_client.get(f"{ROLES_URL}/999999999").status_code == 404

    def test_get_role_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when fetching a role without authentication.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.get(f"{ROLES_URL}/{ADMIN_ROLE_UUID}").status_code == 401
        assert client.get(f"{ROLES_URL}/{ADMIN_ROLE_ID}").status_code == 401
