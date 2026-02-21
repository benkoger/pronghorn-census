import os

import pytest

from annotation_api.app import create_app
from annotation_api.app.extensions import base

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
        with app.app_context():
            user = base.create_user('tRunner', 'testing123', 'manual-token', 'en-us')
            
        client.post('/api/v1/authenticate', json={'external-id': 'testing123'}, follow_redirects=True)
        yield client

    @pytest.fixture
    def runner(self, app):
        return app.test_cli_runner()