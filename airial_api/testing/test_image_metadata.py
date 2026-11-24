"""Integration and unit tests for the Image Metadata API endpoints."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from flask.testing import FlaskClient
from testing_core import APITester

from database.object_models.core.image_metadata import ImageMetadata

METADATA_URL = "/api/v1/image-metadata"
IMAGE_KEYRING = {"pkey": 1047, "uuid": "26be495e-3ec2-41c8-ba14-d0b65726bb67"}


def _build_metadata_payload(transect_id: int = 12) -> dict[str, Any]:
    """Build a valid image metadata creation payload.

    Args:
        transect_id (int): Flight transect identifier. Defaults to 12.

    Returns:
        dict[str, Any]: Valid CreateImageMetadataReq payload dictionary.
    """
    return {
        "image_ids": IMAGE_KEYRING,
        "captured_at": datetime(2025, 6, 15, 14, 30, 0, tzinfo=UTC).isoformat(),
        "gps_lon": -105.5911,
        "gps_lat": 41.3114,
        "gps_alt_msl_m": 2500.5,
        "yaw_deg": 180.0,
        "pitch_deg": -90.0,
        "fov_deg": 45.2,
        "terrain_elev_m": 2190.0,
        "agl_m": 310.5,
        "transect_id": transect_id,
    }


class TestImageMetadata(APITester):
    """Test suite covering the `/api/v1/image-metadata` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients and
    automatic database transaction rollbacks for isolation.
    """

    @pytest.fixture
    def created_metadata(self, auth_client: FlaskClient) -> dict[str, Any]:
        """Create a sample image metadata record inside the rolled-back transaction.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.

        Returns:
            dict[str, Any]: Serialized created ImageMetadata dictionary.
        """
        res = auth_client.post(METADATA_URL, json=_build_metadata_payload())
        assert res.status_code == 201
        return res.get_json()

    # -------------------------------------------------------------------------
    # 1. POST Create Image Metadata
    # -------------------------------------------------------------------------

    def test_create_image_metadata_success(self, auth_client: FlaskClient) -> None:
        """Verify creating an image metadata record and validating response schema.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        payload = _build_metadata_payload(transect_id=7)
        response = auth_client.post(METADATA_URL, json=payload)
        assert response.status_code == 201

        data = response.get_json()
        validated = ImageMetadata.Response.model_validate(data)
        assert validated.image_id == IMAGE_KEYRING["pkey"]
        assert validated.gps_lon == -105.5911
        assert validated.gps_lat == 41.3114
        assert validated.transect_id == 7

    def test_create_image_metadata_invalid(self, auth_client: FlaskClient) -> None:
        """Verify 400 validation errors for invalid metadata payloads.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.post(METADATA_URL, json={}).status_code == 400
        assert (
            auth_client.post(
                METADATA_URL, json={"image_ids": IMAGE_KEYRING}
            ).status_code
            == 400
        )

    def test_create_image_metadata_unauthenticated(
        self, client: FlaskClient
    ) -> None:
        """Verify 401 response when creating image metadata unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.post(METADATA_URL, json=_build_metadata_payload())
        assert response.status_code == 401

    # -------------------------------------------------------------------------
    # 2. GET Image Metadata by ID (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_get_image_metadata_by_uuid(
        self, auth_client: FlaskClient, created_metadata: dict[str, Any]
    ) -> None:
        """Verify retrieving image metadata by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_metadata (dict[str, Any]): Created metadata fixture.
        """
        response = auth_client.get(f"{METADATA_URL}/{created_metadata['uuid']}")
        assert response.status_code == 200

        data = response.get_json()
        validated = ImageMetadata.Response.model_validate(data)
        assert str(validated.uuid) == created_metadata["uuid"]
        assert validated.metadata_id == created_metadata["metadata_id"]

    def test_get_image_metadata_by_int_id(
        self, auth_client: FlaskClient, created_metadata: dict[str, Any]
    ) -> None:
        """Verify retrieving image metadata by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_metadata (dict[str, Any]): Created metadata fixture.
        """
        response = auth_client.get(
            f"{METADATA_URL}/{created_metadata['metadata_id']}"
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = ImageMetadata.Response.model_validate(data)
        assert validated.metadata_id == created_metadata["metadata_id"]
        assert str(validated.uuid) == created_metadata["uuid"]

    def test_get_image_metadata_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 responses for non-existent metadata UUID and integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.get(f"{METADATA_URL}/{uuid4()}").status_code == 404
        assert auth_client.get(f"{METADATA_URL}/999999999").status_code == 404

    def test_get_image_metadata_unauthenticated(
        self, client: FlaskClient
    ) -> None:
        """Verify 401 response when fetching image metadata unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.get(f"{METADATA_URL}/{uuid4()}").status_code == 401
        assert client.get(f"{METADATA_URL}/1").status_code == 401

    # -------------------------------------------------------------------------
    # 3. PATCH Update Image Metadata (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_update_image_metadata_by_uuid(
        self, auth_client: FlaskClient, created_metadata: dict[str, Any]
    ) -> None:
        """Verify updating image metadata fields by UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_metadata (dict[str, Any]): Created metadata fixture.
        """
        response = auth_client.patch(
            f"{METADATA_URL}/{created_metadata['uuid']}",
            json={"agl_m": 425.0, "transect_id": 22},
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = ImageMetadata.Response.model_validate(data)
        assert validated.agl_m == 425.0
        assert validated.transect_id == 22

    def test_update_image_metadata_by_int_id(
        self, auth_client: FlaskClient, created_metadata: dict[str, Any]
    ) -> None:
        """Verify updating image metadata fields by integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_metadata (dict[str, Any]): Created metadata fixture.
        """
        response = auth_client.patch(
            f"{METADATA_URL}/{created_metadata['metadata_id']}",
            json={"yaw_deg": 95.5, "pitch_deg": -85.0},
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = ImageMetadata.Response.model_validate(data)
        assert validated.yaw_deg == 95.5
        assert validated.pitch_deg == -85.0

    def test_update_image_metadata_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when updating non-existent metadata IDs.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert (
            auth_client.patch(
                f"{METADATA_URL}/{uuid4()}", json={"agl_m": 100.0}
            ).status_code
            == 404
        )

    def test_update_image_metadata_unauthenticated(
        self, client: FlaskClient
    ) -> None:
        """Verify 401 response when updating image metadata unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert (
            client.patch(
                f"{METADATA_URL}/{uuid4()}", json={"agl_m": 100.0}
            ).status_code
            == 401
        )

    # -------------------------------------------------------------------------
    # 4. DELETE Image Metadata (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_delete_image_metadata_by_uuid(
        self, auth_client: FlaskClient, created_metadata: dict[str, Any]
    ) -> None:
        """Verify deleting image metadata by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_metadata (dict[str, Any]): Created metadata fixture.
        """
        del_res = auth_client.delete(
            f"{METADATA_URL}/{created_metadata['uuid']}"
        )
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert (
            auth_client.get(
                f"{METADATA_URL}/{created_metadata['uuid']}"
            ).status_code
            == 404
        )

    def test_delete_image_metadata_by_int_id(
        self, auth_client: FlaskClient, created_metadata: dict[str, Any]
    ) -> None:
        """Verify deleting image metadata by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_metadata (dict[str, Any]): Created metadata fixture.
        """
        del_res = auth_client.delete(
            f"{METADATA_URL}/{created_metadata['metadata_id']}"
        )
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert (
            auth_client.get(
                f"{METADATA_URL}/{created_metadata['metadata_id']}"
            ).status_code
            == 404
        )

    def test_delete_image_metadata_non_existent_idempotent(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify deleting non-existent metadata IDs succeeds idempotently with 204.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.delete(f"{METADATA_URL}/{uuid4()}").status_code == 204
        assert auth_client.delete(f"{METADATA_URL}/999999999").status_code == 204

    def test_delete_image_metadata_unauthenticated(
        self, client: FlaskClient
    ) -> None:
        """Verify 401 response when deleting image metadata unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.delete(f"{METADATA_URL}/{uuid4()}").status_code == 401
        assert client.delete(f"{METADATA_URL}/1").status_code == 401
