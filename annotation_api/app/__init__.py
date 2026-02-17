import os
from config import s3_config
from boto3 import client
from flask import Flask
from flask_cors import CORS
import app.errors as errors
from werkzeug.exceptions import HTTPException
from config import FlaskConfig, s3_config, cache_config
from app.extensions import login_manager, cache, session_manager, base

def create_app():
	app = Flask(__name__)
	app.config.from_object(FlaskConfig)

	CORS(app, resources={
		r'/api/*': {
			'origins': [
				app.config['ORIGIN_URL']
			],
			'supports_credentials': True     
		}
	})
	global pathfinder
	pathfinder = client(
        's3',
        config=s3_config,
        endpoint_url=os.environ.get('AWS_ENDPOINT_URL_S3')
    )

	cache.init_app(app, cache_config)
	login_manager.init_app(app)
	session_manager.init_app(app)
	base.init_app(app)

	app.errorhandler(HTTPException)(errors.handle_generic_http)
	app.errorhandler(500)(errors.internal_service_error)

	from app.routes import bp
	app.register_blueprint(bp)
	return app

