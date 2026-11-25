"""Integration and unit tests for the Predictions API endpoints."""

from typing import Any
from uuid import uuid4

import pytest
from flask.testing import FlaskClient
from testing_core import APITester

from database.object_models.core.predictions import Prediction

PREDICTIONS_URL = "/api/v1/predictions"
IMAGE_ID = 1047
IMAGE_UUID = "26be495e-3ec2-41c8-ba14-d0b65726bb67"
MODEL = {"pkey": 2, "uuid": "f5f4caad-1fd4-46a7-982e-21d396a36d48"}


class TestPredictions(APITester):
    """Test suite covering the `/api/v1/predictions` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients,
    mocked S3 storage, and automatic database transaction rollbacks for isolation.
    """

    @pytest.fixture
    def sample_prediction(self, auth_client: FlaskClient) -> dict[str, Any]:
        """Fetch an existing prediction associated with the sample image.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.

        Returns:
            dict[str, Any]: Serialized prediction dictionary.
        """
        res = auth_client.get(f"/api/v1/images/{IMAGE_UUID}/predictions")
        assert res.status_code == 200
        preds = res.get_json()
        assert preds, "Sample image should contain at least one prediction."
        return preds[0]

    @pytest.fixture
    def valid_create_payload(self) -> dict[str, Any]:
        """Generate a valid request payload for creating a prediction.

        Returns:
            dict[str, Any]: Valid CreatePredictionReq dictionary payload.
        """
        return {
            "image_ids": {"pkey": IMAGE_ID, "uuid": IMAGE_UUID},
            "model_ids": MODEL,
            "label": 2,
            "score": 0.88,
            "box_tx": 50,
            "box_ty": 60,
            "box_bx": 150,
            "box_by": 180,
        }

    # -------------------------------------------------------------------------
    # 1. GET Prediction by ID (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_get_prediction_by_uuid(
        self, auth_client: FlaskClient, sample_prediction: dict[str, Any]
    ) -> None:
        """Verify retrieving a prediction by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_prediction (dict[str, Any]): Sample prediction fixture.
        """
        pred_uuid = sample_prediction["uuid"]
        response = auth_client.get(f"{PREDICTIONS_URL}/{pred_uuid}")
        assert response.status_code == 200

        data = response.get_json()
        Prediction.Response.model_validate(data)
        assert data["uuid"] == pred_uuid
        assert data["pred_id"] == sample_prediction["pred_id"]
        assert data["score"] == sample_prediction["score"]
        assert data["label"] == sample_prediction["label"]
        assert data["dimensions"] == sample_prediction["dimensions"]

    def test_get_prediction_by_int_id(
        self, auth_client: FlaskClient, sample_prediction: dict[str, Any]
    ) -> None:
        """Verify retrieving a prediction by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_prediction (dict[str, Any]): Sample prediction fixture.
        """
        pred_id = sample_prediction["pred_id"]
        response = auth_client.get(f"{PREDICTIONS_URL}/{pred_id}")
        assert response.status_code == 200

        data = response.get_json()
        Prediction.Response.model_validate(data)
        assert data["pred_id"] == pred_id
        assert data["uuid"] == sample_prediction["uuid"]

    def test_get_prediction_by_uuid_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when querying a non-existent prediction UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{PREDICTIONS_URL}/{uuid4()}")
        assert response.status_code == 404

    def test_get_prediction_by_int_id_not_found(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 404 response when querying a non-existent prediction integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{PREDICTIONS_URL}/999999999")
        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # 2. GET Bulk Predictions Query
    # -------------------------------------------------------------------------

    def test_get_predictions_bulk_by_uuid(
        self, auth_client: FlaskClient, sample_prediction: dict[str, Any]
    ) -> None:
        """Verify retrieving predictions in bulk by a single UUID parameter.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_prediction (dict[str, Any]): Sample prediction fixture.
        """
        pred_uuid = sample_prediction["uuid"]
        response = auth_client.get(
            PREDICTIONS_URL, query_string={"object_ids": pred_uuid}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        Prediction.Response.model_validate(data[0])
        assert data[0]["uuid"] == pred_uuid
        assert data[0]["pred_id"] == sample_prediction["pred_id"]

    def test_get_predictions_bulk_by_int_id(
        self, auth_client: FlaskClient, sample_prediction: dict[str, Any]
    ) -> None:
        """Verify retrieving predictions in bulk by a single integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            sample_prediction (dict[str, Any]): Sample prediction fixture.
        """
        pred_id = sample_prediction["pred_id"]
        response = auth_client.get(
            PREDICTIONS_URL, query_string={"object_ids": pred_id}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        Prediction.Response.model_validate(data[0])
        assert data[0]["pred_id"] == pred_id
        assert data[0]["uuid"] == sample_prediction["uuid"]

    def test_get_predictions_bulk_multiple_ids(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify retrieving multiple predictions simultaneously in bulk.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        preds_res = auth_client.get(f"/api/v1/images/{IMAGE_UUID}/predictions")
        assert preds_res.status_code == 200
        preds = preds_res.get_json()
        assert len(preds) >= 2, "Test requires at least 2 predictions on sample image."

        target_uuids = [preds[0]["uuid"], preds[1]["uuid"]]
        response = auth_client.get(
            PREDICTIONS_URL,
            query_string=[("object_ids", target_uuids[0]), ("object_ids", target_uuids[1])],
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 2
        retrieved_uuids = {item["uuid"] for item in data}
        assert retrieved_uuids == set(target_uuids)
        for item in data:
            Prediction.Response.model_validate(item)

    def test_get_predictions_bulk_non_existent(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify bulk retrieval with non-existent UUID returns an empty list.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(
            PREDICTIONS_URL, query_string={"object_ids": str(uuid4())}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_predictions_bulk_missing_query(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 400 validation error when bulk query parameter is omitted.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(PREDICTIONS_URL)
        assert response.status_code == 400

    # -------------------------------------------------------------------------
    # 3. POST Create Prediction
    # -------------------------------------------------------------------------

    def test_create_prediction_success(
        self, auth_client: FlaskClient, valid_create_payload: dict[str, Any]
    ) -> None:
        """Verify creating a valid prediction record with bounding coordinates.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            valid_create_payload (dict[str, Any]): Valid creation payload fixture.
        """
        response = auth_client.post(PREDICTIONS_URL, json=valid_create_payload)
        assert response.status_code == 200

        data = response.get_json()
        Prediction.Response.model_validate(data)
        assert data["score"] == valid_create_payload["score"]
        assert data["label"] == valid_create_payload["label"]
        assert data["dimensions"] == {
            "top_left": {
                "x": valid_create_payload["box_tx"],
                "y": valid_create_payload["box_ty"],
            },
            "bottom_right": {
                "x": valid_create_payload["box_bx"],
                "y": valid_create_payload["box_by"],
            },
        }

        # Verify newly created prediction is retrievable by UUID and int ID
        created_uuid = data["uuid"]
        created_id = data["pred_id"]

        get_uuid_res = auth_client.get(f"{PREDICTIONS_URL}/{created_uuid}")
        assert get_uuid_res.status_code == 200
        assert get_uuid_res.get_json()["pred_id"] == created_id

        get_id_res = auth_client.get(f"{PREDICTIONS_URL}/{created_id}")
        assert get_id_res.status_code == 200
        assert get_id_res.get_json()["uuid"] == created_uuid

    def test_create_prediction_invalid_body_empty(
        self, auth_client: FlaskClient
    ) -> None:
        """Verify 400 response when posting an empty payload.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.post(PREDICTIONS_URL, json={})
        assert response.status_code == 400

    def test_create_prediction_missing_required_fields(
        self, auth_client: FlaskClient, valid_create_payload: dict[str, Any]
    ) -> None:
        """Verify 400 response when required bounding coordinates or labels are omitted.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            valid_create_payload (dict[str, Any]): Valid creation payload fixture.
        """
        del valid_create_payload["box_tx"]
        response = auth_client.post(PREDICTIONS_URL, json=valid_create_payload)
        assert response.status_code == 400

    def test_create_prediction_invalid_coordinate_types(
        self, auth_client: FlaskClient, valid_create_payload: dict[str, Any]
    ) -> None:
        """Verify 400 response when field data types are invalid.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
            valid_create_payload (dict[str, Any]): Valid creation payload fixture.
        """
        valid_create_payload["score"] = "invalid_score_str"
        response = auth_client.post(PREDICTIONS_URL, json=valid_create_payload)
        assert response.status_code == 400

