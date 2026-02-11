from annotation_testing_core import APITester


class TestImages(APITester):
    def test_create_presigned_get(self, auth_client):
        body = {
            'expires_in': 3600
        }
        response = auth_client.post(
            '/api/v1/images/26be495e-3ec2-41c8-ba14-d0b65726bb67/presigned_url', 
            json=body
            )

        assert response.status_code == 201

    def test_create_image(self, auth_client):
        body = {
            'name': 'cool_pronghorn',
            'herd_unit_id': 1,
            'survey_id': 1,
            'img_key': 's3://image/something',
            'image_length_px': 67,
            'image_width_px': 67
        }
        response = auth_client.post('/api/v1/images', json=body)

        assert response.status_code == 201

    def test_get_image_crops(self, auth_client):
        response = auth_client.get('/api/v1/images/26be495e-3ec2-41c8-ba14-d0b65726bb67/crops')

        assert response.status_code == 200

    def test_get_image_predictions(self, auth_client):
        response = auth_client.get('/api/v1/images/26be495e-3ec2-41c8-ba14-d0b65726bb67/predictions')

        assert response.status_code == 200

    def test_get_image_annotations(self, auth_client):
        response = auth_client.get('/api/v1/images/97f3951c-fd16-4352-b746-7dfa0f1db948/annotations')

        assert response.status_code == 200

    def test_update_image(self, auth_client):
        body = {
            'name': 'creative_new_name',
        }
        response = auth_client.patch('/api/v1/images/602db2a3-0958-497e-9075-19d858213d90', json=body)

        assert response.status_code == 200

    def test_delete_image(self, auth_client):
        response = auth_client.delete('/api/v1/images/08644912-e87e-4bac-ab1f-7140ee51312c')

        assert response.status_code == 204