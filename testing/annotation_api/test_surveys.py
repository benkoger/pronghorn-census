from annotation_testing_core import APITester
from datetime import datetime
import urllib.parse

class TestSurveys(APITester):
    def test_create_survey(self, auth_client):
        body = {
            'survey_date': datetime.now().isoformat(),
            'project_id': '58bb015b-cc74-45a2-b986-def9173cdf86',
            'herd_unit_ids': [1],
            'name': 'test survey',
            'additional_info': 'you should not be seeing this'
        }
        response = auth_client.post('/api/v1/surveys', json=body)

        assert response.status_code == 201

    def test_update_survey(self, auth_client):
        body = {
            'name': 'a new survey name'
        }
        response = auth_client.patch('/api/v1/surveys/f4c0b5e0-af30-46fa-a276-6169932b6a34', json=body)

        assert response.status_code == 200

    def test_get_survey_annotations(self, auth_client):
        resposne = auth_client.get('/api/v1/surveys/f4c0b5e0-af30-46fa-a276-6169932b6a34/annotations')
        
        assert resposne.status_code == 200

    def test_get_survey_herd_units(self, auth_client):
        resposne = auth_client.get('/api/v1/surveys/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd-units')
        
        assert resposne.status_code == 200

    def test_get_survey_annotated_images(self, auth_client):
        params = {
            'herd_unit': 1,
            'label': 3, 
        }
        query_string = urllib.parse.urlencode(params)

        response = auth_client.get(f'/api/v1/surveys/f4c0b5e0-af30-46fa-a276-6169932b6a34/annotated_images?{query_string}')
        assert response.status_code == 200