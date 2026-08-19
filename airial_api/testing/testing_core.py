import pytest

from app import create_app
from app.extensions import base
from database.object_models.user_management.users import CreateUserReq

class APITester:
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
            'SERVER_NAME': 'localhost',
        })
        yield app

        base.close_pool()
    
    @pytest.fixture
    def client(self, app): 
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def auth_client(self, client, app):     
        client.post('/api/v1/authenticate', json={'email': 'tester@local.host', 'password': 'Learning2Count'}, follow_redirects=True)
        yield client

    @pytest.fixture
    def runner(self, app):
        return app.test_cli_runner()
