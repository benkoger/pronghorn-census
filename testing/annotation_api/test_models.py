from annotation_api.app import create_app
import pytest 
from annotation_api.app.extensions import base
import urllib.parse

class TestModels:
    @pytest.fixture
    def app(self):
        app = create_app()
        #Important! The host must be overwritten prior to connection
        base._config['host'] = 'localhost'
        base.create_pool()
        app.config.update({
            'TESTING': True,
            'SESSION_COOKIE_SECURE': False,   
            'SESSION_COOKIE_DOMAIN': None,    
            'SESSION_COOKIE_HTTPONLY': False, 
            'SERVER_NAME': "localhost",
            'LOGIN_DISABLED': True,        
        })
        yield app

        base.close_pool()
    
    @pytest.fixture
    def client(self, app): 
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def runner(self, app):
        return app.test_cli_runner()

    def test_create_model(self, client):
        body = {
            'name' : 'test_model',
            'project_id' : 1,
            'schema_id' : 1, 
            'survey_ids' : [1],
        }
        response = client.post('/api/v1/models', json=body)
        print(f"Response: {response}")
        assert response.status_code == 201

    def test_get_model_training(self, client):
        params = {
            'survey': 1,
            'herd_unit': 1,
            'label': 2, 
        }
        query_string= urllib.parse.urlencode(params)

        response = client.get(f'/api/v1/models/training?{query_string}')
        assert response.status_code == 200

    def test_update_model(self, client):
        body = {
            'model_id': 1,
            'name' : 'testName'
        }
        response = client.patch(f'/api/v1/models/f5f4caad-1fd4-46a7-982e-21d396a36d48', json=body)
        assert response.status_code == 200