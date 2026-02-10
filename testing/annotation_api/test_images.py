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
            'name': 'cool_pronghorn',
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

    def test_get_image_predictions(self, client):
        response = client.get('/api/v1/images/26be495e-3ec2-41c8-ba14-d0b65726bb67/predictions')

        assert response.status_code == 200

    def test_get_image_annotations(self, client):
        response = client.get('/api/v1/images/97f3951c-fd16-4352-b746-7dfa0f1db948/annotations')

        assert response.status_code == 200

    def test_update_image(self, client):
        body = {
            'name': 'creative_new_name',
        }
        response = client.patch('/api/v1/images/602db2a3-0958-497e-9075-19d858213d90', json=body)

        assert response.status_code == 200

    def test_delete_image(self, client):
        response = client.delete('/api/v1/images/08644912-e87e-4bac-ab1f-7140ee51312c')

        assert response.status_code == 204