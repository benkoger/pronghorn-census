"""Integration and unit tests for the Image Footprints API endpoints."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from flask.testing import FlaskClient
from testing_core import APITester

from database.object_models.core.image_footprints import ImageFootprint

FOOTPRINTS_URL = "/api/v1/image-footprints"
IMAGE_KEYRING = {"pkey": 1047, "uuid": "26be495e-3ec2-41c8-ba14-d0b65726bb67"}


def _build_footprint_payload(has_detection: bool = True) -> dict[str, Any]:
    """Build a valid image footprint creation payload.

    Args:
        has_detection (bool): Whether the image contains detections. Defaults to True.

    Returns:
        dict[str, Any]: Valid CreateImageFootprintReq payload dictionary.
    """
    polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [-105.60, 41.30],
                [-105.59, 41.30],
                [-105.59, 41.31],
                [-105.60, 41.31],
                [-105.60, 41.30],
            ]
        ],
    }
    return {
        "image_ids": IMAGE_KEYRING,
        "footprint": polygon,
        "has_detection": has_detection,
        "footprint_metadata": polygon,
        "bbox_wsen": [-105.60, 41.30, -105.59, 41.31],
        "footprint_partial": False,
        "area_m2": 12500.0,
        "area_geodesic_m2": 12505.5,
        "area_sigma_m2": 15.2,
        "area_q05_m2": 12480.0,
        "area_q95_m2": 12530.0,
        "dem_name": "USGS_13_n42w106",
        "georef_status": "ok",
        "n_ties": 12,
        "tie_residual_before_m": 1.8,
        "rmse_h_m": 0.45,
        "rmse_p50_m": 0.35,
        "rmse_p90_m": 0.72,
        "n_checkpoints": 4,
        "pose_delta": [0.1, -0.2, 0.05, 0.01, -0.02, 0.03],
        "pose_sigma": [0.05, 0.05, 0.08, 0.01, 0.01, 0.02],
        "pose_free": ["x", "y", "z"],
        "pose_cond": 14.5,
        "prior_source": "exif",
        "gcps": [{"id": 1, "lon": -105.595, "lat": 41.305}],
        "overlay_uri": "s3://pronghorn-count-test/overlays/test_overlay.png",
        "georef_modified": datetime(2025, 6, 15, 14, 30, 0, tzinfo=UTC).isoformat(),
    }


class TestImageFootprints(APITester):
    """Test suite covering the `/api/v1/image-footprints` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients and
    automatic database transaction rollbacks for isolation.
    """

    @pytest.fixture
    def created_footprint(self, auth_client: FlaskClient) -> dict[str, Any]:
        """Create a sample image footprint record inside the rolled-back transaction.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.

        Returns:
            dict[str, Any]: Serialized created ImageFootprint dictionary.
        """
        res = auth_client.post(FOOTPRINTS_URL, json=_build_footprint_payload())
        assert res.status_code == 201
        return res.get_json()

    # -------------------------------------------------------------------------
    # 1. POST Create Image Footprint
    # -------------------------------------------------------------------------

    def test_create_image_footprint_success(self, auth_client: FlaskClient) -> None:
        """Verify creating an image footprint and validating response schema.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        payload = _build_footprint_payload(has_detection=True)
        response = auth_client.post(FOOTPRINTS_URL, json=payload)
        assert response.status_code == 201

        data = response.get_json()
        validated = ImageFootprint.Response.model_validate(data)
        assert validated.image_id == IMAGE_KEYRING["pkey"]
        assert validated.has_detection is True
        assert validated.dem_name == "USGS_13_n42w106"
        assert validated.georef_status == "ok"
        assert validated.footprint is not None
        assert validated.footprint["type"] == "Polygon"

    def test_create_image_footprint_invalid(self, auth_client: FlaskClient) -> None:
        """Verify 400 validation errors for invalid footprint payloads.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.post(FOOTPRINTS_URL, json={}).status_code == 400
        assert (
            auth_client.post(
                FOOTPRINTS_URL, json={"image_ids": IMAGE_KEYRING}
            ).status_code
            == 400
        )

    def test_create_image_footprint_unauthenticated(
        self, client: FlaskClient
    ) -> None:
        """Verify 401 response when creating a footprint unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.post(FOOTPRINTS_URL, json=_build_footprint_payload())
        assert response.status_code == 401

    # -------------------------------------------------------------------------
    # 2. GET Image Footprint by ID (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_get_image_footprint_by_uuid(
        self, auth_client: FlaskClient, created_footprint: dict[str, Any]
    ) -> None:
        """Verify retrieving an image footprint by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_footprint (dict[str, Any]): Created footprint fixture.
        """
        response = auth_client.get(
            f"{FOOTPRINTS_URL}/{created_footprint['uuid']}"
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = ImageFootprint.Response.model_validate(data)
        assert str(validated.uuid) == created_footprint["uuid"]
        assert validated.footprint_id == created_footprint["footprint_id"]

    def test_get_image_footprint_by_int_id(
        self, auth_client: FlaskClient, created_footprint: dict[str, Any]
    ) -> None:
        """Verify retrieving an image footprint by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_footprint (dict[str, Any]): Created footprint fixture.
        """
        response = auth_client.get(
            f"{FOOTPRINTS_URL}/{created_footprint['footprint_id']}"
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = ImageFootprint.Response.model_validate(data)
        assert validated.footprint_id == created_footprint["footprint_id"]
        assert str(validated.uuid) == created_footprint["uuid"]

    def test_get_image_footprint_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 responses for non-existent footprint UUID and integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.get(f"{FOOTPRINTS_URL}/{uuid4()}").status_code == 404
        assert auth_client.get(f"{FOOTPRINTS_URL}/999999999").status_code == 404

    def test_get_image_footprint_unauthenticated(
        self, client: FlaskClient
    ) -> None:
        """Verify 401 response when fetching a footprint unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.get(f"{FOOTPRINTS_URL}/{uuid4()}").status_code == 401
        assert client.get(f"{FOOTPRINTS_URL}/1").status_code == 401

    # -------------------------------------------------------------------------
    # 3. PATCH Update Image Footprint (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_update_image_footprint_by_uuid(
        self, auth_client: FlaskClient, created_footprint: dict[str, Any]
    ) -> None:
        """Verify updating image footprint fields by UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_footprint (dict[str, Any]): Created footprint fixture.
        """
        response = auth_client.patch(
            f"{FOOTPRINTS_URL}/{created_footprint['uuid']}",
            json={"has_detection": False, "georef_status": "verified"},
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = ImageFootprint.Response.model_validate(data)
        assert validated.has_detection is False
        assert validated.georef_status == "verified"

    def test_update_image_footprint_by_int_id(
        self, auth_client: FlaskClient, created_footprint: dict[str, Any]
    ) -> None:
        """Verify updating image footprint fields by integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_footprint (dict[str, Any]): Created footprint fixture.
        """
        response = auth_client.patch(
            f"{FOOTPRINTS_URL}/{created_footprint['footprint_id']}",
            json={"area_m2": 13000.0, "n_ties": 18},
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = ImageFootprint.Response.model_validate(data)
        assert validated.area_m2 == 13000.0
        assert validated.n_ties == 18

    def test_update_image_footprint_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when updating non-existent footprint IDs.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert (
            auth_client.patch(
                f"{FOOTPRINTS_URL}/{uuid4()}", json={"n_ties": 5}
            ).status_code
            == 404
        )

    def test_update_image_footprint_unauthenticated(
        self, client: FlaskClient
    ) -> None:
        """Verify 401 response when updating a footprint unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert (
            client.patch(
                f"{FOOTPRINTS_URL}/{uuid4()}", json={"n_ties": 5}
            ).status_code
            == 401
        )

    # -------------------------------------------------------------------------
    # 4. DELETE Image Footprint (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_delete_image_footprint_by_uuid(
        self, auth_client: FlaskClient, created_footprint: dict[str, Any]
    ) -> None:
        """Verify deleting an image footprint by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_footprint (dict[str, Any]): Created footprint fixture.
        """
        del_res = auth_client.delete(
            f"{FOOTPRINTS_URL}/{created_footprint['uuid']}"
        )
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert (
            auth_client.get(
                f"{FOOTPRINTS_URL}/{created_footprint['uuid']}"
            ).status_code
            == 404
        )

    def test_delete_image_footprint_by_int_id(
        self, auth_client: FlaskClient, created_footprint: dict[str, Any]
    ) -> None:
        """Verify deleting an image footprint by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            created_footprint (dict[str, Any]): Created footprint fixture.
        """
        del_res = auth_client.delete(
            f"{FOOTPRINTS_URL}/{created_footprint['footprint_id']}"
        )
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert (
            auth_client.get(
                f"{FOOTPRINTS_URL}/{created_footprint['footprint_id']}"
            ).status_code
            == 404
        )

    def test_delete_image_footprint_non_existent_idempotent(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify deleting non-existent footprint IDs succeeds idempotently with 204.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.delete(f"{FOOTPRINTS_URL}/{uuid4()}").status_code == 204
        assert auth_client.delete(f"{FOOTPRINTS_URL}/999999999").status_code == 204

    def test_delete_image_footprint_unauthenticated(
        self, client: FlaskClient
    ) -> None:
        """Verify 401 response when deleting a footprint unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.delete(f"{FOOTPRINTS_URL}/{uuid4()}").status_code == 401
        assert client.delete(f"{FOOTPRINTS_URL}/1").status_code == 401
