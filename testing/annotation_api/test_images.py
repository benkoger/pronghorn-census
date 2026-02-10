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
            'expires_in': 3600
        }
        response = client.post(
            '/api/v1/images/26be495e-3ec2-41c8-ba14-d0b65726bb67/presigned_url', 
            json=body
            )

        assert response.status_code == 201

    def test_create_image(self, client):
        body = {
            'name': 'cool_pronghorn69.jpg',
            'herd_unit_id': 1,
            'survey_id': 1,
            'img_key': 's3://image/something',
            'image_length_px': 67,
            'image_width_px': 67
        }
        response = client.post('/api/v1/images', json=body)

        assert response.status_code == 201

    def test_get_image_crops(self, client):
        response = client.get('/api/v1/images/26be495e-3ec2-41c8-ba14-d0b65726bb67/crops')

        assert response.status_code == 200