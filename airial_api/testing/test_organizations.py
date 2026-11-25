"""Integration and unit tests for the Organizations API endpoints."""

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from flask.testing import FlaskClient
from testing_core import APITester

from database.object_models.user_management.organizations import Organization

ORGS_URL = "/api/v1/organizations"


class TestOrganizations(APITester):
    """Test suite covering the `/api/v1/organizations` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients and
    automatic database transaction rollbacks for isolation.
    """

    # -------------------------------------------------------------------------
    # 1. POST Create Organization
    # -------------------------------------------------------------------------

    def test_create_organization_success_with_mocked_insert(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify POST /organizations serializes created Organization and returns 201.

        Organization._create is currently an unimplemented stub in the model layer,
        so this test patches Organization._create to verify router validation,
        response serialization, and status code handling.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        now = datetime.now(UTC)
        org_uuid = uuid4()
        stub_org = Organization(
            organization_id=99,
            name="Mocked_Test_Org",
            logo_url="https://example.com/logo.png",
            created=now,
            modified=now,
            uuid=org_uuid,
        )

        with patch.object(
            Organization, "_create", return_value=(stub_org, [])
        ) as mock_create:
            response = auth_client.post(
                ORGS_URL,
                json={
                    "name": "Mocked_Test_Org",
                    "logo_url": "https://example.com/logo.png",
                },
            )

        assert response.status_code == 201
        mock_create.assert_called_once()
        data = response.get_json()
        validated = Organization.Response.model_validate(data)
        assert validated.organization_id == 99
        assert validated.name == "Mocked_Test_Org"
        assert str(validated.uuid) == str(org_uuid)

    def test_create_organization_unimplemented_returns_400(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify POST /organizations returns 400 FailedToCreate while _create is a stub.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.post(
            ORGS_URL, json={"name": f"Org_{uuid4().hex[:8]}"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["message"] == "Failed to create Organization"

    def test_create_organization_invalid_payload(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 400 validation errors when posting invalid organization payloads.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.post(ORGS_URL, json={}).status_code == 400
        assert (
            auth_client.post(
                ORGS_URL, json={"logo_url": "https://example.com/logo.png"}
            ).status_code
            == 400
        )

