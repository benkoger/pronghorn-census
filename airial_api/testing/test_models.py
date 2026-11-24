"""Integration and unit tests for the Models API endpoints."""

from typing import Any
from uuid import uuid4

from flask.testing import FlaskClient
from testing_core import APITester

from database.object_models.project_management.models import Model, ModelType
from database.object_models.project_management.schemas import Schema

MODELS_URL = "/api/v1/models"
MODEL_ID = 2
MODEL_UUID = "f5f4caad-1fd4-46a7-982e-21d396a36d48"
PROJECT_KEYRING = {"pkey": 1, "uuid": "58bb015b-cc74-45a2-b986-def9173cdf86"}
SCHEMA_KEYRING = {"pkey": 1, "uuid": "1b9930d5-386d-4132-9afb-e5dbdf43ea23"}


def _build_model_payload(
    model_type: ModelType = ModelType.DETECTION,
) -> dict[str, Any]:
    """Build a valid model creation payload.

    Args:
        model_type (ModelType): Model architecture type. Defaults to DETECTION.

    Returns:
        dict[str, Any]: Valid CreateModelReq payload dictionary.
    """
    return {
        "name": f"TestModel_{uuid4().hex[:8]}",
        "model_type": model_type.value,
        "project_ids": PROJECT_KEYRING,
        "schema_ids": SCHEMA_KEYRING,
    }


