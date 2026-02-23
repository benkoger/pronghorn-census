import os

from boto3 import client
from flask import Flask
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

import app.errors as errors
from app.extensions import base, cache, login_manager, session_manager
from config import s3_config
from config import FlaskConfig, cache_config, s3_config

def create_app():
	app = Flask(__name__)
	app.config.from_object(FlaskConfig)

	CORS(app, resources={
		r'/api/*': {
			'origins': [
				app.config['ORIGIN_URL'],
			],
			'supports_credentials': True     
		}
	})
	setattr(app, 's3', client(
        's3',
        config=s3_config,
        endpoint_url=os.environ.get('AWS_ENDPOINT_URL_S3')
    ) )

	cache.init_app(app, cache_config)
	login_manager.init_app(app)
	session_manager.init_app(app)
	base.init_app(app)

	app.errorhandler(HTTPException)(errors.handle_generic_http)
	app.errorhandler(500)(errors.internal_service_error)

	from app.routes import bp
	app.register_blueprint(bp)

	from app.routers.projects import projectBp
	app.register_blueprint(projectBp)

	from app.routers.models import modelBp
	app.register_blueprint(modelBp)

	from app.routers.images import imageBp
	app.register_blueprint(imageBp)

	from app.routers.surveys import surveyBp
	app.register_blueprint(surveyBp)

	from app.routers.herdunits import herdunitBp
	app.register_blueprint(herdunitBp)

	from app.routers.schemas import schemaBp
	app.register_blueprint(schemaBp)

	return app

