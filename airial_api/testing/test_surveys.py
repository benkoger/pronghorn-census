# Pytest runner for the surveys router in the Airial API
# Author Michael B. Lance

from datetime import datetime
from uuid import uuid4
import urllib.parse
import pytest
from pydantic import TypeAdapter

from testing_core import APITester
from database.object_models.project_management.surveys import Survey
from database.object_models.core.annotations import Annotation
from database.object_models.project_management.herd_units import HerdUnit


class TestSurveys(APITester):
    SURVEY_INT_ID = 1
    SURVEY_UUID = "f4c0b5e0-af30-46fa-a276-6169932b6a34"

    # -------------------------------------------------------------------------
    # 1. GET Single & Related Endpoint Schema Validation
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "endpoint, expected_schema, is_list",
        [
            (f"/api/v1/surveys/{SURVEY_INT_ID}", Survey.Response, False),
            (f"/api/v1/surveys/{SURVEY_UUID}", Survey.Response, False),
            (f"/api/v1/surveys/{SURVEY_INT_ID}/annotations", Annotation.Response, True),
            (f"/api/v1/surveys/{SURVEY_UUID}/annotations", Annotation.Response, True),
            (f"/api/v1/surveys/{SURVEY_INT_ID}/herd-units", HerdUnit.Response, True),
            (f"/api/v1/surveys/{SURVEY_UUID}/herd-units", HerdUnit.Response, True),
        ],
    )
    def test_get_endpoints_schema_success(
        self, auth_client, endpoint, expected_schema, is_list
    ):
        response = auth_client.get(endpoint)
        assert response.status_code == 200

        data = response.get_json()
        if is_list:
            TypeAdapter(list[expected_schema]).validate_python(data)
        else:
            expected_schema.model_validate(data)

    def test_get_survey_images(self, auth_client):
        response = auth_client.get(f"/api/v1/surveys/{self.SURVEY_UUID}/images?page=1&per_page=10")
        assert response.status_code == 200
        data = response.get_json()
        assert "images" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["per_page"] == 10

    def test_get_survey_annotated_images(self, auth_client):
        params = {"herd_unit": 1, "label": 6}
        query_string = urllib.parse.urlencode(params)
        response = auth_client.get(f"/api/v1/surveys/{self.SURVEY_INT_ID}/annotated_images?{query_string}")
        assert response.status_code == 200
        response_uuid = auth_client.get(f"/api/v1/surveys/{self.SURVEY_UUID}/annotated_images?{query_string}")
        assert response_uuid.status_code == 200

    def test_get_survey_not_found(self, auth_client):
        random_uuid = str(uuid4())
        response = auth_client.get(f"/api/v1/surveys/{random_uuid}")
        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # 2. POST Endpoint Validation & Payloads
    # -------------------------------------------------------------------------

    def test_create_survey_success(self, auth_client):
        payload = {
            "name": f"survey_{uuid4().hex[:6]}",
            "survey_date": datetime.now().isoformat(),
            "project_ids": {"pkey": 1, "uuid": "58bb015b-cc74-45a2-b986-def9173cdf86"},
            "herd_unit_ids": {"pkey": 1, "uuid": "4317a307-9595-4116-be11-c7584561dd8d"},
            "additional_info": "Automated test survey",
        }
        response = auth_client.post("/api/v1/surveys", json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert "survey_id" in data
        assert "uuid" in data

    def test_create_survey_validation_error(self, auth_client):
        payload = {"name": "incomplete_survey"}
        response = auth_client.post("/api/v1/surveys", json=payload)
        assert response.status_code == 400

    # -------------------------------------------------------------------------
    # 3. PATCH & DELETE Lifecycles
    # -------------------------------------------------------------------------

    def test_update_survey_success(self, auth_client):
        new_name = f"updated_survey_{uuid4().hex[:4]}"
        response = auth_client.patch(f"/api/v1/surveys/{self.SURVEY_UUID}", json={"name": new_name})
        assert response.status_code == 200
        assert response.get_json()["name"] == new_name

        response_int = auth_client.patch(f"/api/v1/surveys/{self.SURVEY_INT_ID}", json={"name": new_name})
        assert response_int.status_code == 200

    def test_delete_survey_lifecycle(self, auth_client):
        payload = {
            "name": f"survey_to_delete_{uuid4().hex[:6]}",
            "survey_date": datetime.now().isoformat(),
            "project_ids": {"pkey": 1, "uuid": "58bb015b-cc74-45a2-b986-def9173cdf86"},
            "herd_unit_ids": {"pkey": 1, "uuid": "4317a307-9595-4116-be11-c7584561dd8d"},
            "additional_info": "Will be deleted",
        }
        create_res = auth_client.post("/api/v1/surveys", json=payload)
        assert create_res.status_code == 201
        target_uuid = create_res.get_json()["uuid"]

        delete_res = auth_client.delete(f"/api/v1/surveys/{target_uuid}")
        assert delete_res.status_code == 204

        get_res = auth_client.get(f"/api/v1/surveys/{target_uuid}")
        assert get_res.status_code == 404
