"""Integration and unit tests for the Reviewed Areas API endpoints."""

from typing import Any
from uuid import uuid4

import pytest
from flask.testing import FlaskClient
from testing_core import APITester

from database.object_models.core.annotations import Annotation
from database.object_models.core.images import ReviewedArea

IMAGE_ID = 1047
IMAGE_UUID = "26be495e-3ec2-41c8-ba14-d0b65726bb67"
SURVEY_UUID = "f4c0b5e0-af30-46fa-a276-6169932b6a34"
HERD_UNIT_UUID = "4317a307-9595-4116-be11-c7584561dd8d"
RA_URL = "/api/v1/reviewed-area"


class TestReviewedAreas(APITester):
    """Test suite covering the `/api/v1/reviewed-area` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients,
    mocked S3 storage, and automatic database transaction rollbacks for isolation.
    """

    @pytest.fixture
    def sample_crop(self, auth_client: FlaskClient) -> dict[str, Any]:
        """Fetch an existing reviewed area crop associated with the sample image.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.

        Returns:
            dict[str, Any]: Serialized reviewed area crop dictionary.
        """
        res = auth_client.get(f"/api/v1/images/{IMAGE_UUID}/crops")
        assert res.status_code == 200
        crops = res.get_json()
        assert crops, "Sample image should contain at least one reviewed area crop."
        return crops[0]

    # -------------------------------------------------------------------------
    # 1. GET List & Query Filtering
    # -------------------------------------------------------------------------

    def test_get_reviewed_areas_default(self, auth_client: FlaskClient) -> None:
        """Verify fetching reviewed areas with default query parameters.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(RA_URL)
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        for item in data:
            ReviewedArea.Response.model_validate(item)

    def test_get_reviewed_areas_by_survey_id(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify filtering reviewed areas by survey UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            RA_URL, query_string={"survey_id": SURVEY_UUID, "include_reviewed": True}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        for item in data:
            ReviewedArea.Response.model_validate(item)

    def test_get_reviewed_areas_by_herd_unit_id(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify filtering reviewed areas by herd unit UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            RA_URL,
            query_string={"herd_unit_id": HERD_UNIT_UUID, "include_reviewed": True},
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        for item in data:
            ReviewedArea.Response.model_validate(item)

    def test_get_reviewed_areas_paginated(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify paginated reviewed area listing response format.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            RA_URL,
            query_string={"page": 1, "per_page": 5, "include_reviewed": True},
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, dict)
        assert "crops" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["per_page"] == 5
        assert isinstance(data["crops"], list)
        for item in data["crops"]:
            ReviewedArea.Response.model_validate(item)

    def test_get_reviewed_areas_search(
        self, auth_client: FlaskClient, sample_crop: dict[str, Any]
    ) -> None:
        """Verify name search filtering on reviewed areas.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_crop (dict[str, Any]): Sample crop fixture.
        """
        search_term = sample_crop["name"][:4]
        response = auth_client.get(
            RA_URL,
            query_string={"search": search_term, "include_reviewed": True},
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        for item in data:
            ReviewedArea.Response.model_validate(item)

    def test_get_reviewed_areas_filter_type(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify filtering reviewed areas by activity type.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            RA_URL,
            query_string={"type": "auto cropper", "include_reviewed": True},
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        for item in data:
            validated = ReviewedArea.Response.model_validate(item)
            assert validated.type.value == "auto cropper"

    # -------------------------------------------------------------------------
    # 2. GET Single by ID (UUID and Integer ID)
    # -------------------------------------------------------------------------

    def test_get_reviewed_area_by_uuid(
        self, auth_client: FlaskClient, sample_crop: dict[str, Any]
    ) -> None:
        """Verify retrieving a reviewed area by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_crop (dict[str, Any]): Sample crop fixture.
        """
        response = auth_client.get(f"{RA_URL}/{sample_crop['uuid']}")
        assert response.status_code == 200

        data = response.get_json()
        validated = ReviewedArea.Response.model_validate(data)
        assert str(validated.uuid) == sample_crop["uuid"]
        assert validated.reviewed_area_id == sample_crop["reviewed_area_id"]

    def test_get_reviewed_area_by_int_id(
        self, auth_client: FlaskClient, sample_crop: dict[str, Any]
    ) -> None:
        """Verify retrieving a reviewed area by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_crop (dict[str, Any]): Sample crop fixture.
        """
        response = auth_client.get(f"{RA_URL}/{sample_crop['reviewed_area_id']}")
        assert response.status_code == 200

        data = response.get_json()
        validated = ReviewedArea.Response.model_validate(data)
        assert validated.reviewed_area_id == sample_crop["reviewed_area_id"]
        assert str(validated.uuid) == sample_crop["uuid"]

    def test_get_reviewed_area_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when querying a non-existent reviewed area UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{RA_URL}/{uuid4()}")
        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # 3. GET Annotations for Reviewed Area
    # -------------------------------------------------------------------------

    def test_get_reviewed_area_annotations_by_uuid(
        self, auth_client: FlaskClient, sample_crop: dict[str, Any]
    ) -> None:
        """Verify retrieving annotations for a reviewed area by UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_crop (dict[str, Any]): Sample crop fixture.
        """
        response = auth_client.get(f"{RA_URL}/{sample_crop['uuid']}/annotations")
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        for item in data:
            Annotation.Response.model_validate(item)

    def test_get_reviewed_area_annotations_by_int_id(
        self, auth_client: FlaskClient, sample_crop: dict[str, Any]
    ) -> None:
        """Verify retrieving annotations for a reviewed area by integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_crop (dict[str, Any]): Sample crop fixture.
        """
        response = auth_client.get(
            f"{RA_URL}/{sample_crop['reviewed_area_id']}/annotations"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        for item in data:
            Annotation.Response.model_validate(item)

    # -------------------------------------------------------------------------
    # 4. POST Presigned GET URL
    # -------------------------------------------------------------------------

    def test_create_ra_presigned_get_success(
        self, auth_client: FlaskClient, sample_crop: dict[str, Any]
    ) -> None:
        """Verify generating a presigned GET URL for an existing reviewed area.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_crop (dict[str, Any]): Sample crop fixture.
        """
        payload = {"reviewed_area_id": sample_crop["uuid"]}
        response = auth_client.post(f"{RA_URL}/presigned-get-url", json=payload)
        assert response.status_code == 201

        url = response.get_json()
        assert isinstance(url, str)
        assert url.startswith("http")

    def test_create_ra_presigned_get_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when requesting presigned URL for unknown area.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        payload = {"reviewed_area_id": str(uuid4())}
        response = auth_client.post(f"{RA_URL}/presigned-get-url", json=payload)
        assert response.status_code == 404

    def test_create_ra_presigned_get_invalid(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 400 response when requesting presigned URL with invalid body.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.post(f"{RA_URL}/presigned-get-url", json={})
        assert response.status_code == 400

    # -------------------------------------------------------------------------
    # 5. PATCH Update Reviewed Area (UUID and Integer ID)
    # -------------------------------------------------------------------------

    def test_update_reviewed_area_by_uuid(
        self, auth_client: FlaskClient, sample_crop: dict[str, Any]
    ) -> None:
        """Verify updating a reviewed area by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_crop (dict[str, Any]): Sample crop fixture.
        """
        new_name = f"updated_ra_{uuid4().hex[:6]}"
        response = auth_client.patch(
            f"{RA_URL}/{sample_crop['uuid']}", json={"name": new_name}
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = ReviewedArea.Response.model_validate(data)
        assert validated.name == new_name

    def test_update_reviewed_area_by_int_id(
        self, auth_client: FlaskClient, sample_crop: dict[str, Any]
    ) -> None:
        """Verify updating a reviewed area by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_crop (dict[str, Any]): Sample crop fixture.
        """
        new_name = f"updated_ra_int_{uuid4().hex[:6]}"
        response = auth_client.patch(
            f"{RA_URL}/{sample_crop['reviewed_area_id']}", json={"name": new_name}
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = ReviewedArea.Response.model_validate(data)
        assert validated.name == new_name

    def test_update_reviewed_area_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when updating a non-existent reviewed area UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.patch(
            f"{RA_URL}/{uuid4()}", json={"name": "phantom_crop"}
        )
        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # 6. PATCH Set-Reviewed Workflow (UUID and Integer ID)
    # -------------------------------------------------------------------------

    def test_set_reviewed_by_uuid(
        self, auth_client: FlaskClient, sample_crop: dict[str, Any]
    ) -> None:
        """Verify marking a reviewed area as reviewed via its UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_crop (dict[str, Any]): Sample crop fixture.
        """
        response = auth_client.patch(f"{RA_URL}/{sample_crop['uuid']}/set-reviewed")
        assert response.status_code == 200

        data = response.get_json()
        ReviewedArea.Response.model_validate(data)

    def test_set_reviewed_by_int_id(
        self, auth_client: FlaskClient, sample_crop: dict[str, Any]
    ) -> None:
        """Verify marking a reviewed area as reviewed via its integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_crop (dict[str, Any]): Sample crop fixture.
        """
        response = auth_client.patch(
            f"{RA_URL}/{sample_crop['reviewed_area_id']}/set-reviewed"
        )
        assert response.status_code == 200

        data = response.get_json()
        ReviewedArea.Response.model_validate(data)

    def test_set_reviewed_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when setting reviewed on a non-existent area.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.patch(f"{RA_URL}/{uuid4()}/set-reviewed")
        assert response.status_code == 404
