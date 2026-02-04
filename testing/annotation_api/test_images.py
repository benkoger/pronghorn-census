from annotation_api.app import create_app
import pytest 
from annotation_api.app.extensions import base

class TestImages:
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

    def test_create_presigned_get(self, client):
        body = {
            'ra_key': "images/survey/f4c0b5e0-af30-46fa-a276-6169932b6a34/herd_unit/4317a307-9595-4116-be11-c7584561dd8d/image/pr527_by2023_survey1_flight1_00001_20240627_115303.JPG",
            'expires_in': 3600
        }
        response = client.post('/api/v1/images/presigned_url', json=body)

        assert response.status_code == 201