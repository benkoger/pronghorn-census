"""Integration and unit tests for the AM Units API endpoints."""

from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
from flask.testing import FlaskClient
from testing_core import APITester

from app.extensions import base, cache
from database.object_models.core.am_units import AmUnit

AM_UNITS_URL = "/api/v1/am-units"
AM_URL = "/api/v1/active-measurements"
SURVEY = {"pkey": 1, "uuid": "f4c0b5e0-af30-46fa-a276-6169932b6a34"}
LABEL = {"pkey": 3, "uuid": "d36185ab-1ae4-42f9-86b8-ec2f98f67693"}
MODEL = {"pkey": 2, "uuid": "f5f4caad-1fd4-46a7-982e-21d396a36d48"}
IMAGE_UUID = "26be495e-3ec2-41c8-ba14-d0b65726bb67"


class TestAmUnits(APITester):
    """Test suite covering the `/api/v1/am-units` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients and
    automatic database transaction rollbacks for isolation.
    """

    @pytest.fixture
    def active_measurement(
        self, auth_client: FlaskClient
    ) -> Generator[dict[str, Any]]:
        """Create a disposable active measurement record for AM unit tests.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.

        Yields:
            dict[str, Any]: Serialized active measurement dictionary.
        """

        def _clear(cursor, _db) -> None:
            cursor.execute(
                "DELETE FROM projectmanagement.active_measurements "
                "WHERE survey_id = %(sid)s;",
                {"sid": SURVEY["pkey"]},
            )

        base.execute(_clear)

        res = auth_client.post(
            AM_URL,
            json={
                "survey_ids": SURVEY,
                "label_ids": LABEL,
                "random_seed": 42,
                "retraining_cadence": 0,
                "target_percentage": 0.1,
            },
        )
        assert res.status_code == 201
        row = res.get_json()
        yield row
        for key in ("am_state_", "am_terms_", "am_area_", "am_threshold_"):
            cache.delete(f"{key}{row['uuid']}")

    @pytest.fixture
    def reviewed_area_keyring(self, auth_client: FlaskClient) -> dict[str, Any]:
        """Fetch an existing reviewed area keyring from the sample image.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.

        Returns:
            dict[str, Any]: ReviewedArea keyring with integer pkey and UUID.
        """
        res = auth_client.get(f"/api/v1/images/{IMAGE_UUID}/crops")
        assert res.status_code == 200
        crops = res.get_json()
        assert crops, "Sample image should contain at least one reviewed area."
        return {"pkey": crops[0]["reviewed_area_id"], "uuid": crops[0]["uuid"]}

    @staticmethod
    def _build_am_unit_payload(
        active_measurement: dict[str, Any],
        reviewed_area_keyring: dict[str, Any],
        relative_position: int = 1,
    ) -> dict[str, Any]:
        """Build a valid AmUnit creation payload.

        Args:
            active_measurement (dict[str, Any]): Parent active measurement dict.
            reviewed_area_keyring (dict[str, Any]): Linked reviewed area keyring.
            relative_position (int): Position in measurement sequence.

        Returns:
            dict[str, Any]: Valid CreateAmUnitReq payload dictionary.
        """
        return {
            "active_measurement_ids": {
                "pkey": active_measurement["active_measurement_id"],
                "uuid": active_measurement["uuid"],
            },
            "reviewed_area_ids": reviewed_area_keyring,
            "reg_model_ids": MODEL,
            "dect_model_ids": MODEL,
            "relative_position": relative_position,
            "model_count": 3.5,
            "human_count": 4,
            "current_count": 120.0,
            "current_ci_lower": 100.0,
            "current_ci_upper": 140.0,
        }

    @pytest.fixture
    def created_am_unit(
        self,
        auth_client: FlaskClient,
        active_measurement: dict[str, Any],
        reviewed_area_keyring: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a sample AM unit inside the rolled-back transaction.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            active_measurement (dict[str, Any]): Active measurement fixture.
            reviewed_area_keyring (dict[str, Any]): Reviewed area keyring fixture.

        Returns:
            dict[str, Any]: Serialized created AmUnit dictionary.
        """
        payload = self._build_am_unit_payload(
            active_measurement, reviewed_area_keyring
        )
        res = auth_client.post(AM_UNITS_URL, json=payload)
        assert res.status_code == 201
        return res.get_json()

    # -------------------------------------------------------------------------
    # 1. POST Create AM Unit
    # -------------------------------------------------------------------------

    def test_create_am_unit_success(
        self,
        auth_client: FlaskClient,
        active_measurement: dict[str, Any],
        reviewed_area_keyring: dict[str, Any],
    ) -> None:
        """Verify creating an AM unit and validating response schema.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            active_measurement (dict[str, Any]): Active measurement fixture.
            reviewed_area_keyring (dict[str, Any]): Reviewed area keyring fixture.
        """
        payload = self._build_am_unit_payload(
            active_measurement, reviewed_area_keyring, relative_position=2
        )
        response = auth_client.post(AM_UNITS_URL, json=payload)
        assert response.status_code == 201

        data = response.get_json()
        validated = AmUnit.Response.model_validate(data)
        assert (
            validated.active_measurement_id
            == active_measurement["active_measurement_id"]
        )
        assert validated.reviewed_area_id == reviewed_area_keyring["pkey"]
        assert validated.model_count == 3.5
        assert validated.human_count == 4
        assert validated.relative_position == 2

    def test_create_am_unit_invalid(self, auth_client: FlaskClient) -> None:
        """Verify 400 validation errors for invalid AM unit payloads.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.post(AM_UNITS_URL, json={}).status_code == 400
        assert (
            auth_client.post(AM_UNITS_URL, json={"human_count": 2}).status_code
            == 400
        )

    def test_create_am_unit_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when creating an AM unit unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.post(AM_UNITS_URL, json={"human_count": 2})
        assert response.status_code == 401

    # -------------------------------------------------------------------------
    # 2. GET AM Unit by ID (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_get_am_unit_by_uuid(
        self, auth_client: FlaskClient, created_am_unit: dict[str, Any]
    ) -> None:
        """Verify retrieving an AM unit by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_am_unit (dict[str, Any]): Created AM unit fixture.
        """
        response = auth_client.get(f"{AM_UNITS_URL}/{created_am_unit['uuid']}")
        assert response.status_code == 200

        data = response.get_json()
        validated = AmUnit.Response.model_validate(data)
        assert str(validated.uuid) == created_am_unit["uuid"]
        assert validated.am_unit_id == created_am_unit["am_unit_id"]

    def test_get_am_unit_by_int_id(
        self, auth_client: FlaskClient, created_am_unit: dict[str, Any]
    ) -> None:
        """Verify retrieving an AM unit by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_am_unit (dict[str, Any]): Created AM unit fixture.
        """
        response = auth_client.get(
            f"{AM_UNITS_URL}/{created_am_unit['am_unit_id']}"
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = AmUnit.Response.model_validate(data)
        assert validated.am_unit_id == created_am_unit["am_unit_id"]
        assert str(validated.uuid) == created_am_unit["uuid"]

    def test_get_am_unit_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 responses for non-existent AM unit UUID and integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.get(f"{AM_UNITS_URL}/{uuid4()}").status_code == 404
        assert auth_client.get(f"{AM_UNITS_URL}/999999999").status_code == 404

    def test_get_am_unit_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when fetching an AM unit unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.get(f"{AM_UNITS_URL}/{uuid4()}").status_code == 401
        assert client.get(f"{AM_UNITS_URL}/1").status_code == 401

    # -------------------------------------------------------------------------
    # 3. PATCH Update AM Unit (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_update_am_unit_by_uuid(
        self, auth_client: FlaskClient, created_am_unit: dict[str, Any]
    ) -> None:
        """Verify updating AM unit metrics by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_am_unit (dict[str, Any]): Created AM unit fixture.
        """
        response = auth_client.patch(
            f"{AM_UNITS_URL}/{created_am_unit['uuid']}",
            json={
                "human_count": 9,
                "current_count": 155.0,
                "current_ci_lower": 130.0,
                "current_ci_upper": 180.0,
            },
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = AmUnit.Response.model_validate(data)
        assert validated.human_count == 9
        assert validated.current_count == 155.0

    def test_update_am_unit_by_int_id(
        self, auth_client: FlaskClient, created_am_unit: dict[str, Any]
    ) -> None:
        """Verify updating AM unit metrics by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_am_unit (dict[str, Any]): Created AM unit fixture.
        """
        response = auth_client.patch(
            f"{AM_UNITS_URL}/{created_am_unit['am_unit_id']}",
            json={"human_count": 6, "relative_position": 3},
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = AmUnit.Response.model_validate(data)
        assert validated.human_count == 6
        assert validated.relative_position == 3

    def test_update_am_unit_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 response when updating a non-existent AM unit.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert (
            auth_client.patch(
                f"{AM_UNITS_URL}/{uuid4()}", json={"human_count": 1}
            ).status_code
            == 404
        )

    def test_update_am_unit_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when updating an AM unit unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert (
            client.patch(
                f"{AM_UNITS_URL}/{uuid4()}", json={"human_count": 1}
            ).status_code
            == 401
        )

    # -------------------------------------------------------------------------
    # 4. DELETE AM Unit (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_delete_am_unit_by_uuid(
        self, auth_client: FlaskClient, created_am_unit: dict[str, Any]
    ) -> None:
        """Verify deleting an AM unit by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_am_unit (dict[str, Any]): Created AM unit fixture.
        """
        del_res = auth_client.delete(
            f"{AM_UNITS_URL}/{created_am_unit['uuid']}"
        )
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert (
            auth_client.get(f"{AM_UNITS_URL}/{created_am_unit['uuid']}").status_code
            == 404
        )

    def test_delete_am_unit_by_int_id(
        self, auth_client: FlaskClient, created_am_unit: dict[str, Any]
    ) -> None:
        """Verify deleting an AM unit by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_am_unit (dict[str, Any]): Created AM unit fixture.
        """
        del_res = auth_client.delete(
            f"{AM_UNITS_URL}/{created_am_unit['am_unit_id']}"
        )
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert (
            auth_client.get(
                f"{AM_UNITS_URL}/{created_am_unit['am_unit_id']}"
            ).status_code
            == 404
        )

    def test_delete_am_unit_non_existent_idempotent(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify deleting non-existent AM unit IDs succeeds idempotently with 204.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.delete(f"{AM_UNITS_URL}/{uuid4()}").status_code == 204
        assert auth_client.delete(f"{AM_UNITS_URL}/999999999").status_code == 204

    def test_delete_am_unit_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when deleting an AM unit unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.delete(f"{AM_UNITS_URL}/{uuid4()}").status_code == 401
        assert client.delete(f"{AM_UNITS_URL}/1").status_code == 401
