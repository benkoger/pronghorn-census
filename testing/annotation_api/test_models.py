from annotation_testing_core import APITester
import urllib.parse

class TestModels(APITester):
    def test_create_model(self, auth_client):
        body = {
            'name' : 'test_model',
            'project_id' : 1,
            'schema_id' : 1, 
            'survey_ids' : [1],
        }
        response = auth_client.post('/api/v1/models', json=body)
        print(f"Response: {response}")
        assert response.status_code == 201

    def test_get_model_training(self, auth_client):
        params = {
            'survey': 1,
            'herd_unit': 1,
            'label': 2, 
        }
        query_string = urllib.parse.urlencode(params)

        response = auth_client.get(f'/api/v1/models/training?{query_string}')
        assert response.status_code == 200

    def test_update_model(self, auth_client):
        body = {
            'model_id': 1,
            'name' : 'testName'
        }
        response = auth_client.patch(f'/api/v1/models/f5f4caad-1fd4-46a7-982e-21d396a36d48', json=body)
        assert response.status_code == 200