class TestModels(APITester):
    """Test suite covering the `/api/v1/models` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients and
    automatic database transaction rollbacks for isolation.
    """

    # -------------------------------------------------------------------------
    # 1. GET Model by ID (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_get_model_by_uuid(self, auth_client: FlaskClient) -> None:
        """Verify retrieving a model by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{MODELS_URL}/{MODEL_UUID}")
        assert response.status_code == 200

        data = response.get_json()
        validated = Model.Response.model_validate(data)
        assert validated.model_id == MODEL_ID
        assert str(validated.uuid) == MODEL_UUID

    def test_get_model_by_int_id(self, auth_client: FlaskClient) -> None:
        """Verify retrieving a model by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{MODELS_URL}/{MODEL_ID}")
        assert response.status_code == 200

        data = response.get_json()
        validated = Model.Response.model_validate(data)
        assert validated.model_id == MODEL_ID
        assert str(validated.uuid) == MODEL_UUID

    def test_get_model_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 responses for non-existent model UUID and integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.get(f"{MODELS_URL}/{uuid4()}").status_code == 404
        assert auth_client.get(f"{MODELS_URL}/999999999").status_code == 404

    def test_get_model_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when fetching a model unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.get(f"{MODELS_URL}/{MODEL_UUID}").status_code == 401
        assert client.get(f"{MODELS_URL}/{MODEL_ID}").status_code == 401

    # -------------------------------------------------------------------------
    # 2. GET Model Schema
    # -------------------------------------------------------------------------

    def test_get_model_schema_by_uuid(self, auth_client: FlaskClient) -> None:
        """Verify retrieving the label schema for a model by UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{MODELS_URL}/{MODEL_UUID}/schema")
        assert response.status_code == 200

        data = response.get_json()
        validated = Schema.Response.model_validate(data)
        assert validated.schema_id == SCHEMA_KEYRING["pkey"]

    def test_get_model_schema_by_int_id(self, auth_client: FlaskClient) -> None:
        """Verify retrieving the label schema for a model by integer ID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.get(f"{MODELS_URL}/{MODEL_ID}/schema")
        assert response.status_code == 200

        data = response.get_json()
        validated = Schema.Response.model_validate(data)
        assert validated.schema_id == SCHEMA_KEYRING["pkey"]

    def test_get_model_schema_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 response when fetching schema for a non-existent model.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.get(f"{MODELS_URL}/{uuid4()}/schema").status_code == 404

    # -------------------------------------------------------------------------
    # 3. GET / POST / PUT Artifact Stub Endpoints
    # -------------------------------------------------------------------------

    def test_artifact_get_endpoints(self, auth_client: FlaskClient) -> None:
        """Verify GET model artifact endpoints return 200 when authenticated.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        for suffix in (
            "json",
            "json/train",
            "json/val",
            "weights",
            "config",
            "readme",
        ):
            res = auth_client.get(f"{MODELS_URL}/{MODEL_UUID}/{suffix}")
            assert res.status_code == 200

    def test_artifact_post_and_put_endpoints(self, auth_client: FlaskClient) -> None:
        """Verify POST and PUT model artifact endpoints return 200 when authenticated.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        for suffix in ("train", "val", "weights", "config", "readme"):
            assert auth_client.post(f"{MODELS_URL}/{MODEL_UUID}/{suffix}").status_code == 200

        assert auth_client.put(f"{MODELS_URL}/{MODEL_UUID}").status_code == 200
        for suffix in ("train", "val", "weights", "config", "readme"):
            assert auth_client.put(f"{MODELS_URL}/{MODEL_UUID}/{suffix}").status_code == 200

    def test_artifact_endpoints_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 responses for artifact endpoints when unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.get(f"{MODELS_URL}/{MODEL_UUID}/json").status_code == 401
        assert client.post(f"{MODELS_URL}/{MODEL_UUID}/train").status_code == 401
        assert client.put(f"{MODELS_URL}/{MODEL_UUID}").status_code == 401

    # -------------------------------------------------------------------------
    # 4. POST Create Model
    # -------------------------------------------------------------------------

    def test_create_model_success(self, auth_client: FlaskClient) -> None:
        """Verify creating a new model record and retrieving it afterwards.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        payload = _build_model_payload(ModelType.REGRESSION)
        response = auth_client.post(MODELS_URL, json=payload)
        assert response.status_code == 201

        data = response.get_json()
        validated = Model.Response.model_validate(data)
        assert validated.name == payload["name"]
        assert validated.model_type == ModelType.REGRESSION
        assert validated.schema_id == SCHEMA_KEYRING["pkey"]

        get_res = auth_client.get(f"{MODELS_URL}/{validated.uuid}")
        assert get_res.status_code == 200
        assert get_res.get_json()["name"] == payload["name"]

    def test_create_model_invalid_payload(self, auth_client: FlaskClient) -> None:
        """Verify 400 validation errors for invalid model creation payloads.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.post(MODELS_URL, json={}).status_code == 400
        assert (
            auth_client.post(
                MODELS_URL, json={"name": "MissingType"}
            ).status_code
            == 400
        )

    def test_create_model_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when creating a model unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        response = client.post(MODELS_URL, json=_build_model_payload())
        assert response.status_code == 401

    # -------------------------------------------------------------------------
    # 5. PATCH Update Model (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_update_model_by_uuid(self, auth_client: FlaskClient) -> None:
        """Verify updating a model name by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        new_name = f"UpdatedModel_{uuid4().hex[:8]}"
        response = auth_client.patch(
            f"{MODELS_URL}/{MODEL_UUID}", json={"name": new_name}
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = Model.Response.model_validate(data)
        assert validated.name == new_name

    def test_update_model_by_int_id(self, auth_client: FlaskClient) -> None:
        """Verify updating a model name by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        new_name = f"UpdatedModelInt_{uuid4().hex[:8]}"
        response = auth_client.patch(
            f"{MODELS_URL}/{MODEL_ID}", json={"name": new_name}
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = Model.Response.model_validate(data)
        assert validated.name == new_name

    def test_update_model_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 response when updating a non-existent model.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        response = auth_client.patch(
            f"{MODELS_URL}/{uuid4()}", json={"name": "Phantom"}
        )
        assert response.status_code == 404

    def test_update_model_invalid_payload(self, auth_client: FlaskClient) -> None:
        """Verify 400 response when patching a model with empty payload.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.patch(f"{MODELS_URL}/{MODEL_UUID}", json={}).status_code == 400

    # -------------------------------------------------------------------------
    # 6. DELETE Model (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_delete_model_by_uuid(self, auth_client: FlaskClient) -> None:
        """Verify deleting a model by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        create_res = auth_client.post(MODELS_URL, json=_build_model_payload())
        assert create_res.status_code == 201
        created = create_res.get_json()

        del_res = auth_client.delete(f"{MODELS_URL}/{created['uuid']}")
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert auth_client.get(f"{MODELS_URL}/{created['uuid']}").status_code == 404

    def test_delete_model_by_int_id(self, auth_client: FlaskClient) -> None:
        """Verify deleting a model by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        create_res = auth_client.post(MODELS_URL, json=_build_model_payload())
        assert create_res.status_code == 201
        created = create_res.get_json()

        del_res = auth_client.delete(f"{MODELS_URL}/{created['model_id']}")
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert auth_client.get(f"{MODELS_URL}/{created['model_id']}").status_code == 404

    def test_delete_model_unauthenticated(self, client: FlaskClient) -> None:
        """Verify 401 response when deleting a model unauthenticated.

        Args:
            client (FlaskClient): Unauthenticated test client fixture.
        """
        assert client.delete(f"{MODELS_URL}/{uuid4()}").status_code == 401
        assert client.delete(f"{MODELS_URL}/{MODEL_ID}").status_code == 401
