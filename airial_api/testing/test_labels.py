"""Integration and unit tests for the Labels API endpoints."""

from typing import Any
from uuid import uuid4

from flask.testing import FlaskClient
from testing_core import APITester

from database.object_models.project_management.labels import Label

LABELS_URL = "/api/v1/labels"
SCHEMA_KEYRING = {"pkey": 1, "uuid": "1b9930d5-386d-4132-9afb-e5dbdf43ea23"}


def _build_label_payload(label_num: int = 99) -> dict[str, Any]:
    """Build a valid label creation payload.

    Args:
        label_num (int): Numeric class index for the label. Defaults to 99.

    Returns:
        dict[str, Any]: Valid CreateLabelReq payload dictionary.
    """
    return {
        "name": f"TestLabel_{uuid4().hex[:8]}",
        "schema_ids": SCHEMA_KEYRING,
        "label": label_num,
        "image_link": "https://example.com/label.png",
        "color": "#33aa55",
    }


class TestLabels(APITester):
    """Test suite covering the `/api/v1/labels` REST endpoints.

    Inherits from `APITester` to provide authenticated Flask test clients and
    automatic database transaction rollbacks for isolation.
    """

    # -------------------------------------------------------------------------
    # 1. POST Create Label
    # -------------------------------------------------------------------------

    def test_create_label_success(self, auth_client: FlaskClient) -> None:
        """Verify successfully creating a label under an existing schema.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        payload = _build_label_payload(label_num=97)
        response = auth_client.post(LABELS_URL, json=payload)
        assert response.status_code == 201

        data = response.get_json()
        validated = Label.Response.model_validate(data)
        assert validated.name == payload["name"]
        assert validated.label == 97
        assert validated.schema_id == SCHEMA_KEYRING["pkey"]
        assert validated.color == "#33aa55"
        assert validated.image_link == "https://example.com/label.png"

        schema_labels = auth_client.get(
            f"/api/v1/schemas/{SCHEMA_KEYRING['uuid']}/labels"
        )
        assert schema_labels.status_code == 200
        uuids = {item["uuid"] for item in schema_labels.get_json()}
        assert str(validated.uuid) in uuids

    def test_create_label_invalid_payload(self, auth_client: FlaskClient) -> None:
        """Verify 400 validation errors when posting incomplete label payloads.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.post(LABELS_URL, json={}).status_code == 400
        assert (
            auth_client.post(LABELS_URL, json={"name": "MissingFields"}).status_code
            == 400
        )

    # -------------------------------------------------------------------------
    # 2. DELETE Label (UUID & Integer Primary Key)
    # -------------------------------------------------------------------------

    def test_delete_label_by_uuid(self, auth_client: FlaskClient) -> None:
        """Verify deleting a label by its public UUID.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        create_res = auth_client.post(LABELS_URL, json=_build_label_payload(95))
        assert create_res.status_code == 201
        created = create_res.get_json()

        del_res = auth_client.delete(f"{LABELS_URL}/{created['uuid']}")
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert auth_client.delete(f"{LABELS_URL}/{created['uuid']}").status_code == 404

    def test_delete_label_by_int_id(self, auth_client: FlaskClient) -> None:
        """Verify deleting a label by its integer primary key.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        create_res = auth_client.post(LABELS_URL, json=_build_label_payload(96))
        assert create_res.status_code == 201
        created = create_res.get_json()

        del_res = auth_client.delete(f"{LABELS_URL}/{created['label_id']}")
        assert del_res.status_code == 204
        assert del_res.data == b""

        assert (
            auth_client.delete(f"{LABELS_URL}/{created['label_id']}").status_code == 404
        )

    def test_delete_label_not_found(self, auth_client: FlaskClient) -> None:
        """Verify 404 response when deleting non-existent label IDs.

        Args:
            auth_client (FlaskClient): Authenticated test client fixture.
        """
        assert auth_client.delete(f"{LABELS_URL}/{uuid4()}").status_code == 404
        assert auth_client.delete(f"{LABELS_URL}/999999999").status_code == 404

