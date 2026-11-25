"""Integration and unit tests for the Crop Verifier API endpoints."""

from typing import Any
from uuid import uuid4

import pytest
from flask.testing import FlaskClient
from testing_core import APITester

from app.extensions import base
from database.object_models.core.images import Image, ReviewedArea

VERIFIER_URL = "/api/v1/verifier"
AREA_URL = f"{VERIFIER_URL}/area-needing-reviewed"
COUNT_URL = f"{VERIFIER_URL}/needing-reviewed"
SURVEY_UUID = "f4c0b5e0-af30-46fa-a276-6169932b6a34"
HERD_UNIT_KEYRING = {"pkey": 1, "uuid": "4317a307-9595-4116-be11-c7584561dd8d"}
PROJECT_KEYRING = {"pkey": 1, "uuid": "58bb015b-cc74-45a2-b986-def9173cdf86"}


class TestCropVerifier(APITester):
    """Test suite covering the `/api/v1/verifier` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients and
    automatic database transaction rollbacks for isolation.
    """

    @pytest.fixture
    def empty_survey_uuid(self, auth_client: FlaskClient) -> str:
        """Create a disposable survey with no images or reviewed areas.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.

        Returns:
            str: Public UUID of the empty survey.
        """
        res = auth_client.post(
            "/api/v1/surveys",
            json={
                "name": f"EmptyVerifierSurvey_{uuid4().hex[:8]}",
                "survey_date": "2025-07-01T00:00:00Z",
                "herd_unit_ids": HERD_UNIT_KEYRING,
                "project_ids": PROJECT_KEYRING,
            },
        )
        assert res.status_code == 201
        return res.get_json()["uuid"]

    # -------------------------------------------------------------------------
    # 1. GET Area Needing Reviewed
    # -------------------------------------------------------------------------

    def test_get_area_needing_reviewed_success(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify fetching crops locks an available image and returns ReviewedAreas.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            AREA_URL, query_string={"survey_id": SURVEY_UUID}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1

        locked_image_ids: set[int] = set()
        for item in data:
            validated = ReviewedArea.Response.model_validate(item)
            locked_image_ids.add(validated.image_id)

        assert len(locked_image_ids) == 1
        locked_image_id = next(iter(locked_image_ids))

        locked_image = base.get(Image, locked_image_id)
        assert locked_image.opened_by_user_id != 0

    def test_get_area_needing_reviewed_include_reviewed(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify fetching crops with include_reviewed=true returns 200.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            AREA_URL,
            query_string={"survey_id": SURVEY_UUID, "include_reviewed": True},
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for item in data:
            ReviewedArea.Response.model_validate(item)

    def test_get_area_needing_reviewed_empty_returns_204(
        self, auth_client: FlaskClient, empty_survey_uuid: str
    ) -> None:
        """Verify 204 No Content when no reviewed areas exist for a survey.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            empty_survey_uuid (str): Empty survey UUID fixture.
        """
        response = auth_client.get(
            AREA_URL, query_string={"survey_id": empty_survey_uuid}
        )
        assert response.status_code == 204
        assert response.data == b""

    def test_get_area_needing_reviewed_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when querying a non-existent survey UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            AREA_URL, query_string={"survey_id": str(uuid4())}
        )
        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # 2. GET Selection Count (/needing-reviewed)
    # -------------------------------------------------------------------------

    def test_get_selection_count_success(self, auth_client: FlaskClient) -> None:
        """Verify retrieving count of crops needing review in a survey.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            COUNT_URL, query_string={"survey_id": SURVEY_UUID}
        )
        assert response.status_code == 200

        data: dict[str, Any] = response.get_json()
        assert isinstance(data, dict)
        assert isinstance(data["count"], int)
        assert data["count"] >= 1

    def test_get_selection_count_include_opened_and_reviewed(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify count changes when locking an image and toggling include_opened.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        before = auth_client.get(
            COUNT_URL,
            query_string={"survey_id": SURVEY_UUID, "include_opened": False},
        ).get_json()["count"]

        lock_res = auth_client.get(
            AREA_URL, query_string={"survey_id": SURVEY_UUID}
        )
        assert lock_res.status_code == 200
        locked_count = len(lock_res.get_json())

        after_excluded = auth_client.get(
            COUNT_URL,
            query_string={"survey_id": SURVEY_UUID, "include_opened": False},
        ).get_json()["count"]
        after_included = auth_client.get(
            COUNT_URL,
            query_string={"survey_id": SURVEY_UUID, "include_opened": True},
        ).get_json()["count"]

        assert after_excluded == before - locked_count
        assert after_included >= before

        unreviewed_before = auth_client.get(
            COUNT_URL,
            query_string={
                "survey_id": SURVEY_UUID,
                "include_reviewed": False,
                "include_opened": True,
            },
        ).get_json()["count"]

        # Ensure include_reviewed flag works when another crop is marked reviewed.
        def _mark_one_reviewed(cursor, _db) -> None:
            cursor.execute(
                "UPDATE core.reviewed_area SET reviewed_by_user_id = 1 "
                "WHERE reviewed_area_id = %(raid)s;",
                {"raid": lock_res.get_json()[0]["reviewed_area_id"]},
            )

        base.execute(_mark_one_reviewed)

        unreviewed_after = auth_client.get(
            COUNT_URL,
            query_string={
                "survey_id": SURVEY_UUID,
                "include_reviewed": False,
                "include_opened": True,
            },
        ).get_json()["count"]
        all_total = auth_client.get(
            COUNT_URL,
            query_string={
                "survey_id": SURVEY_UUID,
                "include_reviewed": True,
                "include_opened": True,
            },
        ).get_json()["count"]
        assert unreviewed_after == unreviewed_before - 1
        assert all_total >= unreviewed_after

    def test_get_selection_count_empty_survey(
        self, auth_client: FlaskClient, empty_survey_uuid: str
    ) -> None:
        """Verify zero count for a survey with no reviewed areas.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            empty_survey_uuid (str): Empty survey UUID fixture.
        """
        response = auth_client.get(
            COUNT_URL, query_string={"survey_id": empty_survey_uuid}
        )
        assert response.status_code == 200
        assert response.get_json() == {"count": 0}

    def test_get_selection_count_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when querying count for a non-existent survey.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            COUNT_URL, query_string={"survey_id": str(uuid4())}
        )
        assert response.status_code == 404

