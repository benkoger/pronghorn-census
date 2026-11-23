"""Integration and unit tests for the Annotations API endpoints."""

from typing import Any
from uuid import uuid4

import pytest
from flask.testing import FlaskClient
from testing_core import APITester

from database.object_models.core.activity import ActivityType
from database.object_models.core.annotations import Annotation

IMAGE_ID = 1047
IMAGE_UUID = "26be495e-3ec2-41c8-ba14-d0b65726bb67"
HERD_UNIT_ID = 1
LABEL_ID = 3
ANNOTATIONS_URL = "/api/v1/annotations"


class TestAnnotations(APITester):
    """Test suite covering the `/api/v1/annotations` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients and
    automatic database transaction rollbacks for test isolation.
    """

    @pytest.fixture
    def sample_reviewed_area(self, auth_client: FlaskClient) -> dict[str, Any]:
        """Fetch an existing reviewed area associated with the sample image.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.

        Returns:
            dict[str, Any]: Serialized reviewed area dictionary containing integer
                and UUID identifiers.
        """
        res = auth_client.get(f"/api/v1/images/{IMAGE_UUID}/crops")
        assert res.status_code == 200
        crops = res.get_json()
        assert crops, "Sample image should contain at least one reviewed area crop."
        return crops[0]

    def _build_payload(
        self,
        reviewed_area: dict[str, Any],
        box_tx: int = 100,
        box_ty: int = 100,
        box_bx: int = 200,
        box_by: int = 200,
    ) -> dict[str, Any]:
        """Build a valid payload for creating an annotation record.

        Args:
            reviewed_area (dict[str, Any]): The parent reviewed area dictionary.
            box_tx (int): Top-left X pixel coordinate.
            box_ty (int): Top-left Y pixel coordinate.
            box_bx (int): Bottom-right X pixel coordinate.
            box_by (int): Bottom-right Y pixel coordinate.

        Returns:
            dict[str, Any]: Annotation creation request payload.
        """
        return {
            "label_id": LABEL_ID,
            "image_ids": {"pkey": IMAGE_ID, "uuid": IMAGE_UUID},
            "herd_unit_id": HERD_UNIT_ID,
            "box_tx": box_tx,
            "box_ty": box_ty,
            "box_bx": box_bx,
            "box_by": box_by,
            "uuid": str(uuid4()),
            "type": ActivityType.AUTO_CROPPER.value,
            "reviewed_area_ids": {
                "pkey": reviewed_area["reviewed_area_id"],
                "uuid": reviewed_area["uuid"],
            },
        }

    # -------------------------------------------------------------------------
    # 1. Single Annotation Creation & Validation
    # -------------------------------------------------------------------------

    def test_create_annotation_success(
        self, auth_client: FlaskClient, sample_reviewed_area: dict[str, Any]
    ) -> None:
        """Verify successful creation of a single annotation record.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_reviewed_area (dict[str, Any]): Sample reviewed area fixture.
        """
        payload = self._build_payload(sample_reviewed_area)
        response = auth_client.post(ANNOTATIONS_URL, json=payload)
        assert response.status_code == 201

        data = response.get_json()
        validated = Annotation.Response.model_validate(data)
        assert validated.label_id == LABEL_ID
        assert validated.image_id == IMAGE_ID
        assert validated.herd_unit_id == HERD_UNIT_ID
        assert str(validated.uuid) == payload["uuid"]
        assert validated.dimensions == {
            "top_left": {"x": 100, "y": 100},
            "bottom_right": {"x": 200, "y": 200},
        }

    def test_create_annotation_invalid(self, auth_client: FlaskClient) -> None:
        """Verify 400 response when creating an annotation with invalid payload.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.post(ANNOTATIONS_URL, json={"label_id": LABEL_ID})
        assert response.status_code == 400

    # -------------------------------------------------------------------------
    # 2. Annotation Update (Single by UUID and Integer ID)
    # -------------------------------------------------------------------------

    def test_update_annotation_by_uuid(
        self, auth_client: FlaskClient, sample_reviewed_area: dict[str, Any]
    ) -> None:
        """Verify updating an annotation by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_reviewed_area (dict[str, Any]): Sample reviewed area fixture.
        """
        payload = self._build_payload(sample_reviewed_area)
        created = auth_client.post(ANNOTATIONS_URL, json=payload).get_json()

        update_payload = {"box_tx": 150, "box_ty": 150, "box_bx": 250, "box_by": 250}
        response = auth_client.patch(
            f"{ANNOTATIONS_URL}/{created['uuid']}", json=update_payload
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = Annotation.Response.model_validate(data)
        assert validated.dimensions == {
            "top_left": {"x": 150, "y": 150},
            "bottom_right": {"x": 250, "y": 250},
        }

    def test_update_annotation_by_int_id(
        self, auth_client: FlaskClient, sample_reviewed_area: dict[str, Any]
    ) -> None:
        """Verify updating an annotation by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_reviewed_area (dict[str, Any]): Sample reviewed area fixture.
        """
        payload = self._build_payload(sample_reviewed_area)
        created = auth_client.post(ANNOTATIONS_URL, json=payload).get_json()

        update_payload = {"box_tx": 120, "box_ty": 130}
        response = auth_client.patch(
            f"{ANNOTATIONS_URL}/{created['annotation_id']}", json=update_payload
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = Annotation.Response.model_validate(data)
        assert validated.dimensions["top_left"]["x"] == 120
        assert validated.dimensions["top_left"]["y"] == 130

    def test_update_annotation_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 response when attempting to update non-existent annotation.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.patch(
            f"{ANNOTATIONS_URL}/{uuid4()}", json={"box_tx": 50}
        )
        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # 3. Annotation Deletion (Single by UUID and Integer ID)
    # -------------------------------------------------------------------------

    def test_delete_annotation_by_uuid(
        self, auth_client: FlaskClient, sample_reviewed_area: dict[str, Any]
    ) -> None:
        """Verify deleting an annotation by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_reviewed_area (dict[str, Any]): Sample reviewed area fixture.
        """
        payload = self._build_payload(sample_reviewed_area)
        created = auth_client.post(ANNOTATIONS_URL, json=payload).get_json()

        delete_res = auth_client.delete(f"{ANNOTATIONS_URL}/{created['uuid']}")
        assert delete_res.status_code == 204

        # Verify updating deleted annotation returns 404
        assert (
            auth_client.patch(
                f"{ANNOTATIONS_URL}/{created['uuid']}", json={"box_tx": 10}
            ).status_code
            == 404
        )

    def test_delete_annotation_by_int_id(
        self, auth_client: FlaskClient, sample_reviewed_area: dict[str, Any]
    ) -> None:
        """Verify deleting an annotation by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_reviewed_area (dict[str, Any]): Sample reviewed area fixture.
        """
        payload = self._build_payload(sample_reviewed_area)
        created = auth_client.post(ANNOTATIONS_URL, json=payload).get_json()

        delete_res = auth_client.delete(
            f"{ANNOTATIONS_URL}/{created['annotation_id']}"
        )
        assert delete_res.status_code == 204

    # -------------------------------------------------------------------------
    # 4. Bulk Operations (Create, Update, Delete)
    # -------------------------------------------------------------------------

    def test_bulk_import_empty(
        self, auth_client: FlaskClient, sample_reviewed_area: dict[str, Any]
    ) -> None:
        """Verify bulk import endpoint returns empty list when given no requests.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_reviewed_area (dict[str, Any]): Sample reviewed area fixture.
        """
        bulk_payload = {
            "reviewed_area_id": sample_reviewed_area["uuid"],
            "requests": [],
        }
        res = auth_client.post(f"{ANNOTATIONS_URL}/bulk-import", json=bulk_payload)
        assert res.status_code == 201
        assert res.get_json() == []

    def test_bulk_import_success(
        self, auth_client: FlaskClient, sample_reviewed_area: dict[str, Any]
    ) -> None:
        """Verify bulk import creating multiple annotations in one request.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_reviewed_area (dict[str, Any]): Sample reviewed area fixture.
        """
        p1 = self._build_payload(sample_reviewed_area, box_tx=10, box_bx=50)
        p2 = self._build_payload(sample_reviewed_area, box_tx=60, box_bx=120)
        bulk_payload = {
            "reviewed_area_id": sample_reviewed_area["uuid"],
            "requests": [p1, p2],
        }

        res = auth_client.post(f"{ANNOTATIONS_URL}/bulk-import", json=bulk_payload)
        assert res.status_code == 201
        data = res.get_json()
        assert len(data) == 2
        for item in data:
            Annotation.Response.model_validate(item)

    def test_bulk_update_success(
        self, auth_client: FlaskClient, sample_reviewed_area: dict[str, Any]
    ) -> None:
        """Verify bulk update of multiple annotations, skipping items without ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_reviewed_area (dict[str, Any]): Sample reviewed area fixture.
        """
        p1 = self._build_payload(sample_reviewed_area, box_tx=10, box_bx=50)
        p2 = self._build_payload(sample_reviewed_area, box_tx=60, box_bx=120)
        c1 = auth_client.post(ANNOTATIONS_URL, json=p1).get_json()
        c2 = auth_client.post(ANNOTATIONS_URL, json=p2).get_json()

        bulk_update_payload = {
            "reviewed_area_id": sample_reviewed_area["uuid"],
            "requests": [
                {"annotation_id": c1["uuid"], "box_tx": 15},
                {"box_tx": 999},
                {"annotation_id": c2["uuid"], "box_tx": 65},
            ],
        }
        res = auth_client.patch(
            f"{ANNOTATIONS_URL}/bulk-update", json=bulk_update_payload
        )
        assert res.status_code == 200
        updated = res.get_json()
        assert len(updated) == 2
        assert updated[0]["dimensions"]["top_left"]["x"] == 15
        assert updated[1]["dimensions"]["top_left"]["x"] == 65

    def test_bulk_delete_success(
        self, auth_client: FlaskClient, sample_reviewed_area: dict[str, Any]
    ) -> None:
        """Verify bulk deletion of multiple annotations.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_reviewed_area (dict[str, Any]): Sample reviewed area fixture.
        """
        p1 = self._build_payload(sample_reviewed_area)
        p2 = self._build_payload(sample_reviewed_area)
        c1 = auth_client.post(ANNOTATIONS_URL, json=p1).get_json()
        c2 = auth_client.post(ANNOTATIONS_URL, json=p2).get_json()

        bulk_del_payload = {
            "requests": [
                {"annotation_id": c1["uuid"]},
                {"annotation_id": c2["uuid"]},
            ]
        }
        res = auth_client.delete(
            f"{ANNOTATIONS_URL}/bulk-delete", json=bulk_del_payload
        )
        assert res.status_code == 204

        # Confirm both are deleted
        assert (
            auth_client.patch(
                f"{ANNOTATIONS_URL}/{c1['uuid']}", json={"box_tx": 1}
            ).status_code
            == 404
        )
        assert (
            auth_client.patch(
                f"{ANNOTATIONS_URL}/{c2['uuid']}", json={"box_tx": 1}
            ).status_code
            == 404
        )
