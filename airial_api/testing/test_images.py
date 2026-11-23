"""Integration and unit tests for the Images API endpoints."""

import hashlib
import io
from typing import Any
from uuid import uuid4

import pytest
from flask import FlaskClient
from PIL import Image as PILImage
from pydantic import BaseModel
from testing_core import APITester

from app.extensions import cache
from database.object_models.core.annotations import Annotation
from database.object_models.core.image_footprints import ImageFootprint
from database.object_models.core.image_metadata import ImageMetadata
from database.object_models.core.images import Image, ReviewedArea
from database.object_models.core.predictions import Prediction


class TestImages(APITester):
    """Test suite covering the `/api/v1/images` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients, mocked S3
    buckets, and automatic database transaction rollbacks for isolation.
    """

    # -------------------------------------------------------------------------
    # 1. GET Single & List Endpoint Schema Validation
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "endpoint, expected_schema, is_list",
        [
            (
                "/api/v1/images/26be495e-3ec2-41c8-ba14-d0b65726bb67",
                Image.Response,
                False,
            ),
            (
                "/api/v1/images/26be495e-3ec2-41c8-ba14-d0b65726bb67/predictions",
                Prediction.Response,
                True,
            ),
            (
                "/api/v1/images/26be495e-3ec2-41c8-ba14-d0b65726bb67/crops",
                ReviewedArea.Response,
                True,
            ),
            (
                "/api/v1/images/26be495e-3ec2-41c8-ba14-d0b65726bb67/annotations",
                Annotation.Response,
                True,
            ),
            (
                "/api/v1/images/26be495e-3ec2-41c8-ba14-d0b65726bb67/metadata",
                ImageMetadata.Response,
                True,
            ),
            (
                "/api/v1/images/26be495e-3ec2-41c8-ba14-d0b65726bb67/footprints",
                ImageFootprint.Response,
                True,
            ),
        ],
    )
    def test_get_endpoints_schema_success(
        self,
        auth_client: FlaskClient,
        endpoint: str,
        expected_schema: type[BaseModel],
        is_list: bool,
    ) -> None:
        """Validates that GET image endpoints return 200 OK and match expected schemas.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            endpoint (str): The API endpoint path to request.
            expected_schema (type[BaseModel]): Pydantic model class used to validate
                the payload structure.
            is_list (bool): Flag indicating whether the expected response payload
                is a list of records or a single object.
        """
        response = auth_client.get(endpoint)
        assert response.status_code == 200

        data = response.get_json()
        if is_list:
            for item in data:
                expected_schema.model_validate(item)
        else:
            expected_schema.model_validate(data)

    # -------------------------------------------------------------------------
    # 2. GET Not Found / Authorization Edge Cases
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "path_suffix",
        [
            "",
            "/predictions",
        ],
    )
    def test_get_image_not_found(
        self, auth_client: FlaskClient, path_suffix: str
    ) -> None:
        """Verifies that requesting a non-existent image UUID returns a 404 status.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            path_suffix (str): Additional endpoint sub-path appended to the non-existent
                image UUID (e.g., "" or "/predictions").
        """
        random_uuid = str(uuid4())
        response = auth_client.get(f"/api/v1/images/{random_uuid}{path_suffix}")
        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # 3. POST Endpoint Validation & Payloads
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "endpoint, payload, expected_status",
        [
            # Valid image creation
            (
                "/api/v1/images",
                {
                    "name": f"pronghorn_{uuid4().hex[:6]}",
                    "herd_unit_ids": {
                        "pkey": 1,
                        "uuid": "4317a307-9595-4116-be11-c7584561dd8d",
                    },
                    "survey_ids": {
                        "pkey": 1,
                        "uuid": "f4c0b5e0-af30-46fa-a276-6169932b6a34",
                    },
                    "img_key": f"s3://bucket/test_{uuid4().hex}.jpg",
                    "image_length_px": 1080,
                    "image_width_px": 1920,
                },
                201,
            ),
            # Invalid image creation (missing fields)
            (
                "/api/v1/images",
                {"name": "incomplete_image"},
                400,
            ),
            # Presigned URL creation
            (
                "/api/v1/images/presigned-get-url",
                {
                    "image_id": "26be495e-3ec2-41c8-ba14-d0b65726bb67",
                    "expires_in": 3600,
                },
                201,
            ),
            # Presigned URL creation (failure)
            (
                "/api/v1/images/presigned-get-url",
                {
                    "image_id": str(uuid4()),
                    "expires_in": 3600,
                },
                404,
            ),
            # Multipart upload creation
            (
                "/api/v1/images/create-multipart-upload",
                {"image_key": f"uploads/new_capture_{uuid4().hex[:6]}.jpg"},
                201,
            ),
            # Presigned POST
            (
                "/api/v1/images/presigned-put-url",
                {
                    "image_id": "26be495e-3ec2-41c8-ba14-d0b65726bb67",
                    "upload_id": "5",
                    "part_number": 67,
                    "chunk_size": 4,
                    "chunk_md5": hashlib.md5(b"post_me").hexdigest(),
                },
                201,
            ),
        ],
    )
    def test_post_endpoints(
        self,
        auth_client: FlaskClient,
        endpoint: str,
        payload: dict[str, Any],
        expected_status: int,
    ) -> None:
        """Tests POST endpoints for image creation, presigned URLs, and multipart setup.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            endpoint (str): The API endpoint path to which the POST request is sent.
            payload (dict[str, Any]): JSON payload body sent in the request.
            expected_status (int): The expected HTTP status code of the response.
        """
        response = auth_client.post(endpoint, json=payload)
        assert response.status_code == expected_status

    # -------------------------------------------------------------------------
    # 4. State-Mutating Lifecycles (PATCH & DELETE)
    # -------------------------------------------------------------------------

    def test_update_image_success(self, auth_client: FlaskClient) -> None:
        """Tests updating image metadata via the PATCH endpoint.

        Verifies that an existing image can be fetched, updated with a new name,
        and that the returned JSON payload confirms the modification.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        img_id = "26be495e-3ec2-41c8-ba14-d0b65726bb67"
        new_name = f"updated_{uuid4().hex[:4]}"

        assert auth_client.get(f"/api/v1/images/{img_id}").status_code == 200

        response = auth_client.patch(
            f"/api/v1/images/{img_id}", json={"name": new_name}
        )
        assert response.status_code == 200
        assert response.get_json()["name"] == new_name

    def test_delete_image_lifecycle(self, auth_client: FlaskClient) -> None:
        """Tests the full lifecycle of creating and subsequently deleting an image.

        Ensures that a newly created image responds with 201 Created, can be retrieved
        with 200 OK, is successfully deleted with 204 No Content, and is subsequently
        unreachable via GET (returning 404 Not Found).

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        payload = {
            "name": f"pronghorn_{uuid4().hex[:6]}",
            "herd_unit_ids": {
                "pkey": 1,
                "uuid": "4317a307-9595-4116-be11-c7584561dd8d",
            },
            "survey_ids": {
                "pkey": 1,
                "uuid": "f4c0b5e0-af30-46fa-a276-6169932b6a34",
            },
            "img_key": f"s3://temp/delete_{uuid4().hex}.jpg",
            "image_length_px": 100,
            "image_width_px": 101,
        }

        create_res = auth_client.post("/api/v1/images", json=payload)
        assert create_res.status_code == 201

        target_id = create_res.get_json()["uuid"]
        assert auth_client.get(f"/api/v1/images/{target_id}").status_code == 200

        delete_res = auth_client.delete(f"/api/v1/images/{target_id}")
        assert delete_res.status_code == 204

        # SpiceDB relationships are not deleted yet (needs fixed).
        assert auth_client.get(f"/api/v1/images/{target_id}").status_code == 404

    # -------------------------------------------------------------------------
    # 5. Coverage for Prediction Crops & Cache Routes
    # -------------------------------------------------------------------------

    def test_get_prediction_crop_not_found(self, auth_client: FlaskClient) -> None:
        """Verifies that requesting a non-existent prediction crop returns 404 Not Found.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        res_404 = auth_client.get(f"/api/v1/images/prediction_crops/{uuid4()!s}")
        assert res_404.status_code == 404

    def test_create_prediction_crops_cache_miss_success(
        self, auth_client: FlaskClient
    ) -> None:
        """Tests prediction crop creation on cache miss, fetching from S3 and populating cache.

        Simulates an initial cache miss by clearing Valkey, seeds mock S3 with image
        bytes, requests crop generation, verifies that the raw image is cached, and
        validates that the resulting crop is stored and returned as a valid WebP image.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        img_id = "26be495e-3ec2-41c8-ba14-d0b65726bb67"

        img_res = auth_client.get(f"/api/v1/images/{img_id}")
        assert img_res.status_code == 200
        img_key = img_res.get_json()["img_key"]

        # Seed S3 object
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=img_key,
            Body=self._generate_jpeg_bytes(1000, 1000),
        )

        # Force cache miss
        cache.delete(img_id)
        assert cache.get(img_id) is None

        preds_res = auth_client.get(f"/api/v1/images/{img_id}/predictions")
        preds = preds_res.get_json()
        pred_ids = [pred["uuid"] for pred in preds]

        # POST triggers S3 fetch & caches image data
        payload = {"image_id": img_id, "prediction_id": pred_ids}
        response = auth_client.post("/api/v1/images/prediction_crops", json=payload)
        assert response.status_code == 200

        # Verify image was saved to cache
        assert cache.get(img_id) is not None

        # Verify crop is a valid WebP image
        target_pred_id = pred_ids[0]
        crop_res = auth_client.get(f"/api/v1/images/prediction_crops/{target_pred_id}")
        assert crop_res.status_code == 200
        assert crop_res.mimetype == "image/webp"

        decoded_img = PILImage.open(io.BytesIO(crop_res.data))
        assert decoded_img.format == "WEBP"
        assert decoded_img.width > 0
        assert decoded_img.height > 0

    def test_create_prediction_crops_cache_hit_success(
        self, auth_client: FlaskClient
    ) -> None:
        """Tests prediction crop generation when source image bytes are already cached.

        Pre-populates the cache with raw JPEG image bytes to simulate a cache hit,
        invokes the crop generation endpoint, and verifies that the resulting crop
        is created without needing to fetch from S3 and is returned as a valid WebP image.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        img_id = "26be495e-3ec2-41c8-ba14-d0b65726bb67"

        img_res = auth_client.get(f"/api/v1/images/{img_id}")
        assert img_res.status_code == 200

        # Seed cache directly before request to force cache hit
        raw_jpeg_bytes = self._generate_jpeg_bytes(1000, 1000)
        cache.set(img_id, raw_jpeg_bytes, 500)

        preds_res = auth_client.get(f"/api/v1/images/{img_id}/predictions")
        preds = preds_res.get_json()
        pred_ids = [pred["uuid"] for pred in preds]

        # POST skips S3 and uses cached image
        payload = {"image_id": img_id, "prediction_id": pred_ids}
        response = auth_client.post("/api/v1/images/prediction_crops", json=payload)
        assert response.status_code == 200

        # Verify crop retrieval
        target_pred_id = pred_ids[0]
        crop_res = auth_client.get(f"/api/v1/images/prediction_crops/{target_pred_id}")
        assert crop_res.status_code == 200

        decoded_img = PILImage.open(io.BytesIO(crop_res.data))
        assert decoded_img.format == "WEBP"
        assert decoded_img.width > 0
        assert decoded_img.height > 0

    # -------------------------------------------------------------------------
    # 6. Coverage for Multipart Complete & Abort
    # -------------------------------------------------------------------------

    def test_abort_multipart_upload_success(self, auth_client: FlaskClient) -> None:
        """Tests aborting an active S3 multipart upload session.

        Initializes a multipart upload session and verifies that sending an abort
        request returns 200 OK and cleans up the upload state.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        key = f"uploads/test_abort_{uuid4().hex[:6]}.jpg"

        upload_res = auth_client.post(
            "/api/v1/images/create-multipart-upload",
            json={"image_key": key},
        )
        assert upload_res.status_code == 201

        upload_id = upload_res.data.decode("utf-8").strip('"')

        abort_payload = {
            "image_key": key,
            "upload_id": upload_id,
        }
        response = auth_client.post(
            "/api/v1/images/abort-multipart-upload", json=abort_payload
        )

        assert response.status_code == 200

    def test_complete_multipart_upload_success(self, auth_client: FlaskClient) -> None:
        """Tests the complete multipart upload flow including part upload and completion.

        Initializes an upload session, requests a presigned PUT URL for a part chunk,
        uploads the part chunk directly to mock S3, and sends the completion payload
        verifying that the server responds with 200 OK.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        key = f"uploads/test_complete_{uuid4().hex[:6]}.jpg"

        init_res = auth_client.post(
            "/api/v1/images/create-multipart-upload",
            json={"image_key": key},
        )
        assert init_res.status_code == 201
        upload_id = init_res.data.decode("utf-8").strip('"')

        chunk_data = self._generate_jpeg_bytes(
            width=10, height=10
        )  # Fake JPEG blob bytes
        chunk_md5 = hashlib.md5(chunk_data).hexdigest()

        put_res = auth_client.post(
            "/api/v1/images/presigned-put-url",
            json={
                "image_id": "26be495e-3ec2-41c8-ba14-d0b65726bb67",
                "upload_id": upload_id,
                "part_number": 1,
                "chunk_size": len(chunk_data),
                "chunk_md5": chunk_md5,
            },
        )
        assert put_res.status_code == 201

        part_res = self.s3.upload_part(
            Bucket=self.bucket_name,
            Key=key,
            UploadId=upload_id,
            PartNumber=1,
            Body=chunk_data,
        )

        complete_payload = {
            "image_key": key,
            "upload_id": upload_id,
            "parts": [
                {
                    "PartNumber": 1,
                    "ETag": part_res["ETag"],
                }
            ],
        }
        response = auth_client.post(
            "/api/v1/images/complete-multipart-upload", json=complete_payload
        )
        assert response.status_code == 200

    # -------------------------------------------------------------------------
    # 7. Coverage for Closing User Images
    # -------------------------------------------------------------------------

    def test_close_user_images_success(self, auth_client: FlaskClient) -> None:
        """Tests closing active image viewer sessions for the authenticated user.

        Sends a PATCH request to close any open images associated with the user
        and asserts that the operation succeeds with a 200 OK status.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.patch("/api/v1/images/close-user-images")
        assert response.status_code == 200
