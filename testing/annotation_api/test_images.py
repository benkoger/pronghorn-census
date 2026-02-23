from uuid import uuid4

import pytest

from annotation_testing_core import APITester

class TestImages(APITester):
    
    def test_get_image_by_id_success(self, auth_client):
        img_id = "26be495e-3ec2-41c8-ba14-d0b65726bb67"
        response = auth_client.get(f'/api/v1/images/{img_id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'uuid' in data
        assert data['uuid'] == img_id

    def test_get_image_not_found(self, auth_client):
        random_uuid = str(uuid4())
        response = auth_client.get(f'/api/v1/images/{random_uuid}')
        assert response.status_code == 404

    def test_get_image_crops(self, auth_client):
        img_id = "26be495e-3ec2-41c8-ba14-d0b65726bb67"
        response = auth_client.get(f'/api/v1/images/{img_id}/crops')
        
        assert response.status_code == 200
        data = response.get_json()
        print(data)
        assert isinstance(data, list)
        if len(data) > 0:
            assert 'reviewed_area_id' in data[0]

    def test_create_image_success(self, auth_client):
        body = {
            'name': f'pronghorn_{uuid4().hex[:6]}',
            'herd_unit_id': 1,
            'survey_id': 1,
            'img_key': f's3://bucket/test_{uuid4().hex}.jpg',
            'image_length_px': 1080,
            'image_width_px': 1920
        }
        response = auth_client.post('/api/v1/images', json=body)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['name'] == body['name']
        assert 'uuid' in data

    def test_create_image_invalid_payload(self, auth_client):
        body = {'name': 'incomplete_image'}
        response = auth_client.post('/api/v1/images', json=body)
        assert response.status_code == 400

    def test_create_presigned_get_success(self, auth_client):
        """
        CORRECTION: Your original test used /presigned_url, 
        but your Flask route is /presigned-get-url.
        """
        img_id = "26be495e-3ec2-41c8-ba14-d0b65726bb67"
        body = {
            'image_id': img_id,
            'expires_in': 3600
        }
        response = auth_client.post('/api/v1/images/presigned-get-url', json=body)

        assert response.status_code == 201
        assert "http" in response.get_data(as_text=True)

    def test_create_multipart_upload(self, auth_client):
        body = {
            'image_key': 'uploads/new_capture.jpg'
        }
        response = auth_client.post('/api/v1/images/create-multipart-upload', json=body)
        
        assert response.status_code == 201
        assert len(response.get_data(as_text=True)) > 0

    # --- PATCH Endpoints ---

    def test_update_image_success(self, auth_client):
        img_id = "602db2a3-0958-497e-9075-19d858213d90"
        new_name = f"updated_{uuid4().hex[:4]}"
        body = {'name': new_name}
        
        response = auth_client.patch(f'/api/v1/images/{img_id}', json=body)
        
        assert response.status_code == 200
        assert response.get_json()['name'] == new_name


    def test_delete_image_lifecycle(self, auth_client):
        setup_body = {
            'name': 'delete_me_test',
            'herd_unit_id': 1,
            'survey_id': 1,
            'img_key': 's3://temp/delete.jpg',
            'image_length_px': 100,
            'image_width_px': 100
        }
        created = auth_client.post('/api/v1/images', json=setup_body).get_json()
        print(created)
        target_id = created['uuid']

        delete_response = auth_client.delete(f'/api/v1/images/{target_id}')
        assert delete_response.status_code == 204

        get_response = auth_client.get(f'/api/v1/images/{target_id}')
        assert get_response.status_code == 404