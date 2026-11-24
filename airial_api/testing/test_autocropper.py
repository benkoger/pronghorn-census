"""Integration and unit tests for the AutoCropper API endpoints."""

from collections.abc import Generator
from typing import Any
from uuid import UUID, uuid4

import pytest
from flask.testing import FlaskClient
from testing_core import APITester

from app.extensions import base, cache
from database.object_models.core.images import Image, ReviewedArea
from database.object_models.core.predictions import Prediction

AUTOCROPPER_URL = "/api/v1/autocropper"
BATCH_URL = f"{AUTOCROPPER_URL}/batch"
SURVEY_UUID = "f4c0b5e0-af30-46fa-a276-6169932b6a34"
HERD_UNIT_UUID = "4317a307-9595-4116-be11-c7584561dd8d"
MODEL_UUID = "f5f4caad-1fd4-46a7-982e-21d396a36d48"
ALL_LABEL_IDS = [2, 3, 4, 5, 6]


class TestAutoCropper(APITester):
    """Test suite covering the `/api/v1/autocropper` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients,
    mocked S3 storage, and automatic database transaction rollbacks.
    """

    @pytest.fixture
    def candidate_batch(self, auth_client: FlaskClient) -> list[dict[str, Any]]:
        """Fetch a candidate batch of unreviewed images and predictions.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.

        Returns:
            list[dict[str, Any]]: List of image/prediction batch dictionaries.
        """
        res = auth_client.get(
            BATCH_URL,
            query_string={
                "survey_id": SURVEY_UUID,
                "herd_unit_id": HERD_UNIT_UUID,
                "model_id": MODEL_UUID,
                "label": [2, 3],
                "batch_size": 2,
                "min_confidence": 0.5,
            },
        )
        assert res.status_code == 200
        batch = res.get_json()
        assert isinstance(batch, list)
        assert len(batch) >= 1
        return batch

    @pytest.fixture
    def staged_batch_image(
        self, auth_client: FlaskClient, candidate_batch: list[dict[str, Any]]
    ) -> Generator[dict[str, Any]]:
        """Upload synthetic JPEG bytes to mocked S3 for the first batch image.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            candidate_batch (list[dict[str, Any]]): Candidate batch fixture.

        Yields:
            dict[str, Any]: First batch entry ready for POST /api/v1/autocropper.
        """
        entry = candidate_batch[0]
        image_uuid = entry["uuid"]
        image_obj = base.get(Image, UUID(image_uuid))

        jpeg_bytes = self._generate_jpeg_bytes(
            width=image_obj.image_width_px,
            height=image_obj.image_length_px,
            color="green",
        )
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=image_obj.img_key,
            Body=jpeg_bytes,
            ContentType="image/jpeg",
        )
        cache.delete(image_obj.uuid)

        yield entry

        cache.delete(image_obj.uuid)

    # -------------------------------------------------------------------------
    # 1. GET Autocropper Batch
    # -------------------------------------------------------------------------

    def test_fetch_batch_success(self, auth_client: FlaskClient) -> None:
        """Verify fetching a batch returns images with nested predictions and locks them.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            BATCH_URL,
            query_string={
                "survey_id": SURVEY_UUID,
                "herd_unit_id": HERD_UNIT_UUID,
                "model_id": MODEL_UUID,
                "label": [2, 3],
                "batch_size": 1,
                "min_confidence": 0.5,
            },
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        item = data[0]
        assert "uuid" in item
        assert "image_id" in item
        assert isinstance(item["predictions"], list)
        assert len(item["predictions"]) >= 1
        assert "dimensions" in item["predictions"][0]

        locked_image = base.get(Image, item["image_id"])
        assert locked_image.opened_by_user_id != 0

    def test_fetch_batch_invalid_query(self, auth_client: FlaskClient) -> None:
        """Verify 400 validation error when required query parameters are missing.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.get(BATCH_URL).status_code == 400
        assert (
            auth_client.get(
                BATCH_URL, query_string={"survey_id": SURVEY_UUID}
            ).status_code
            == 400
        )

    def test_fetch_batch_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 response when referencing a non-existent herd unit UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            BATCH_URL,
            query_string={
                "survey_id": SURVEY_UUID,
                "herd_unit_id": str(uuid4()),
                "model_id": MODEL_UUID,
                "label": [2, 3],
                "batch_size": 1,
                "min_confidence": 0.5,
            },
        )
        assert response.status_code == 404

    def test_fetch_batch_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when fetching autocropper batch unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.get(
            BATCH_URL,
            query_string={
                "survey_id": SURVEY_UUID,
                "herd_unit_id": HERD_UNIT_UUID,
                "model_id": MODEL_UUID,
                "label": [2, 3],
                "batch_size": 1,
                "min_confidence": 0.5,
            },
        )
        assert response.status_code == 401

    # -------------------------------------------------------------------------
    # 2. POST Auto-Crop Image
    # -------------------------------------------------------------------------

    def test_auto_crop_image_success(
        self, auth_client: FlaskClient, staged_batch_image: dict[str, Any]
    ) -> None:
        """Verify auto-cropping generates crops, annotations, S3 files, and unlocks image.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            staged_batch_image (dict[str, Any]): Batch image with staged S3 JPEG.
        """
        image_uuid = staged_batch_image["uuid"]
        image_id = staged_batch_image["image_id"]
        preds = staged_batch_image["predictions"][:2]

        payload = {
            "image_id": image_uuid,
            "predictions": preds,
            "label_ids": ALL_LABEL_IDS,
        }
        response = auth_client.post(AUTOCROPPER_URL, json=payload)
        assert response.status_code == 201
        assert response.data == b""

        # Image lock should be released.
        unlocked = base.get(Image, image_id)
        assert unlocked.opened_by_user_id == 0

        # Predictions should be marked reviewed.
        for p in preds:
            updated_pred = base.get(Prediction, p["pred_id"])
            assert updated_pred.reviewed_by_user_id != 0

        # Crops should exist in DB and S3.
        crops = base.where(ReviewedArea, {"image_id": image_id})
        assert len(crops) >= 1
        s3_objects = self.s3.list_objects_v2(
            Bucket=self.bucket_name, Prefix=f"images/{image_uuid}/reviewed_area/"
        )
        assert s3_objects.get("KeyCount", 0) >= 1

    def test_auto_crop_image_invalid_payload(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 400 validation errors for invalid auto-crop payloads.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.post(AUTOCROPPER_URL, json={}).status_code == 400
        assert (
            auth_client.post(
                AUTOCROPPER_URL, json={"image_id": str(uuid4())}
            ).status_code
            == 400
        )

    def test_auto_crop_image_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 response when auto-cropping a non-existent image UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        payload = {
            "image_id": str(uuid4()),
            "predictions": [],
            "label_ids": ALL_LABEL_IDS,
        }
        response = auth_client.post(AUTOCROPPER_URL, json=payload)
        assert response.status_code == 404

    def test_auto_crop_image_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when invoking auto-crop unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.post(
            AUTOCROPPER_URL,
            json={
                "image_id": str(uuid4()),
                "predictions": [],
                "label_ids": ALL_LABEL_IDS,
            },
        )
        assert response.status_code == 401
