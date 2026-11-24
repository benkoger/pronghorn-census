"""Integration and unit tests for the Herd Units API endpoints."""

from typing import Any
from uuid import uuid4

from flask.testing import FlaskClient
from testing_core import APITester

from database.object_models.project_management.herd_units import HerdUnit
from database.object_models.project_management.surveys import Survey

HERD_UNITS_URL = "/api/v1/herd-units"
HERD_UNIT_ID = 1
HERD_UNIT_UUID = "4317a307-9595-4116-be11-c7584561dd8d"
PROJECT_KEYRING = {"pkey": 1, "uuid": "58bb015b-cc74-45a2-b986-def9173cdf86"}


def _build_herd_unit_payload(habitable_area: float | None = 125.5) -> dict[str, Any]:
    """Build a valid herd unit creation payload.

    Args:
        habitable_area (float | None): Optional habitable area in square kilometers.

    Returns:
        dict[str, Any]: Valid CreateHerdUnitReq payload dictionary.
    """
    payload: dict[str, Any] = {
        "name": f"TestHerd_{uuid4().hex[:8]}",
        "project_ids": PROJECT_KEYRING,
    }
    if habitable_area is not None:
        payload["habitable_area"] = habitable_area
    return payload


class TestHerdUnits(APITester):
    """Test suite covering the `/api/v1/herd-units` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients and
    automatic database transaction rollbacks for isolation.
    """

    # -------------------------------------------------------------------------
    # 1. GET Herd Unit by ID (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_get_herd_unit_by_uuid(self, auth_client: FlaskClient) -> None:
        """Verify retrieving a herd unit by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{HERD_UNITS_URL}/{HERD_UNIT_UUID}")
        assert response.status_code == 200

        data = response.get_json()
        validated = HerdUnit.Response.model_validate(data)
        assert validated.herd_unit_id == HERD_UNIT_ID
        assert str(validated.uuid) == HERD_UNIT_UUID

    def test_get_herd_unit_by_int_id(self, auth_client: FlaskClient) -> None:
        """Verify retrieving a herd unit by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{HERD_UNITS_URL}/{HERD_UNIT_ID}")
        assert response.status_code == 200

        data = response.get_json()
        validated = HerdUnit.Response.model_validate(data)
        assert validated.herd_unit_id == HERD_UNIT_ID
        assert str(validated.uuid) == HERD_UNIT_UUID

    def test_get_herd_unit_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 responses for non-existent herd unit UUID and integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.get(f"{HERD_UNITS_URL}/{uuid4()}").status_code == 404
        assert auth_client.get(f"{HERD_UNITS_URL}/999999999").status_code == 404

    def test_get_herd_unit_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when fetching a herd unit unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.get(f"{HERD_UNITS_URL}/{HERD_UNIT_UUID}").status_code == 401
        assert client.get(f"{HERD_UNITS_URL}/{HERD_UNIT_ID}").status_code == 401

    # -------------------------------------------------------------------------
    # 2. GET Surveys for Herd Unit
    # -------------------------------------------------------------------------

    def test_get_herd_unit_surveys_by_uuid(self, auth_client: FlaskClient) -> None:
        """Verify retrieving surveys linked to a herd unit by UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{HERD_UNITS_URL}/{HERD_UNIT_UUID}/surveys")
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            Survey.Response.model_validate(item)

    def test_get_herd_unit_surveys_by_int_id(self, auth_client: FlaskClient) -> None:
        """Verify retrieving surveys linked to a herd unit by integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{HERD_UNITS_URL}/{HERD_UNIT_ID}/surveys")
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            Survey.Response.model_validate(item)

    def test_get_herd_unit_surveys_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 response when fetching surveys for non-existent herd unit.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert (
            auth_client.get(f"{HERD_UNITS_URL}/{uuid4()}/surveys").status_code == 404
        )

    def test_get_herd_unit_surveys_unauthenticated(
        self, client: FlaskClient
    ) -> None:
        """Verify 401 response when fetching herd unit surveys unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert (
            client.get(f"{HERD_UNITS_URL}/{HERD_UNIT_UUID}/surveys").status_code == 401
        )

    # -------------------------------------------------------------------------
    # 3. POST Create Herd Unit
    # -------------------------------------------------------------------------

    def test_create_herd_unit_success(self, auth_client: FlaskClient) -> None:
        """Verify creating a herd unit and retrieving it via UUID and integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        payload = _build_herd_unit_payload(habitable_area=250.75)
        response = auth_client.post(HERD_UNITS_URL, json=payload)
        assert response.status_code == 201

        data = response.get_json()
        validated = HerdUnit.Response.model_validate(data)
        assert validated.name == payload["name"]
        assert validated.habitable_area == 250.75

        get_res = auth_client.get(f"{HERD_UNITS_URL}/{validated.uuid}")
        assert get_res.status_code == 200
        assert get_res.get_json()["name"] == payload["name"]

    def test_create_herd_unit_invalid_payload(self, auth_client: FlaskClient) -> None:
        """Verify 400 validation errors for invalid herd unit creation payloads.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.post(HERD_UNITS_URL, json={}).status_code == 400
        assert (
            auth_client.post(
                HERD_UNITS_URL, json={"name": "MissingProject"}
            ).status_code
            == 400
        )

    def test_create_herd_unit_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when creating a herd unit unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.post(HERD_UNITS_URL, json=_build_herd_unit_payload())
        assert response.status_code == 401

    # -------------------------------------------------------------------------
    # 4. DELETE Herd Unit (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_delete_herd_unit_by_uuid(self, auth_client: FlaskClient) -> None:
        """Verify deleting a herd unit by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        create_res = auth_client.post(
            HERD_UNITS_URL, json=_build_herd_unit_payload(None)
        )
        assert create_res.status_code == 201
        created = create_res.get_json()

        del_res = auth_client.delete(f"{HERD_UNITS_URL}/{created['uuid']}")
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert auth_client.get(f"{HERD_UNITS_URL}/{created['uuid']}").status_code == 404

    def test_delete_herd_unit_by_int_id(self, auth_client: FlaskClient) -> None:
        """Verify deleting a herd unit by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        create_res = auth_client.post(
            HERD_UNITS_URL, json=_build_herd_unit_payload(None)
        )
        assert create_res.status_code == 201
        created = create_res.get_json()

        del_res = auth_client.delete(f"{HERD_UNITS_URL}/{created['herd_unit_id']}")
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert (
            auth_client.get(f"{HERD_UNITS_URL}/{created['herd_unit_id']}").status_code
            == 404
        )

    def test_delete_herd_unit_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 response when deleting non-existent herd unit IDs.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.delete(f"{HERD_UNITS_URL}/{uuid4()}").status_code == 404
        assert auth_client.delete(f"{HERD_UNITS_URL}/999999999").status_code == 404

    def test_delete_herd_unit_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when deleting a herd unit unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.delete(f"{HERD_UNITS_URL}/{uuid4()}").status_code == 401
        assert client.delete(f"{HERD_UNITS_URL}/1").status_code == 401
