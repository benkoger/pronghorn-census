# Pytest runner for the surveys router in the Airial API
# Author Michael B. Lance

from datetime import datetime, timezone
import urllib.parse
from uuid import uuid4

from pydantic import BaseModel, TypeAdapter
import pytest

from database.object_models.core.annotations import Annotation
from database.object_models.core.images import Image
from database.object_models.project_management import HerdUnit, Survey, SurveyStatus
from testing_core import APITester


class PaginatedImagesResponse(BaseModel):
    images: list[Image.Response]
    total: int
    page: int | None = None
    per_page: int | None = None


class TestSurveys(APITester):
    # -------------------------------------------------------------------------
    # 1. GET Single & List Endpoint Schema Validation
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "endpoint, expected_schema, is_list",
        [
            (
                "/api/v1/surveys/f4c0b5e0-af30-46fa-a276-6169932b6a34",
                Survey.Response,
                False,
            ),
            (
                "/api/v1/surveys/1",
                Survey.Response,
                False,
            ),
            (
                "/api/v1/surveys/f4c0b5e0-af30-46fa-a276-6169932b6a34/annotations",
                Annotation.Response,
                True,
            ),
            (
                "/api/v1/surveys/1/annotations",
                Annotation.Response,
                True,
            ),
            (
                "/api/v1/surveys/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd-units",
                HerdUnit.Response,
                True,
            ),
            (
                "/api/v1/surveys/1/herd-units",
                HerdUnit.Response,
                True,
            ),
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

    # -------------------------------------------------------------------------
    # 2. GET Paginated & Filtered Images
    # -------------------------------------------------------------------------

    def test_get_survey_images_paginated_success(self, auth_client):
        survey_uuid = "f4c0b5e0-af30-46fa-a276-6169932b6a34"
        response = auth_client.get(
            f"/api/v1/surveys/{survey_uuid}/images?page=1&per_page=10"
        )
        assert response.status_code == 200

        data = response.get_json()
        validated = PaginatedImagesResponse.model_validate(data)
        assert len(validated.images) == 10
        assert validated.page == 1
        assert validated.per_page == 10
        assert validated.total > 0

    def test_get_survey_images_pagination_navigation(self, auth_client):
        survey_uuid = "f4c0b5e0-af30-46fa-a276-6169932b6a34"
        res_page1 = auth_client.get(
            f"/api/v1/surveys/{survey_uuid}/images?page=1&per_page=5"
        )
        res_page2 = auth_client.get(
            f"/api/v1/surveys/{survey_uuid}/images?page=2&per_page=5"
        )

        assert res_page1.status_code == 200
        assert res_page2.status_code == 200

        page1_data = PaginatedImagesResponse.model_validate(res_page1.get_json())
        page2_data = PaginatedImagesResponse.model_validate(res_page2.get_json())

        assert len(page1_data.images) == 5
        assert len(page2_data.images) == 5
        assert page1_data.page == 1
        assert page2_data.page == 2

        # Verify items on different pages do not overlap
        page1_uuids = {img.uuid for img in page1_data.images}
        page2_uuids = {img.uuid for img in page2_data.images}
        assert page1_uuids.isdisjoint(page2_uuids)

    def test_get_survey_images_clamped_query_bounds(self, auth_client):
        survey_uuid = "f4c0b5e0-af30-46fa-a276-6169932b6a34"
        response = auth_client.get(
            f"/api/v1/surveys/{survey_uuid}/images?page=-1&per_page=0"
        )
        assert response.status_code == 200
        data = response.get_json()
        validated = PaginatedImagesResponse.model_validate(data)
        assert validated.page == 1
        assert validated.per_page >= 1 #pyright: ignore

    def test_get_survey_images_no_pagination(self, auth_client):
        survey_uuid = "f4c0b5e0-af30-46fa-a276-6169932b6a34"
        response = auth_client.get(
                f"/api/v1/surveys/{survey_uuid}/images"
                )

        assert response.status_code == 200
        data = response.get_json()
        PaginatedImagesResponse.model_validate(data)


    def test_get_survey_annotated_images_with_filters(self, auth_client):
        survey_uuid = "f4c0b5e0-af30-46fa-a276-6169932b6a34"
        params = [("label", 3), ("herd_unit", 1)]
        query_string = urllib.parse.urlencode(params)

        response = auth_client.get(
            f"/api/v1/surveys/{survey_uuid}/annotated_images?{query_string}"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)

    # -------------------------------------------------------------------------
    # 3. GET Not Found / Edge Cases
    # -------------------------------------------------------------------------

    def test_get_survey_not_found(self, auth_client):
        random_uuid = str(uuid4())
        response = auth_client.get(f"/api/v1/surveys/{random_uuid}")
        assert response.status_code == 404

    def test_get_survey_int_id_not_found(self, auth_client):
        response = auth_client.get("/api/v1/surveys/9999999")
        assert response.status_code == 404

    def test_get_survey_annotated_images_not_found(self, auth_client):
        random_uuid = str(uuid4())
        response = auth_client.get(f"/api/v1/surveys/{random_uuid}/annotated_images")
        assert response.status_code == 404

    # -------------------------------------------------------------------------
    # 4. POST Endpoint Validation & Payloads
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "endpoint, payload, expected_status",
        [
            # Valid survey creation
            (
                "/api/v1/surveys",
                {
                    "project_ids": {
                        "pkey": 1,
                        "uuid": "58bb015b-cc74-45a2-b986-def9173cdf86",
                    },
                    "herd_unit_ids": {
                        "pkey": 1,
                        "uuid": "4317a307-9595-4116-be11-c7584561dd8d",
                    },
                    "survey_date": datetime.now(timezone.utc).isoformat(),
                    "name": f"survey_{uuid4().hex[:6]}",
                    "status": "uploaded",
                    "survey_area": 1500.5,
                    "additional_info": "Automated test survey",
                },
                201,
            ),
            # Invalid survey creation (missing required fields)
            (
                "/api/v1/surveys",
                {
                    "name": "incomplete_survey",
                },
                400,
            ),
        ],
    )
    def test_post_endpoints(self, auth_client, endpoint, payload, expected_status):
        response = auth_client.post(endpoint, json=payload)
        assert response.status_code == expected_status
        if expected_status == 201:
            data = response.get_json()
            Survey.Response.model_validate(data)

    # -------------------------------------------------------------------------
    # 5. State-Mutating Lifecycles (PATCH & DELETE)
    # -------------------------------------------------------------------------

    def test_update_survey_by_uuid_success(self, auth_client):
        survey_uuid = "f4c0b5e0-af30-46fa-a276-6169932b6a34"
        new_name = f"updated_{uuid4().hex[:6]}"

        response = auth_client.patch(
            f"/api/v1/surveys/{survey_uuid}",
            json={"name": new_name, "status": "measuring"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == new_name
        assert data["status"] == "measuring"

    def test_update_survey_by_int_success(self, auth_client):
        new_name = f"updated_int_{uuid4().hex[:6]}"

        response = auth_client.patch(
            "/api/v1/surveys/1",
            json={"name": new_name, "survey_area": 999.9},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == new_name
        assert data["survey_area"] == 999.9

    def test_update_survey_not_found(self, auth_client):
        random_uuid = str(uuid4())
        response = auth_client.patch(
            f"/api/v1/surveys/{random_uuid}",
            json={"name": "does_not_matter"},
        )
        assert response.status_code == 404

    def test_delete_survey_lifecycle(self, auth_client):
        payload = {
            "project_ids": {
                "pkey": 1,
                "uuid": "58bb015b-cc74-45a2-b986-def9173cdf86",
            },
            "herd_unit_ids": {
                "pkey": 1,
                "uuid": "4317a307-9595-4116-be11-c7584561dd8d",
            },
            "survey_date": datetime.now(timezone.utc).isoformat(),
            "name": f"delete_me_{uuid4().hex[:6]}",
        }

        create_res = auth_client.post("/api/v1/surveys", json=payload)
        assert create_res.status_code == 201

        created_survey = create_res.get_json()
        target_uuid = created_survey["uuid"]

        assert auth_client.get(f"/api/v1/surveys/{target_uuid}").status_code == 200

        delete_res = auth_client.delete(f"/api/v1/surveys/{target_uuid}")
        assert delete_res.status_code == 204

        assert auth_client.get(f"/api/v1/surveys/{target_uuid}").status_code == 404
